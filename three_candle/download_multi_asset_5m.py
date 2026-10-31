#!/usr/bin/env python3
"""Download 5-minute OHLCV research data for 10 stock/FX/futures symbols.

Run: python three_candle/download_multi_asset_5m.py --days 55
Or:  python three_candle/download_multi_asset_5m.py --start 2026-09-01 --end 2026-10-31

Dependencies: pip install yfinance pandas
End date is exclusive. Yahoo typically retains only ~60 days for 5m data.
Missing historical data is reported explicitly; never silently synthetic-fill.
Output UTC CSVs plus download manifest. NQ=F and GC=F are continuous
Yahoo futures; contract-roll artifacts exist; FX reported Volume is commonly
zero (not tick volume). Data is research-only, not executable tick history.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf

SYMBOLS = {
    "MU": ("MU", "STOCK"),
    "INTC": ("INTC", "STOCK"),
    "NVDA": ("NVDA", "STOCK"),
    "AMD": ("AMD", "STOCK"),
    "WDC": ("WDC", "STOCK"),
    "EURUSD": ("EURUSD=X", "FX"),
    "GBPUSD": ("GBPUSD=X", "FX"),
    "USDJPY": ("JPY=X", "FX"),
    "NQ": ("NQ=F", "FUTURES"),
    "GOLD": ("GC=F", "FUTURES"),
}
BASE = Path(__file__).resolve().parent / "data" / "multi_asset_5m"

def normalize(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    names = ["Open", "High", "Low", "Close", "Volume"]
    if any(k not in df for k in names):
        raise ValueError(f"Missing OHLCV columns: {df.columns.tolist()}")
    df = df[names].copy()
    if df.index.tz is None:
        raise ValueError("Downloaded index missing timezone")
    df.index = df.index.tz_convert("UTC")
    df.index.name = "Datetime_UTC"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    return df

def fetch(ticker, start, end, chunk_days=5):
    chunks, errors = [], []
    cursor = start
    while cursor < end:
        stop = min(cursor + timedelta(days=chunk_days), end)
        try:
            df = yf.download(ticker, start=cursor.date().isoformat(),
                             end=stop.date().isoformat(), interval="5m",
                             prepost=True, auto_adjust=False,
                             threads=False, progress=False)
            if not df.empty:
                chunks.append(normalize(df))
            else:
                errors.append(f"{cursor.date()}..{stop.date()}: empty")
        except Exception as exc:
            errors.append(f"{cursor.date()}..{stop.date()}: {str(exc)[:160]}")
        cursor = stop
        time.sleep(0.3)
    if not chunks:
        return pd.DataFrame(), errors
    whole = pd.concat(chunks).sort_index()
    whole = whole[~whole.index.duplicated(keep="last")]
    whole = whole.loc[(whole.index >= pd.Timestamp(start)) &
                      (whole.index < pd.Timestamp(end))]
    return whole, errors

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=55)
    ap.add_argument("--start", type=str)
    ap.add_argument("--end", type=str)
    ap.add_argument("--symbols", nargs="+", choices=tuple(SYMBOLS))
    args = ap.parse_args()
    if args.start and args.end:
        start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    elif args.start or args.end:
        ap.error("Provide both --start and --end, or neither.")
    else:
        now = datetime.now(timezone.utc)
        end = datetime.combine(now.date()+timedelta(days=1),
                               datetime.min.time(), tzinfo=timezone.utc)
        start = end - timedelta(days=args.days)
    if not start < end:
        ap.error("End must be after start")
    BASE.mkdir(parents=True, exist_ok=True)
    manifest = {"requested_utc": [start.isoformat(), end.isoformat()],
                "created_utc":datetime.now(timezone.utc).isoformat(),
                "source":"Yahoo Finance yfinance 5m, extended hours requested",
                "symbols":{}}
    for symbol in (args.symbols or SYMBOLS.keys()):
        ticker, asset = SYMBOLS[symbol]
        print(f"Downloading {symbol} ({ticker})", flush=True)
        df, errors = fetch(ticker,start,end)
        status = "NO_DATA" if df.empty else ("PARTIAL_OR_UNVERIFIED" if errors else "DOWNLOADED_COVERAGE_UNVERIFIED")
        record = {"ticker":ticker,"class":asset,"status":status,
                  "rows":len(df),"errors":errors,
                  "start_utc":None,"end_utc":None,"file":None}
        if not df.empty:
            path=BASE/f"{symbol}_{start:%Y%m%d}_{end:%Y%m%d}_5m_UTC.csv"
            df.to_csv(path,float_format="%.10g")
            record.update(file=str(path.relative_to(Path(__file__).resolve().parents[1])),
                          start_utc=df.index.min().isoformat(),
                          end_utc=df.index.max().isoformat(),
                          zero_volume_rows=int((df.Volume==0).sum()),
                          unique_days=int(df.index.normalize().nunique()))
        manifest["symbols"][symbol]=record
        print(f"  {status}: {len(df)} candles; errors={len(errors)}",flush=True)
    dest=BASE/"download_manifest.json"
    dest.write_text(json.dumps(manifest,indent=2))
    print(f"\nManifest: {dest}")
    print("Downloaded rows do NOT prove complete market/session coverage. Check gaps before backtesting.")
    if any(x["status"]=="NO_DATA" for x in manifest["symbols"].values()):
        sys.exit(2)

if __name__=="__main__":
    main()
