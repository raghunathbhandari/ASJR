"""Download NQZ2026 and GCZ2026 5m IBKR ETH data for Sep/Oct 2026.

Run on VPS (read-only historical data):
/root/trading/venv_new/bin/python three_candle/download_nq_gc_ibkr_months.py --port 4002

Requires ib_insync and pandas. Does not place orders or restart Gateway.
Each successful contract/month writes CSV and a coverage text report.
Incomplete data is labelled, never filled with synthetic candles.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import time

import pandas as pd
from ib_insync import IB, Future, util


CONTRACTS = {
    "NQ": dict(symbol="NQ", lastTradeDateOrContractMonth="202612",
               exchange="CME", currency="USD"),
    "GC": dict(symbol="GC", lastTradeDateOrContractMonth="202612",
               exchange="COMEX", currency="USD"),
}
MONTHS = [(2026, 9), (2026, 10)]
OUTPUT_DIR = Path(__file__).resolve().parent / "data"


def one_month_dates(year, month):
    first = date(year, month, 1)
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    return first, next_month


def request_one_day(ib, contract, day):
    # Request at most two calendar days; keep the UTC rows for day only.
    end_utc = datetime.combine(day + timedelta(days=1), datetime.min.time(),
                               tzinfo=timezone.utc)
    bars = ib.reqHistoricalData(
        contract, endDateTime=end_utc.strftime("%Y%m%d %H:%M:%S UTC"),
        durationStr="2 D", barSizeSetting="5 mins",
        whatToShow="TRADES", useRTH=False, formatDate=2,
        keepUpToDate=False, timeout=50,
    )
    if not bars:
        return pd.DataFrame()
    frame = util.df(bars)
    frame["Datetime_UTC"] = pd.to_datetime(frame["date"], utc=True)
    return frame.loc[frame.Datetime_UTC.dt.date == day].copy()


def coverage_report(frame, start, end, errors):
    """Audit time gaps; no assumption that exchange maintenance is missing data."""
    lines = [f"Requested UTC dates: {start} through {end - timedelta(days=1)}",
             f"Actual rows: {len(frame)}",
             f"Request errors: {len(errors)}"]
    lines += [f"  {entry}" for entry in errors]
    if frame.empty:
        lines.append("STATUS: EMPTY")
        return "\n".join(lines) + "\n"

    intervals = frame.Datetime_UTC.diff().dropna()
    gaps = intervals[intervals > pd.Timedelta(minutes=5)]
    lines.append(f"Gaps larger than 5 minutes: {len(gaps)} "
                 "(includes normal maintenance/weekends)")
    for index, duration in gaps.items():
        lines.append(f"  gap ends {frame.loc[index, 'Datetime_UK']}: {duration}")
    previous_close = frame.Close.shift()
    suspicious = ((frame.High - frame.Low) / previous_close > 0.02) & (previous_close > 0)
    invalid = ((frame.High < frame[["Open", "Close", "Low"]].max(axis=1))
               | (frame.Low > frame[["Open", "Close", "High"]].min(axis=1)))
    lines.append(f"Large 5m ranges (>2% prior close): {int(suspicious.sum())}")
    lines.append(f"Invalid OHLC envelopes: {int(invalid.sum())}")
    for _, row in frame.loc[suspicious | invalid].iterrows():
        lines.append(f"  REVIEW {row.Datetime_UK} O={row.Open} H={row.High} "
                     f"L={row.Low} C={row.Close}")
    lines.append("STATUS: NEEDS REVIEW (not certified complete)")
    return "\n".join(lines) + "\n"


def download_month(ib, contract, ticker, year, month, pause):
    start, end = one_month_dates(year, month)
    frames, errors = [], []
    current = start
    print(f"\n{ticker} {year}-{month:02d}: requesting UTC days {start} to {end - timedelta(days=1)}",
          flush=True)
    while current < end:
        try:
            daily = request_one_day(ib, contract, current)
            if not daily.empty:
                frames.append(daily)
            print(f"  {current}: {len(daily)} rows", flush=True)
        except Exception as exc:
            message = f"{current}: {type(exc).__name__}: {exc}"
            errors.append(message)
            print(f"  ERROR {message}", flush=True)
        current += timedelta(days=1)
        time.sleep(pause)

    if not frames:
        print(f"  WARNING: no data for {ticker} {year}-{month:02d}; CSV not written")
        return
    frame = pd.concat(frames, ignore_index=True)
    frame = frame.sort_values("Datetime_UTC").drop_duplicates("Datetime_UTC")
    frame = frame.loc[
        (frame.Datetime_UTC.dt.date >= start)
        & (frame.Datetime_UTC.dt.date < end)
    ].reset_index(drop=True)
    frame["Datetime_UK"] = frame.Datetime_UTC.dt.tz_convert("Europe/London")
    frame = frame.rename(columns={"open": "Open", "high": "High", "low": "Low",
                                  "close": "Close", "volume": "Volume"})
    columns = ["Datetime_UK", "Datetime_UTC", "Open", "High", "Low", "Close", "Volume"]
    label = f"{ticker}Z2026_IBKR_5m_{year}-{month:02d}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv = OUTPUT_DIR / f"{label}.csv"
    report = OUTPUT_DIR / f"{label}_coverage.txt"

    # Save independent monthly outputs; never rewrite another contract's data.
    frame[columns].to_csv(csv, index=False)
    report.write_text(coverage_report(frame, start, end, errors), encoding="utf-8")
    print(f"  SAVED {len(frame)} bars: {csv}", flush=True)
    print(f"  AUDIT: {report}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4002)
    parser.add_argument("--client-id", type=int, default=79)
    parser.add_argument("--pause", type=float, default=2.0)
    parser.add_argument("--symbols", nargs="+", choices=["NQ", "GC"],
                        default=["NQ", "GC"])
    parser.add_argument("--months", nargs="+", choices=["2026-09", "2026-10"],
                        default=["2026-09", "2026-10"])
    args = parser.parse_args()

    ib = IB()
    try:
        ib.connect(args.host, args.port, clientId=args.client_id,
                   timeout=20, readonly=True)
        for ticker in args.symbols:
            qualified = ib.qualifyContracts(Future(**CONTRACTS[ticker]))
            if len(qualified) != 1:
                print(f"ERROR: could not qualify {ticker} Dec-2026; skipping.")
                continue
            print(f"Qualified {ticker}: {qualified[0]}", flush=True)
            for value in args.months:
                year, month = map(int, value.split("-"))
                download_month(ib, qualified[0], ticker, year, month, args.pause)
    finally:
        if ib.isConnected():
            ib.disconnect()


if __name__ == "__main__":
    main()
