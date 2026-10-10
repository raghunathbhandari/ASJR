import sys
import os
from pathlib import Path
import importlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import Utils.asjr_paths as paths
import Utils.asjr_day as asjr_day
import Utils.asjr_storage as storage
import Utils.asjr_watchlist as watchlist
import Utils.asjr_universe as universe
import Utils.asjr_ibkr as ibkr
import Utils.asjr_yfinance as yfd
import Utils.asjr_features as daily_features
import Utils.asjr_intraday_features as intraday_features
import Utils.asjr_alerts as alerts
import Utils.asjr_market as market
import Utils.asjr_snapshot as snapshot
import Utils.asjr_git as asjr_git
import Utils.asjr_logger as asjr_logger
import Strategies.RudraReversal1H.rudra_reversal as rudra_reversal
from RudraScanner.bot_hook import run_bot_shadow
from RudraScanner.engine import evaluate_scanner, persist_features
from RudraScanner.volume_history import apply_rolling_rvol20
from RudraScanner.hourly import refresh_hourly_cache
from RudraScanner.reversal_bridge import seed_new_symbols
from RudraScanner.topdown import classify_topdown, ticker_etf_from_sources
from RudraScanner.patterns import PatternSettings, detect_five_patterns
from RudraScanner.delivery import deliver_scanner_alerts
from RudraScanner.discovery import read_ai_csv

try:
    from Backtesting.DataLoader.forex_download_hook import launch_forex_download_once
except Exception:
    launch_forex_download_once = None

try:
    from Backtesting.DataLoader.nq_download_hook import launch_nq_download_once
except Exception:
    launch_nq_download_once = None

ASJR_ANALYST_VERSION = "2026.10.10.5"

for m in (
    paths, asjr_day, storage, watchlist, universe, ibkr, yfd,
    daily_features, intraday_features, alerts, market, snapshot,
    asjr_git, asjr_logger, rudra_reversal
):
    importlib.reload(m)


def run_rudra_reversal_strategy(trade_date=None, tickers=None):
    """Run locked 1H Rudra-Reversal rules with an optionally shared ticker set."""
    if tickers is None:
        return rudra_reversal.build_rudra_reversal_alerts(trade_date=trade_date)
    return rudra_reversal.build_rudra_reversal_alerts(
        trade_date=trade_date, tickers=tuple(tickers),
    )


