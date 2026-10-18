#!/usr/bin/env python3
"""Rudra-Gann: Yahoo NQ=F 5m gap downloader, with explicit historical limit.

Never fabricate missing 5m bars. Save per-NY-session research files only.
Use in isolated /root/trading/ASJR-Gann checkout; no Chakra or broker orders.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import yfinance as yf

DEST=Path("RudraScanner/ResearchData/Gann")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",default="2025-12-12")
    p.add_argument("--end",default="2026-01-19")
    p.add_argument("--latest",action="store_true",help="Download last ~59 days instead")
    args=p.parse_args()
    today=pd.Timestamp.now(tz="UTC").normalize()
    start=pd.Timestamp(args.start,tz="UTC")
    end=pd.Timestamp(args.end,tz="UTC")
    if args.latest:
        end=today
        start=today-pd.Timedelta(days=59)
    if end<start:p.error("end before start")
    earliest=today-pd.Timedelta(days=59)
    if start<earliest:
        print(f"YAHOO 5M | UNAVAILABLE | requested {start.date()} to {end.date()}")
        print(f"YAHOO 5M | historical 5m limited to roughly last 60 days; earliest safe request {earliest.date()}")
        print("MISSING DATA | use IBKR dated FUT or another licensed history provider; do not build false 5m candles from 1H")
        return 3
    try:
        d=yf.download("NQ=F",start=start.date().isoformat(),
                 end=(end+pd.Timedelta(days=1)).date().isoformat(),
                 interval="5m",auto_adjust=False,prepost=True,
                 threads=False,progress=False,multi_level_index=False)
    except Exception as exc:
        print("YAHOO 5M | DOWNLOAD ERROR |",type(exc).__name__,str(exc)[:120]);return 2
    if d is None or d.empty:
        print("YAHOO 5M | 0 BARS | no files saved");return 2
    if isinstance(d.columns,pd.MultiIndex):d.columns=d.columns.get_level_values(0)
    if d.index.tz is None:
        print("YAHOO 5M | INVALID | timezone missing");return 2
    ny=d.tz_convert("America/New_York")
    cols=["Open","High","Low","Close","Volume"]
    if not set(cols).issubset(ny.columns):
        print("YAHOO 5M | INVALID | missing OHLCV");return 2
    ny=ny[cols].dropna(subset=cols[:4])
    count=0
    for session,group in ny.groupby(ny.index.date):
        if not(start.date()<=session<=end.date()):continue
        if len(group)<20:
            print(f"YAHOO 5M | SKIP | {session}: {len(group)} candles");continue
        out=DEST/f"NQ_{session}_5m.csv"
        if out.exists():
            print(f"YAHOO 5M | EXISTING | {session}, no overwrite")
            continue
        out.parent.mkdir(parents=True,exist_ok=True)
        group.index.name="datetime_ny"
        group.to_csv(out)
        count+=1
        print(f"YAHOO 5M | SAVED | {session} | {len(group)} bars | {out}")
    print(f"YAHOO 5M | COMPLETE | {count} new session files (local isolated worktree; not automatically committed)")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
