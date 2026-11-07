#!/usr/bin/env python3
"""Download 5-minute MESZ2026 and MNQZ2026 IBKR history, 1–6 Nov 2026.

Read-only IBKR Gateway port 4002. Saves new CSVs locally; does not git push.
Existing files are never overwritten.
"""
from datetime import date, datetime, time as daytime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from ib_insync import IB, Future

START = date(2026, 11, 1)
END = date(2026, 11, 6)
EXPIRY = "202612"
SYMBOLS = ("MES", "MNQ")
DEST = Path("/root/trading/ASJR/three_candle/data")
UK = ZoneInfo("Europe/London")


def download(ib: IB, symbol: str) -> None:
    filename = f"{symbol}Z2026_IBKR_5m_{START}_to_{END}.csv"
    target = DEST / filename
    if target.exists():
        print(f"{symbol}: SKIPPED (file exists): {target}", flush=True)
        return

    qualified = ib.qualifyContracts(
        Future(symbol=symbol, lastTradeDateOrContractMonth=EXPIRY,
               exchange="CME", currency="USD")
    )
    if len(qualified) != 1:
        raise RuntimeError(f"{symbol}: contract qualification returned {len(qualified)} matches")
    contract = qualified[0]

    rows = []
    errors = []
    for offset in range((END - START).days + 1):
        day = START + timedelta(days=offset)
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
    ib = IB()
    try:
        ib.connect("127.0.0.1", 4002, clientId=893, readonly=True, timeout=20)
        for symbol in SYMBOLS:
            try:
                download(ib, symbol)
            except Exception as exc:
                print(f"{symbol} FAILED: {exc}", flush=True)
    finally:
        if ib.isConnected():
            ib.disconnect()


if __name__ == "__main__":
    main()
