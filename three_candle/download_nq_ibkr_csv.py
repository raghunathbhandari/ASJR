"""Download historical NQZ2026 5-minute futures bars from IBKR Gateway.

Run on the VPS from repository root:
    python three_candle/download_nq_ibkr_csv.py --start 2026-10-29 --end 2026-10-30

Requirements:
    pip install ib_insync pandas
Gateway must be running and CME historical-data permission must be available.
This script only requests market data and writes a CSV; it places no orders.
"""

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import time

import pandas as pd
from ib_insync import IB, Future, util


def download_nq_ibkr_csv(start, end, host="127.0.0.1", port=1045,
                         client_id=79, output=None):
    """Save NQ Dec-2026 5m ETH OHLCV to a UK-time CSV.

    Times are returned by IBKR and converted through UTC to Europe/London.
    The request is chunked into single calendar days to avoid large pacing queries.
    """
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)
    if last < first:
        raise ValueError("--end must be on/after --start")

    # Dec 2026 NQ futures contract, not a continuous/auto-roll symbol.
    contract = Future(symbol="NQ", lastTradeDateOrContractMonth="202612",
                      exchange="CME", currency="USD")
    ib = IB()
    rows = []
    try:
        ib.connect(host, port, clientId=client_id, timeout=20, readonly=True)
        qualified = ib.qualifyContracts(contract)
        if len(qualified) != 1:
            raise RuntimeError("Unable to qualify Dec-2026 NQ futures contract")
        print(f"IBKR contract: {qualified[0]}")

        # Include the full end date, by requesting to the following midnight UTC.
        # Calendar-day chunks overlap at most at the boundary; duplicates removed.
        current = first
        while current <= last:
            chunk_end = datetime.combine(current + timedelta(days=1),
                                         datetime.min.time(), tzinfo=timezone.utc)
            print(f"Requesting {current} (5 mins, ETH)...")
            bars = ib.reqHistoricalData(
                qualified[0],
                endDateTime=chunk_end.strftime("%Y%m%d %H:%M:%S UTC"),
                durationStr="2 D", barSizeSetting="5 mins",
                whatToShow="TRADES", useRTH=False, formatDate=2,
                keepUpToDate=False,
            )
            if not bars:
                print(f"  WARNING: no bars for {current}")
            else:
                frame = util.df(bars)
                if "date" not in frame:
                    print("  WARNING: no date field")
                else:
                    timestamps = pd.to_datetime(frame["date"], utc=True)
                    day_rows = frame.loc[timestamps.dt.date == current].copy()
                    day_rows["Datetime_UTC"] = timestamps.loc[day_rows.index]
                    rows.append(day_rows)
                    print(f"  {len(day_rows)} candles")
            current += timedelta(days=1)
            time.sleep(1.0)  # modest pacing between requests
    finally:
        if ib.isConnected():
            ib.disconnect()

    if not rows:
        raise RuntimeError("IBKR returned no candles; no CSV was written")

    data = pd.concat(rows, ignore_index=True)
    data = data.drop_duplicates(subset=["Datetime_UTC"]).sort_values("Datetime_UTC")
    data["Datetime_UK"] = data["Datetime_UTC"].dt.tz_convert("Europe/London")
    rename = {"open": "Open", "high": "High", "low": "Low",
              "close": "Close", "volume": "Volume"}
    data = data.rename(columns=rename)
    columns = ["Datetime_UK", "Datetime_UTC", "Open", "High", "Low", "Close", "Volume"]
    data = data[columns]

    path = Path(output) if output else (
        Path(__file__).resolve().parent / "data" /
        f"NQZ2026_IBKR_5m_{start}_to_{end}.csv"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False)
    print(f"Saved {len(data)} rows to: {path}")
    print("Review missing timestamps, outliers and exchange maintenance breaks before backtesting.")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IBKR NQZ2026 historical ETH CSV export")
    parser.add_argument("--start", default="2026-10-29")
    parser.add_argument("--end", default="2026-10-30")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1045)
    parser.add_argument("--client-id", type=int, default=79)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    download_nq_ibkr_csv(args.start, args.end, host=args.host, port=args.port,
                         client_id=args.client_id, output=args.output)
