import sys
from pathlib import Path
import importlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Utils.asjr_paths as paths
import Utils.asjr_storage as storage
import Utils.asjr_watchlist as watchlist
import Utils.asjr_universe as universe
import Utils.asjr_ibkr as ibkr
import Utils.asjr_yfinance as yfd
import Utils.asjr_features as daily_features
import Utils.asjr_intraday_features as intraday_features
import Utils.asjr_market as market
import Utils.asjr_snapshot as snapshot
import Utils.asjr_git as asjr_git
import Utils.asjr_logger as asjr_logger

for m in (
    paths, storage, watchlist, universe, ibkr, yfd,
    daily_features, intraday_features, market, snapshot,
    asjr_git, asjr_logger
):
    importlib.reload(m)


def run_asjr_manual_pipeline(
    app,
    trade_date=None,
    gapup_df=None,
    fetch_gapup_from_app=False,
    include_sector=True,
    git_submit=True,
):
    print("Thank you IBKR, yfinance and AI !")

    log_file = asjr_logger.run_log_path(
        paths.day_dir(trade_date) / "reports"
    )
    logger = asjr_logger.get_run_logger(log_file)

    logger.info("RUN | START | trade_date=%s", paths.trading_day(trade_date))
    logger.info(
        "RUN | OPTIONS | include_sector=%s | git_submit=%s | fetch_gapup_from_app=%s",
        include_sector,
        git_submit,
        fetch_gapup_from_app,
    )

    try:
        # 1. Build universe
        if gapup_df is None and fetch_gapup_from_app:
            logger.info("GAPUP | Fetch started")
            gapup_df = ibkr.get_gapup_tickers(app)
            logger.info("GAPUP | Fetch completed | rows=%s", len(gapup_df))

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

        # 2. Save gap-up raw file when supplied
        if gapup_df is not None and not gapup_df.empty:
            gapup_file = paths.raw_path("ibkr_gapup.csv", trade_date)
            storage.save_csv(
                ibkr.normalize_gapup(gapup_df),
                gapup_file,
            )
            logger.info("FILE | Saved ibkr_gapup | %s", gapup_file)

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

        logger.info("RUN | SUCCESS | log_file=%s", log_file)

        return {
            "universe": uni,
            "daily": daily,
            "intraday_raw": intraday_raw,
            "intraday": intraday,
            "sector": sector,
            "ticker_summary": ticker_summary,
            "snapshot": snap,
            "git": git_result,
            "log_file": str(log_file),
        }

    except Exception:
        logger.exception("RUN | FAILED")
        raise
