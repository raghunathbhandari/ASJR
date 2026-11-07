#!/usr/bin/env python3
"""Download reusable 5-minute MES/MNQ IBKR history for a date range.

Read-only IBKR Gateway port 4002. Saves new CSVs locally; does not git push.
Existing files are never overwritten.
"""
import argparse
from datetime import date, datetime, time as daytime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from ib_insync import IB, Future

SYMBOLS = ("MES", "MNQ")
DEST = Path("/root/trading/ASJR/three_candle/data")
UK = ZoneInfo("Europe/London")


def download(ib: IB, symbol: str, start: date, end: date, expiry: str) -> None:
    filename = f"{symbol}_{expiry}_IBKR_5m_{start}_to_{end}.csv"
    target = DEST / filename
    if target.exists():
        print(f"{symbol}: SKIPPED (file exists): {target}", flush=True)
        return

    qualified = ib.qualifyContracts(
        Future(symbol=symbol, lastTradeDateOrContractMonth=expiry,
               exchange="CME", currency="USD")
    )
    if len(qualified) != 1:
        raise RuntimeError(f"{symbol}: contract qualification returned {len(qualified)} matches")
    contract = qualified[0]

    rows = []
    errors = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        until = datetime.combine(day + timedelta(days=1), daytime.min, timezone.utc)
        try:
            bars = ib.reqHistoricalData(
                contract,
                endDateTime=until.strftime("%Y%m%d %H:%M:%S UTC"),
                durationStr="2 D",
                barSizeSetting="5 mins",
                whatToShow="TRADES",
                useRTH=False,
                formatDate=2,
                keepUpToDate=False,
                timeout=50,
            )
            day_rows = 0
            for bar in bars:
                ts = pd.Timestamp(bar.date)
                ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
                if ts.date() != day:
                    continue
                rows.append({
                    "Datetime_UTC": ts.isoformat(),
                    "Datetime_UK": ts.tz_convert(UK).isoformat(),
                    "Open": bar.open,
                    "High": bar.high,
                    "Low": bar.low,
                    "Close": bar.close,
                    "Volume": bar.volume,
                })
                day_rows += 1
            print(f"{symbol} | {day} UTC | {day_rows} candles", flush=True)
        except Exception as exc:
            errors.append(f"{day}: {exc}")
            print(f"{symbol} | {day} | ERROR: {exc}", flush=True)
        ib.sleep(1.2)

    if errors:
        raise RuntimeError(f"{symbol}: {len(errors)} request failures; refusing partial CSV: {errors}")
    if not rows:
        raise RuntimeError(f"{symbol}: no history returned")

    frame = (pd.DataFrame(rows)
             .drop_duplicates(subset="Datetime_UTC")
             .sort_values("Datetime_UTC"))
    DEST.mkdir(parents=True, exist_ok=True)
    # Exclusive-create: never clobber an existing historical file.
    with target.open("x", encoding="utf-8", newline="") as output:
        frame.to_csv(output, index=False)
    print(f"{symbol} | SAVED {len(frame)} candles | {target}", flush=True)
    print(f"UK first: {frame.iloc[0]['Datetime_UK']} | last: {frame.iloc[-1]['Datetime_UK']}", flush=True)
    print("Coverage is not certified; inspect expected exchange-session gaps.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only IBKR MES/MNQ 5-minute exporter")
    parser.add_argument("--start", help="YYYY-MM-DD, inclusive; use with --end")
    parser.add_argument("--end", help="YYYY-MM-DD, inclusive; use with --start")
    parser.add_argument("--days", type=int, default=6,
                        help="Default: most recent N completed UTC days (default: 6)")
    parser.add_argument("--expiry", default="202612",
                        help="Explicit YYYYMM futures contract; default Dec 2026")
    args = parser.parse_args()

    if bool(args.start) != bool(args.end):
        parser.error("--start and --end must be supplied together")
    if args.days < 1 or args.days > 31:
        parser.error("--days must be 1 through 31")
    if len(args.expiry) != 6 or not args.expiry.isdigit():
        parser.error("--expiry must be YYYYMM")

    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    if args.start:
        try:
            start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
        except ValueError:
            parser.error("Dates must use YYYY-MM-DD")
    else:
        end = yesterday
        start = end - timedelta(days=args.days - 1)

    if end < start or (end - start).days > 30:
        parser.error("Range must be 1–31 calendar days inclusive")
    if end > yesterday:
        parser.error("End must be a completed UTC day (yesterday or earlier)")

    print(f"IBKR MES/MNQ | {start} to {end} UTC | expiry {args.expiry}", flush=True)
    ib = IB()
    try:
        ib.connect("127.0.0.1", 4002, clientId=893, readonly=True, timeout=20)
        for symbol in SYMBOLS:
            try:
                download(ib, symbol, start, end, args.expiry)
            except Exception as exc:
                print(f"{symbol} FAILED: {exc}", flush=True)
    finally:
        if ib.isConnected():
            ib.disconnect()


if __name__ == "__main__":
    main()
