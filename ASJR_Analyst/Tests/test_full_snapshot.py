import sys
from pathlib import Path
import importlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Utils.asjr_paths as paths
import Utils.asjr_storage as storage
import Utils.asjr_features as features

importlib.reload(paths)
importlib.reload(storage)
importlib.reload(features)

def test_build_snapshot(trade_date=None):
    daily_file = paths.raw_path("daily_30d.csv", trade_date)
    if not Path(daily_file).exists():
        print("Missing:", daily_file)
        print("Run test_daily_data() first.")
        return pd.DataFrame()

    df = storage.load_csv(daily_file)
    latest = features.latest_daily_summary(df)

    out = paths.processed_path("ticker_summary.csv", trade_date)
    storage.save_csv(latest, out)

    snapshot = {
        "trade_date": paths.trading_day(trade_date),
        "ticker_count": int(latest["ticker"].nunique()) if not latest.empty else 0,
        "tickers": latest.to_dict(orient="records"),
    }
    snapshot_file = paths.processed_path("asjr_snapshot.json", trade_date)
    storage.save_json(snapshot, snapshot_file)

    print("Summary:", out)
    print("Snapshot:", snapshot_file)
    return latest

if __name__ == "__main__":
    test_build_snapshot()
