#!/usr/bin/env python3
"""NQ=F 5-minute Yahoo import for a user-selected research date.
Publishes research CSV only via isolated scratch clone; never touches Chakra.
"""
import io
import argparse
from datetime import date, timedelta
import subprocess
import tempfile
from pathlib import Path
import pandas as pd
import yfinance as yf

REPO=Path("/root/trading/ASJR")
DEST_ROOT=Path("RudraScanner/ResearchData/Gann")

def git(cwd,*args):
    return subprocess.run(["git",*args],cwd=cwd,capture_output=True,text=True,timeout=90)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--date",default="2026-10-16",help="NY session YYYY-MM-DD")
    args=parser.parse_args()
    session=date.fromisoformat(args.date)
    dest=DEST_ROOT/f"NQ_{session:%Y-%m-%d}_5m.csv"
    start=(session-timedelta(days=1)).isoformat()
    end=(session+timedelta(days=2)).isoformat()
    df=yf.download("NQ=F",start=start,end=end,
                   interval="5m",prepost=True,auto_adjust=False,
                   progress=False,threads=False,multi_level_index=False)
    if df is None or df.empty:
        print("NQ IMPORT | FAILED | Yahoo returned zero rows")
        return 1
    if isinstance(df.columns,pd.MultiIndex):
        df.columns=df.columns.get_level_values(0)
    if df.index.tz is None:
        print("NQ IMPORT | FAILED | timezone missing")
        return 1
    ny=df.tz_convert("America/New_York")
    ny=ny[ny.index.strftime("%Y-%m-%d")==args.date]
    cols=["Open","High","Low","Close","Volume"]
    if ny.empty or any(c not in ny for c in cols):
        print("NQ IMPORT | FAILED | no requested session 5m OHLCV")
        return 1
    ny=ny[cols].dropna(subset=cols[:4])
    if len(ny)<20 or ny.index.duplicated().any() or not ny.index.is_monotonic_increasing:
        print("NQ IMPORT | FAILED | incomplete or duplicate candles")
        return 1
    ny.index.name="datetime_ny"
    with tempfile.TemporaryDirectory(prefix="asjr_gann_nq_") as tmp:
        folder=Path(tmp)/"repo"
        cp=subprocess.run(["git","clone","-q","--no-checkout","--shared",str(REPO),str(folder)],
                          capture_output=True,text=True,timeout=90)
        if cp.returncode:
            print("NQ IMPORT | FAILED | isolated clone");return 1
        remote=git(REPO,"remote","get-url","origin")
        if remote.returncode or "github.com" not in remote.stdout:
            print("NQ IMPORT | FAILED | origin");return 1
        git(folder,"remote","set-url","origin",remote.stdout.strip())
        git(folder,"config","user.name","ASJR Research Bridge")
        git(folder,"config","user.email","asjr-research-bridge@users.noreply.github.com")
        for attempt in range(4):
            if git(folder,"fetch","-q","origin","main").returncode: continue
            if git(folder,"checkout","-q","-B","nq-import-tmp","FETCH_HEAD").returncode: continue
            target=folder/dest
            target.parent.mkdir(parents=True,exist_ok=True)
            ny.to_csv(target)
            if git(folder,"add","--",str(dest)).returncode: continue
            if git(folder,"diff","--cached","--quiet").returncode==0:
                print(f"NQ IMPORT | SUCCESS | {len(ny)} candles | UNCHANGED | {dest}")
                return 0
            if git(folder,"commit","-qm",f"Research: NQ {args.date} 5m Yahoo candles").returncode: continue
            if git(folder,"push","-q","origin","HEAD:refs/heads/main").returncode==0:
                print(f"NQ IMPORT | SUCCESS | {len(ny)} candles | PUSHED | {dest}")
                print(f"First {ny.index[0]} | Last {ny.index[-1]}")
                return 0
    print("NQ IMPORT | FAILED | could not publish to GitHub");return 1

if __name__=="__main__":
    raise SystemExit(main())
