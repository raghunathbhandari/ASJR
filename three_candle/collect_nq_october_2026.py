#!/usr/bin/env python3
"""Bridge-only NQ October 2026 five-minute history collector.

Writes a single validated CSV plus coverage JSON to three_candle/data via an
isolated Git clone. Do not touch the live trading worktree or any other files.
Missing candles remain missing. All OHLCV prices come from Yahoo NQ=F.
"""
from __future__ import annotations
import json
import subprocess
import tempfile
from pathlib import Path
import pandas as pd
import yfinance as yf

REPO = Path("/root/trading/ASJR")
DEST = Path("three_candle/data")
COLS = ["Open", "High", "Low", "Close", "Volume"]

def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, timeout=120, check=False)

def main() -> int:
    pieces = []
    failures = []
    for first, last in [
        ("2026-09-28", "2026-10-05"),
        ("2026-10-05", "2026-10-12"),
        ("2026-10-12", "2026-10-19"),
        ("2026-10-19", "2026-10-26"),
        ("2026-10-26", "2026-11-01"),
    ]:
        try:
            x = yf.download("NQ=F", start=first, end=last, interval="5m",
                            prepost=True, auto_adjust=False, progress=False,
                            threads=False, multi_level_index=False)
            if x is None or x.empty or x.index.tz is None:
                failures.append({"chunk":first, "reason":"empty"})
                continue
            if isinstance(x.columns, pd.MultiIndex):
                x.columns = x.columns.get_level_values(0)
            if not set(COLS).issubset(x):
                failures.append({"chunk":first, "reason":"missing columns"})
                continue
            pieces.append(x[COLS].apply(pd.to_numeric, errors="coerce")
                          .dropna(subset=COLS[:4]))
        except Exception as e:
            failures.append({"chunk":first, "reason":type(e).__name__})
    if not pieces:
        print("NQ OCT 2026 | FAILED | no 5m history; " + json.dumps(failures))
        return 1
    x = pd.concat(pieces).sort_index()
    x = x.loc[~x.index.duplicated(keep="last")]
    x = x.tz_convert("UTC")
    x = x.loc[(x.index >= pd.Timestamp("2026-10-01",tz="UTC")) &
              (x.index < pd.Timestamp("2026-11-01",tz="UTC"))].copy()
    # Reject any elementary OHLC envelope defects and extreme 5m ranges.
    previous = x.Close.shift()
    bad = ((x.High-x.Low)/previous > 0.02) & (previous>0)
    bad |= x.High < x[["Open","Low","Close"]].max(axis=1)
    bad |= x.Low > x[["Open","High","Close"]].min(axis=1)
    bad_timestamps = [str(t) for t in x.index[bad]]
    x = x.loc[~bad]
    if x.empty:
        print("NQ OCT 2026 | FAILED | all bars rejected")
        return 1
    x.index.name = "Datetime_UK"  # 29–31 Oct 2026 is GMT, earlier dates are BST!
    # Use explicit UTC name to avoid confusing early October BST with UTC.
    x.index.name = "Datetime_UTC"
    daily = x.groupby(x.index.tz_convert("America/New_York").date).size()
    coverage = {
        "symbol":"NQ=F", "source":"Yahoo Finance 5m", "timezone":"UTC",
        "requested_calendar_dates":"2026-10-01 through 2026-10-30",
        "first_timestamp":str(x.index.min()), "last_timestamp":str(x.index.max()),
        "rows":int(len(x)), "observed_ny_dates":{str(k):int(v) for k,v in daily.items()},
        "quarantined_bar_timestamps_utc":bad_timestamps,
        "failed_chunks":failures,
        "complete_month_verified":False,
        "notes":"Observed row counts are not proof of full exchange session coverage. Review missing 5m bars before backtesting.",
    }
    with tempfile.TemporaryDirectory(prefix="three_candle_oct_export_") as temp:
        folder=Path(temp)/"repo"
        clone=subprocess.run(["git","clone","-q","--no-checkout","--shared",
                              str(REPO),str(folder)],capture_output=True,timeout=120)
        if clone.returncode: raise RuntimeError("local clone failed")
        origin=git(REPO,"remote","get-url","origin")
        if origin.returncode or "github.com" not in origin.stdout:
            raise RuntimeError("origin validation failed")
        git(folder,"remote","set-url","origin",origin.stdout.strip())
        git(folder,"config","user.name","ASJR Research Bridge")
        git(folder,"config","user.email","asjr-research-bridge@users.noreply.github.com")
        for attempt in range(4):
            if git(folder,"fetch","-q","origin","main").returncode: continue
            if git(folder,"checkout","-q","-B","oct-research","FETCH_HEAD").returncode: continue
            target=folder/DEST
            target.mkdir(parents=True,exist_ok=True)
            x.to_csv(target/"NQ_2026-10_5m_UTC.csv")
            (target/"NQ_2026-10_coverage.json").write_text(
                json.dumps(coverage,indent=2)+"\n",encoding="utf-8")
            rels=[str(DEST/"NQ_2026-10_5m_UTC.csv"),
                  str(DEST/"NQ_2026-10_coverage.json")]
            if git(folder,"add","--",*rels).returncode: continue
            if git(folder,"diff","--cached","--quiet").returncode==0:
                print("NQ OCT 2026 | SUCCESS | UNCHANGED | "+str(len(x))+" rows")
                return 0
            if git(folder,"commit","-qm","Research export NQ Oct 2026 5m and coverage").returncode:
                continue
            if git(folder,"push","-q","origin","HEAD:refs/heads/main").returncode==0:
                print("NQ OCT 2026 | SUCCESS | PUSHED | "+str(len(x))+" rows")
                print("FILES | "+", ".join(rels))
                print("FAILED CHUNKS | "+str(len(failures)))
                return 0
    print("NQ OCT 2026 | FAILED | push retries exhausted")
    return 2

if __name__=="__main__":
    raise SystemExit(main())
