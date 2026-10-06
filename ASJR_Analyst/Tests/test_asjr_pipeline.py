import sys
from pathlib import Path
import importlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
import Strategies.MeanReversal4Pct.mean_reversal as mean_reversal

try:
    from Backtesting.DataLoader.forex_download_hook import launch_forex_download_once
except Exception:
    launch_forex_download_once = None

ASJR_ANALYST_VERSION = "2026.10.06.3"

for m in (
    paths, asjr_day, storage, watchlist, universe, ibkr, yfd,
    daily_features, intraday_features, alerts, market, snapshot,
    asjr_git, asjr_logger, mean_reversal
):
    importlib.reload(m)


def run_mean_reversal_strategy(daily, intraday, trade_date=None):
    """Run the isolated 4% mean-reversal detector."""
    return mean_reversal.build_mean_reversal_alerts(
        daily=daily,
        intraday=intraday,
        trade_date=trade_date,
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
                "alert_data": [], "mean_reversal_alerts": [], "sector": pd.DataFrame(),
                "ticker_summary": pd.DataFrame(),
                "snapshot": {"trade_date": str(pd.Timestamp.now(tz=asjr_day.ET).date())},
                "git": {"status": "SKIPPED_CLOSED_SESSION"}, "log_file": None,
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


    try:
        # 1. Build universe
        if gapup_df is None and fetch_gapup_from_app:
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

        intraday = intraday_features.add_intraday_features(intraday_raw)
        alert_data = alerts.build_wick_alerts(intraday, trade_date=trade_date)
        mean_reversal_alerts = run_mean_reversal_strategy(
            daily=daily,
            intraday=intraday,
            trade_date=trade_date,
        )
        # Deliver before sector research, report writing and Git submission.
        delivery = {"alert_data": alert_data, "mean_reversal_alerts": mean_reversal_alerts}
        if alert_sender is not None:
            sent = alerts.send_alerts(delivery, alert_sender)
            logger.info("ALERTS | Immediate dispatch | events=%s", sent)
        alert_data = delivery["alert_data"]
        mean_reversal_alerts = delivery["mean_reversal_alerts"]
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
            "mean_reversal_alerts": mean_reversal_alerts,
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
    """Send all wicks in one alert during this schedule, wicks first."""
    return alerts.send_alerts(result, sender)
