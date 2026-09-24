import sys
from pathlib import Path
import importlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Utils.asjr_ibkr as ibkr
import Utils.asjr_paths as paths
import Utils.asjr_storage as storage
import Utils.asjr_watchlist as watchlist

importlib.reload(ibkr)
importlib.reload(paths)
importlib.reload(storage)
importlib.reload(watchlist)

def test_ibkr_5m(app, tickers=None, trade_date=None, duration="3 D"):
    print("Thank you IBKR and AI !")

    tickers = tickers or watchlist.fixed_tickers(trade_date)
    result = ibkr.get_ibkr_5m_batch(
        app,
        tickers,
        duration=duration,
        wait_time=20,
        batch_size=5,
    )

    combined = ibkr.combine_5m(result)
    save_to = paths.raw_path("intraday_5m.csv", trade_date)
    storage.save_csv(combined, save_to)

    print("Tickers:", len(tickers))
    print("Rows:", len(combined))
    print("Saved:", save_to)
    return result, combined
