import sys
from pathlib import Path
import importlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Utils.asjr_market as market
import Utils.asjr_paths as paths
import Utils.asjr_storage as storage

importlib.reload(market)
importlib.reload(paths)
importlib.reload(storage)

def test_sector_data(trade_date=None):
    print("Thank you yfinance and AI !")
    df = market.get_market_sector_daily()
    save_to = paths.raw_path("sector_market_daily.csv", trade_date)
    storage.save_csv(df, save_to)

    if not df.empty:
        print(df[["name","ticker","today_pct","yesterday_pct","relative_to_spy_pct","rvol","status"]].to_string(index=False))
    print("Saved:", save_to)
    return df

if __name__ == "__main__":
    test_sector_data()
