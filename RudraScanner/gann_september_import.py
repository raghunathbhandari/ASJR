#!/usr/bin/env python3
"""Research-only September 2026 NQ 5m import; prefer saved local NQ 60d dataset."""
from __future__ import annotations
import subprocess
import tempfile
from datetime import date
from pathlib import Path
import pandas as pd
import yfinance as yf

REPO=Path("/root/trading/ASJR")
DEST=Path("RudraScanner/ResearchData/Gann")
FIRST=date(2026,9,1)
LAST=date(2026,9,30)
def git(cwd,*args):
    return subprocess.run(["git",*args],cwd=cwd,text=True,capture_output=True,timeout=120)

def main():
    local=REPO/"Backtesting/BacktestData/OpenSource/NQ/NQ_5m_60d.csv"
    ny=None
    if local.is_file():
        try:
            old=pd.read_csv(local)
            col="Datetime" if "Datetime" in old.columns else "datetime_ny"
            if col in old.columns and all(k in old.columns for k in ["Open","High","Low","Close","Volume"]):
                old[col]=pd.to_datetime(old[col],utc=True)
                old=old.dropna(subset=[col]).set_index(col)
                existing=old.tz_convert("America/New_York")
                if len(existing.loc[(existing.index.date>=FIRST)&(existing.index.date<=LAST)])>500:
                    ny=existing
                    print("GANN SEPTEMBER | SOURCE | existing local NQ_5m_60d.csv")
        except (ValueError,KeyError,TypeError) as exc:
            print("GANN SEPTEMBER | LOCAL SKIPPED |",type(exc).__name__)
    if ny is None:
        df=yf.download("NQ=F",start="2026-08-31",end="2026-10-02",
                       interval="5m",prepost=True,auto_adjust=False,
                       progress=False,threads=False,multi_level_index=False)
        if df is None or df.empty or df.index.tz is None:
            print("GANN SEPTEMBER | FAILED | Yahoo data unavailable");return 1
        if isinstance(df.columns,pd.MultiIndex):
            df.columns=df.columns.get_level_values(0)
        ny=df.tz_convert("America/New_York")
        print("GANN SEPTEMBER | SOURCE | Yahoo NQ=F 5m")
    cols=["Open","High","Low","Close","Volume"]
    if any(x not in ny.columns for x in cols):
        print("GANN SEPTEMBER | FAILED | columns");return 1
    batch={}
    for day in pd.date_range(FIRST,LAST,freq="B"):
        sub=ny.loc[ny.index.strftime("%Y-%m-%d")==str(day.date()),cols].dropna(subset=cols[:4])
        if len(sub)<50 or sub.index.duplicated().any():
            print(f"GANN SEPTEMBER | MISSING | {day.date()} | {len(sub)} rows")
            continue
        sub.index.name="datetime_ny"
        batch[day.date().isoformat()]=sub
    if not batch:
        print("GANN SEPTEMBER | FAILED | no valid NY sessions");return 1
    with tempfile.TemporaryDirectory(prefix="gann_oct_") as temp:
        folder=Path(temp)/"repo"
        cp=subprocess.run(["git","clone","-q","--no-checkout","--shared",str(REPO),str(folder)],
                          text=True,capture_output=True,timeout=120)
        if cp.returncode:return 2
        remote=git(REPO,"remote","get-url","origin")
        if remote.returncode or "github.com" not in remote.stdout:return 2
        git(folder,"remote","set-url","origin",remote.stdout.strip())
        git(folder,"config","user.name","ASJR Research Bridge")
        git(folder,"config","user.email","asjr-research-bridge@users.noreply.github.com")
        for attempt in range(4):
            if git(folder,"fetch","-q","origin","main").returncode:continue
            if git(folder,"checkout","-q","-B","oct-temp","FETCH_HEAD").returncode:continue
            paths=[]
            for day,sub in batch.items():
                rel=DEST/f"NQ_{day}_5m.csv"
                dest=folder/rel
                dest.parent.mkdir(parents=True,exist_ok=True)
                sub.to_csv(dest)
                paths.append(str(rel))
            if git(folder,"add","--",*paths).returncode:continue
            if git(folder,"diff","--cached","--quiet").returncode==0:
                print(f"GANN SEPTEMBER | SUCCESS | {len(batch)} sessions | UNCHANGED");return 0
            if git(folder,"commit","-qm","Research NQ September 2026 5m OHLCV").returncode:continue
            if git(folder,"push","-q","origin","HEAD:refs/heads/main").returncode==0:
                print(f"GANN SEPTEMBER | SUCCESS | {len(batch)} sessions | PUSHED")
                print("DAYS | "+", ".join(batch))
                return 0
    print("GANN SEPTEMBER | FAILED | publish retries exhausted")
    return 1
if __name__=="__main__":
    raise SystemExit(main())