def run_asjr_manual_pipeline(
    app,
    trade_date=None,
    gapup_df=None,
    fetch_gapup_from_app=False,
    include_sector=True,
    git_submit=True,
    alert_sender=None,
):
    print("Thank you IBKR, yfinance and AI !")

    if trade_date is None:
        resolved_date = asjr_day.scheduled_date()
        if resolved_date is None:
            # A weekend run must not publish Friday bars as today's data.
            print("ASJR Analyst skipped: US stock session closed")
            return {
                "universe": pd.DataFrame(), "daily": pd.DataFrame(),
                "intraday_raw": pd.DataFrame(), "intraday": pd.DataFrame(),
                "alert_data": [], "rudra_reversal_alerts": [], "sector": pd.DataFrame(),
                "ticker_summary": pd.DataFrame(),
                "snapshot": {"trade_date": str(pd.Timestamp.now(tz=asjr_day.ET).date())},
                "git": {"status": "SKIPPED_CLOSED_SESSION"}, "log_file": None,
                "rudra_scanner_shadow": {"state": "SKIPPED_CLOSED_SESSION"},
                "rudra_scanner_features": {"state": "SKIPPED_CLOSED_SESSION"},
                "rudra_scanner_hourly": {"state": "SKIPPED_CLOSED_SESSION"},
                "rudra_scanner_research": {"state": "SKIPPED_CLOSED_SESSION"},
            }
        trade_date = resolved_date

    # paths.day_dir creates all local folders before any CSV or Git operation.
    paths.day_dir(trade_date)
    config_file, config_source = asjr_day.ensure_fixed_watchlist(
        paths.DATALAKE, trade_date
    )

    log_file = asjr_logger.run_log_path(
        paths.day_dir(trade_date) / "reports"
    )
    logger = asjr_logger.get_run_logger(log_file)

    logger.info("RUN | VERSION | %s", ASJR_ANALYST_VERSION)
    logger.info("RUN | START | trade_date=%s", paths.trading_day(trade_date))
    print(f"ASJR Analyst Version: {ASJR_ANALYST_VERSION}")
    logger.info("WATCHLIST | %s | source=%s", config_file, config_source or "prepared")
    logger.info(
        "RUN | OPTIONS | include_sector=%s | git_submit=%s | fetch_gapup_from_app=%s",
        include_sector,
        git_submit,
        fetch_gapup_from_app,
    )

    # One-time EURUSD research import. Safe to call every scheduled DataLake run:
    # the tmux launcher exits immediately when already running or completed.
    try:
        if launch_forex_download_once is None:
            logger.warning("FOREX | One-time launcher import unavailable")
        else:
            forex_launch = launch_forex_download_once()
            logger.info(
                "FOREX | One-time downloader | ok=%s | started=%s | %s",
                forex_launch.get("ok"),
                forex_launch.get("started"),
                forex_launch.get("message"),
            )
    except Exception:
        # Research import must never interrupt the production DataLake/Chakra run.
        logger.exception("FOREX | One-time downloader launch failed")

    # One-time NQ=F Yahoo research import. Runs in detached tmux and must never
    # block or break the production DataLake/Chakra cycle.
    try:
        if launch_nq_download_once is None:
            logger.warning("NQ | One-time launcher import unavailable")
        else:
            nq_launch = launch_nq_download_once()
            logger.info(
                "NQ | One-time downloader | ok=%s | started=%s | %s",
                nq_launch.get("ok"),
                nq_launch.get("started"),
                nq_launch.get("message"),
            )
    except Exception:
        logger.exception("NQ | One-time downloader launch failed")


    try:
        # First gated RudraScanner method integration. Default OFF: zero
        # new IBKR requests and no production universe/alert changes.
        # SHADOW reuses the existing connected app and common DataLake.
        # Never allow an experimental scanner to stop live WICKS/Reversal.
        try:
            rudra_scanner_shadow = run_bot_shadow(
                app, trade_date, repo_root=REPO_ROOT, logger=logger,
            )
            logger.info(
                "RUDRA SCANNER | shadow=%s | state=%s | selected=%s | sources=%s | scans=%s",
                rudra_scanner_shadow.get("mode"),
                rudra_scanner_shadow.get("state"),
                rudra_scanner_shadow.get("selected_total", 0),
                rudra_scanner_shadow.get("selected_by_source", {}),
                rudra_scanner_shadow.get("ibkr_scan_states", {}),
            )
        except Exception:
            logger.exception(
                "RUDRA SCANNER | isolated shadow discovery failed; legacy pipeline continues"
            )
            rudra_scanner_shadow = {"mode": "shadow", "state": "ERROR"}

        # 1. Build universe
        rudra_active = (
            rudra_scanner_shadow.get("mode") == "active"
            and rudra_scanner_shadow.get("state") == "ACTIVE_SELECTED"
            and bool(rudra_scanner_shadow.get("candidates"))
        )
        # ACTIVE is explicit opt-in and strictly fail-closed. No extra
        # old percent-mover scanner calls when the new 30-name list
        # is selected; if incomplete, preserve the legacy workflow.
        if gapup_df is None and fetch_gapup_from_app and not rudra_active:
            logger.info("MOVERS | Fetch started")
            gapup_df = ibkr.get_gapup_tickers(app)
            logger.info("MOVERS | Fetch completed | rows=%s", len(gapup_df))

            gapup_tickers = (
                gapup_df["ticker"]
                .dropna()
                .astype(str)
                .str.upper()
                .tolist()
                if "ticker" in gapup_df.columns
                else []
            )

            logger.info(
                "MOVERS | Tickers | %s",
                ", ".join(gapup_tickers) if gapup_tickers else "None",
            )

        if rudra_active:
            # One bounded list shared by Scanner and Reversal (NQ remains
            # a separate Yahoo instrument). No new IBKR app connection.
            uni = pd.DataFrame([
                {"ticker": item["ticker"],
                 "source": "+".join(item["sources"]),
                 "sector": item.get("fixed_sector", "")}
                for item in rudra_scanner_shadow["candidates"]
            ])
        else:
            uni = universe.build_universe(trade_date, gapup_df=gapup_df)
        tickers = (
            uni["ticker"]
            .dropna()
            .astype(str)
            .str.upper()
            .unique()
            .tolist()
        )
        logger.info("UNIVERSE | Built | tickers=%s", len(tickers))

        # 2. Save scanner movers raw file when supplied (legacy filename retained)
        if gapup_df is not None and not gapup_df.empty:
            gapup_file = paths.raw_path("ibkr_gapup.csv", trade_date)
            storage.save_csv(
                ibkr.normalize_gapup(gapup_df),
                gapup_file,
            )
            logger.info("FILE | Saved ibkr_gapup (movers) | %s", gapup_file)

        # 3. 30-day daily OHLCV
        logger.info(
            "YFINANCE | Daily 30D fetch started | tickers=%s",
            len(tickers),
        )
        daily = yfd.get_daily_ohlcv(tickers, days=30)
        logger.info(
            "YFINANCE | Daily 30D fetch completed | rows=%s",
            len(daily),
        )

        daily = daily_features.add_ema20(daily)
        daily = daily_features.add_daily_atr14(daily)

        daily_file = paths.raw_path("daily_30d.csv", trade_date)
        storage.save_csv(daily, daily_file)
        logger.info("FILE | Saved daily_30d | %s", daily_file)

        daily_latest = daily_features.latest_daily_summary(daily)
        logger.info(
            "FEATURES | Daily summary built | rows=%s",
            len(daily_latest),
        )

        # 4. IBKR 5m data
        logger.info(
            "IBKR | 5m fetch started | tickers=%s | duration=3 D | batch_size=5",
            len(tickers),
        )

        ibkr_result = ibkr.get_ibkr_5m_batch(
            app,
            tickers,
            duration="3 D",
            wait_time=20,
            batch_size=5,
        )

        intraday_raw = ibkr.combine_5m(ibkr_result)

        logger.info(
            "IBKR | 5m fetch completed | rows=%s",
            len(intraday_raw),
        )

        intraday_file = paths.raw_path("intraday_5m.csv", trade_date)
        storage.save_csv(intraday_raw, intraday_file)
        logger.info("FILE | Saved intraday_5m | %s", intraday_file)

        # Scanner feature processing uses this SAME IBKR 5M collection.
        # Only explicit shadow mode performs extra work and emits only
        # saved diagnostic/research outputs, NEVER scanner Discord alerts.
        rudra_scanner_features = {"state": "OFF", "alert_delivery": "DISABLED"}
        if rudra_scanner_shadow.get("mode") in ("shadow", "active"):
            try:
                radar_bars, radar_result = evaluate_scanner(
                    intraday_raw, enable_research=False,
                )
                radar_bars, rvol_history = apply_rolling_rvol20(
                    radar_bars, REPO_ROOT, paths.trading_day(trade_date),
                    save=True,
                )
                radar_result["feature_status"]["rvol_state"] = rvol_history["state"]
                radar_result["feature_status"]["rvol20_ready_rows"] = rvol_history["ready_rows"]
                radar_result["volume_history"] = rvol_history
                radar_paths = persist_features(
                    REPO_ROOT, paths.trading_day(trade_date),
                    radar_bars, radar_result,
                )
                rudra_scanner_features = {
                    "state": radar_result["state"],
                    "quality": radar_result["feature_status"],
                    "files": radar_paths,
                    "alert_delivery": "DISABLED",
                }
                logger.info(
                    "RUDRA SCANNER | indicators saved | mode=%s | wap=%s | rvol20=%s",
                    radar_result["state"],
                    radar_result["feature_status"].get("wap_state"),
                    radar_result["feature_status"].get("rvol_state"),
                )
            except Exception:
                logger.exception("RUDRA SCANNER | nonfatal feature stage failure")
                rudra_scanner_features = {
                    "state": "ERROR", "alert_delivery": "DISABLED",
                }

        intraday = intraday_features.add_intraday_features(intraday_raw)
        alert_data = alerts.build_wick_alerts(intraday, trade_date=trade_date)

        # Locked Reversal detection remains unchanged. ACTIVE mode
        # fetches and reuses a bounded 1H source for the same stock
        # candidates and preserves NQ on its independent Yahoo route.
        rudra_scanner_hourly = {"state": "OFF"}
        if rudra_active:
            try:
                rudra_scanner_hourly = refresh_hourly_cache(
                    app, REPO_ROOT, paths.trading_day(trade_date),
                    tickers,
                )
                logger.info(
                    "RUDRA SCANNER | 1H history | state=%s | rows=%s",
                    rudra_scanner_hourly.get("state"),
                    rudra_scanner_hourly.get("rows"),
                )
            except Exception:
                logger.exception("RUDRA SCANNER | 1H collection failed")
                rudra_scanner_hourly = {"state": "ERROR"}

        try:
            if rudra_active:
                # New symbols must NOT replay historical 1H entries.
                # The locked BB detector and prior pending alerts remain
                # unchanged. Seed only after complete 150-bar history.
                seed_status = seed_new_symbols(
                    trade_date, tickers + ["NQ"],
                )
                logger.info(
                    "RUDRA SCANNER | reversal 1H first-use seed=%s | not_ready=%s",
                    seed_status["seeded"],
                    seed_status["not_ready_150h"],
                )
                rudra_scanner_hourly["reversal_seed"] = seed_status
            rudra_reversal_alerts = run_rudra_reversal_strategy(
                trade_date=trade_date,
                tickers=tickers + ["NQ"] if rudra_active else None,
            )
        except Exception:
            # Rudra-Reversal is independent. Never block live WICKS delivery.
            logger.exception("RUDRA REVERSAL 1H | scan failed")
            rudra_reversal_alerts = []

        # Deliver before sector research, report writing and Git submission.
        # Delivery order is WICKS first, then Rudra-Reversal 1H.
        delivery = {
            "alert_data": alert_data,
            "rudra_reversal_alerts": rudra_reversal_alerts,
        }
        if alert_sender is not None:
            sent = alerts.send_alerts(delivery, alert_sender)
            logger.info("ALERTS | Immediate dispatch | events=%s", sent)
        alert_data = delivery["alert_data"]
        rudra_reversal_alerts = delivery["rudra_reversal_alerts"]
        intraday_latest = intraday_features.latest_intraday_summary(
            intraday
        )

        logger.info(
            "FEATURES | Intraday summary built | rows=%s",
            len(intraday_latest),
        )

        # 5. Sector + market context
        if include_sector:
            logger.info("YFINANCE | Sector/market fetch started")
            sector = market.get_market_sector_daily()
            logger.info(
                "YFINANCE | Sector/market fetch completed | rows=%s",
                len(sector),
            )

            sector_file = paths.raw_path(
                "sector_market_daily.csv",
                trade_date,
            )
            storage.save_csv(sector, sector_file)
            logger.info(
                "FILE | Saved sector_market_daily | %s",
                sector_file,
            )
        else:
            sector = pd.DataFrame()
            logger.info("SECTOR | Skipped")

        # Research pattern evaluation is opt-in and uses strict
        # index -> sector -> ticker confirmation after sector data loads.
        # It cannot alter the locked detectors' rules or their state.
        rudra_scanner_research = {
            "state": "OFF", "alert_delivery": "DISABLED"
        }
        if (
            rudra_scanner_shadow.get("mode") in ("active", "shadow")
            and os.environ.get("RUDRA_SCANNER_RESEARCH", "0") == "1"
            and "radar_bars" in locals()
        ):
            try:
                ai_context, _ = read_ai_csv(
                    paths.master_config_path("ai_scanner_list.csv")
                )
                selected_context = rudra_scanner_shadow.get("candidates", [])
                etfs = ticker_etf_from_sources(
                    selected_context, ai_rows=ai_context,
                )
                index_bias, sectors, context_status = classify_topdown(
                    sector, trade_date=paths.trading_day(trade_date),
                    ticker_etfs=etfs,
                )
                allowed_symbols = set(etfs)
                eligible_bars = radar_bars[
                    radar_bars["ticker"].isin(allowed_symbols)
                ].copy()
                events, detector_health = detect_five_patterns(
                    eligible_bars, index_bias=index_bias,
                    sector_bias_by_ticker=sectors,
                    settings=PatternSettings(enabled_for_research=True),
                )
                radar_result["events"] = events
                radar_result["detector_status"] = detector_health
                radar_result["state"] = "EXPERIMENTAL_RESEARCH"
                persist_features(
                    REPO_ROOT, paths.trading_day(trade_date),
                    radar_bars, radar_result,
                )
                rudra_scanner_research = {
                    "state": "EXPERIMENTAL_RESEARCH",
                    "events": len(events),
                    "context": context_status,
                    "alert_delivery": "DISABLED",
                }
                # Both gates must be explicitly set. Unapproved
                # development thresholds cannot send a trading alert.
                send_state = deliver_scanner_alerts(
                    events, alert_sender,
                    state_file=paths.ROOT / "rudra_scanner_delivery_state.json",
                    trade_date=paths.trading_day(trade_date),
                    enabled=os.environ.get("RUDRA_SCANNER_ALERTS") == "1",
                    thresholds_approved=os.environ.get(
                        "RUDRA_SCANNER_THRESHOLDS_APPROVED") == "1",
                )
                rudra_scanner_research["alert_delivery"] = send_state["state"]
                rudra_scanner_research["events_sent"] = send_state["sent"]
                logger.info(
                    "RUDRA SCANNER | research=%s | index=%s | events=%s | delivery=%s",
                    detector_health["state"], index_bias, len(events),
                    send_state["state"],
                )
            except Exception:
                logger.exception("RUDRA SCANNER | research/delivery failed")
                rudra_scanner_research = {
                    "state": "ERROR", "alert_delivery": "NOT_CONFIRMED",
                }

        # 6. Processed ticker summary + snapshot
        ticker_summary = snapshot.build_ticker_summary(
            uni,
            intraday_summary=intraday_latest,
            daily_summary=daily_latest,
        )

        summary_file = paths.processed_path(
            "ticker_summary.csv",
            trade_date,
        )
        storage.save_csv(
            ticker_summary,
            summary_file,
        )

        logger.info(
            "FILE | Saved ticker_summary | rows=%s | %s",
            len(ticker_summary),
            summary_file,
        )

        snap = snapshot.build_snapshot_dict(
            paths.trading_day(trade_date),
            ticker_summary,
            sector_summary=sector,
        )

        snapshot_file = paths.processed_path(
            "asjr_snapshot.json",
            trade_date,
        )

        storage.save_json(
            snap,
            snapshot_file,
        )

        logger.info(
            "FILE | Saved asjr_snapshot | %s",
            snapshot_file,
        )

        print("Universe:", len(tickers))
        print("Intraday Rows:", len(intraday_raw))
        print("Ticker Summary:", len(ticker_summary))
        print("Snapshot:", snapshot_file)

        logger.info(
            "RUN | DATA COMPLETE | universe=%s | intraday_rows=%s | ticker_summary=%s",
            len(tickers),
            len(intraday_raw),
            len(ticker_summary),
        )

        # 7. Verify generated files and submit DataLake
        git_result = None

        if git_submit:
            required_files = [
                config_file,
                daily_file,
                intraday_file,
                summary_file,
                snapshot_file,
            ]

            if include_sector:
                required_files.append(sector_file)

            if gapup_df is not None and not gapup_df.empty:
                required_files.append(gapup_file)

            logger.info(
                "GIT | File verification started | count=%s",
                len(required_files),
            )

            git_result = asjr_git.submit_datalake(
                trade_date=paths.trading_day(trade_date),
                day_dir=paths.day_dir(trade_date),
                required_files=required_files,
                logger=logger,
            )

        # The day's folder was already committed above. Do not append to its
        # tracked log after Git submit: a dirty prior-day log blocks the next
        # session's pull --rebase when only the new day is staged.
        print("RUN | SUCCESS | log_file:", log_file)

        return {
            "universe": uni,
            "daily": daily,
            "intraday_raw": intraday_raw,
            "intraday": intraday,
            "alerts_dispatched": delivery.get("alerts_dispatched", False),
            "alert_data": alert_data,
            "rudra_reversal_alerts": rudra_reversal_alerts,
            "rudra_scanner_shadow": rudra_scanner_shadow,
            "rudra_scanner_features": rudra_scanner_features,
            "rudra_scanner_hourly": rudra_scanner_hourly,
            "rudra_scanner_research": rudra_scanner_research,
            "sector": sector,
            "ticker_summary": ticker_summary,
            "snapshot": snap,
            "git": git_result,
            "log_file": str(log_file),
        }

    except Exception:
        logger.exception("RUN | FAILED")
        raise


def prepare_alert(result):
    """Compatibility formatter; use alert_sender to send every wick immediately."""
    return alerts.prepare_alert(result)


def mark_alert_sent():
    """Acknowledge the prepared Discord wick batch after successful send."""
    return alerts.mark_alert_sent()



def send_alerts(result, sender):
    """Send WICKS first, then Rudra-Reversal 1H."""
    return alerts.send_alerts(result, sender)
