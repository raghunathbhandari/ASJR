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

for m in (
    paths, storage, watchlist, universe, ibkr, yfd,
    daily_features, intraday_features, market, snapshot
):
    importlib.reload(m)

def run_asjr_manual_pipeline(
    app,
    trade_date=None,
    gapup_df=None,
    fetch_gapup_from_app=False,
    include_sector=True,
):
    print("Thank you IBKR, yfinance and AI !")

    # 1. Build universe
    if gapup_df is None and fetch_gapup_from_app:
        gapup_df = ibkr.get_gapup_tickers(app)

    uni = universe.build_universe(trade_date, gapup_df=gapup_df)
    tickers = uni["ticker"].dropna().astype(str).str.upper().unique().tolist()

    # 2. Save gap-up raw file when supplied
    if gapup_df is not None and not gapup_df.empty:
        storage.save_csv(
            ibkr.normalize_gapup(gapup_df),
            paths.raw_path("ibkr_gapup.csv", trade_date)
        )

    # 3. 30-day daily OHLCV
    daily = yfd.get_daily_ohlcv(tickers, days=30)
    daily = daily_features.add_ema20(daily)
    daily = daily_features.add_daily_atr14(daily)
    storage.save_csv(daily, paths.raw_path("daily_30d.csv", trade_date))
    daily_latest = daily_features.latest_daily_summary(daily)

    # 4. IBKR 5m data
    ibkr_result = ibkr.get_ibkr_5m_batch(
        app, tickers, duration="3 D", wait_time=20, batch_size=5
    )
    intraday_raw = ibkr.combine_5m(ibkr_result)
    storage.save_csv(intraday_raw, paths.raw_path("intraday_5m.csv", trade_date))

    intraday = intraday_features.add_intraday_features(intraday_raw)
    intraday_latest = intraday_features.latest_intraday_summary(intraday)

    # 5. Sector + market context
    sector = market.get_market_sector_daily() if include_sector else pd.DataFrame()
    if include_sector:
        storage.save_csv(sector, paths.raw_path("sector_market_daily.csv", trade_date))

    # 6. Processed ticker summary + snapshot
    ticker_summary = snapshot.build_ticker_summary(
        uni,
        intraday_summary=intraday_latest,
        daily_summary=daily_latest,
    )
    storage.save_csv(
        ticker_summary,
        paths.processed_path("ticker_summary.csv", trade_date)
    )

    snap = snapshot.build_snapshot_dict(
        paths.trading_day(trade_date),
        ticker_summary,
        sector_summary=sector,
    )
    storage.save_json(
        snap,
        paths.processed_path("asjr_snapshot.json", trade_date)
    )

    print("Universe:", len(tickers))
    print("Intraday Rows:", len(intraday_raw))
    print("Ticker Summary:", len(ticker_summary))
    print("Snapshot:", paths.processed_path("asjr_snapshot.json", trade_date))
    return {
        "universe": uni,
        "daily": daily,
        "intraday_raw": intraday_raw,
        "intraday": intraday,
        "sector": sector,
        "ticker_summary": ticker_summary,
        "snapshot": snap,
    }
