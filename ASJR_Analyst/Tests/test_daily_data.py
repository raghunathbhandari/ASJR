import sys
from pathlib import Path
import importlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Utils.asjr_paths as paths
import Utils.asjr_storage as storage
import Utils.asjr_yfinance as yfd
import Utils.asjr_features as features

importlib.reload(paths)
importlib.reload(storage)
importlib.reload(yfd)
importlib.reload(features)

def test_daily_data(tickers=None, trade_date=None):
    print("Thank you yfinance and AI !")
    tickers = tickers or ["AAPL", "INTC", "SPY", "QQQ"]

    df = yfd.get_daily_ohlcv(tickers, days=30)
    if df.empty:
        print("NO DAILY DATA")
        return df

    df = features.add_ema20(df)
    df = features.add_daily_atr14(df)

    save_to = paths.raw_path("daily_30d.csv", trade_date)
    storage.save_csv(df, save_to)

    latest = features.latest_daily_summary(df)
    print(latest[["ticker", "date", "close", "volume", "ema20", "dist_ema20_pct", "atr14"]].to_string(index=False))
    print("Saved:", save_to)
    return df

if __name__ == "__main__":
    test_daily_data()
