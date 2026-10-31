#!/usr/bin/env python3
"""Fill September NQ 5m Yahoo gaps from archived Gann daily files.
Run in /root/trading/ASJR-Synced; publish only September merged CSV and
coverage JSON with a separate temporary git clone. No live worktree edits.
"""
import json
import subprocess
import tempfile
from pathlib import Path
import pandas as pd

REPO=Path("/root/trading/ASJR-Synced")
OUT=Path("three_candle/data")
ARCH=Path("RudraScanner/ResearchData/Gann")
COLS=["Open","High","Low","Close","Volume"]

def git(cwd,*args):
    return subprocess.run(["git",*args],cwd=cwd,text=True,capture_output=True,timeout=120)

def main():
    source=REPO/OUT/"NQ_2026-09_5m_UTC.csv"
    cov_source=REPO/OUT/"NQ_2026-09_coverage.json"
    if not source.is_file() or not cov_source.is_file():
        raise SystemExit("Missing original September CSV / coverage; run git fetch+merge in synced checkout first")
    main=pd.read_csv(source,index_col=0,parse_dates=True)
    main.index=pd.to_datetime(main.index,utc=True)
    main=main[COLS].apply(pd.to_numeric,errors="coerce")
    archived=[]
    for day in ("01","02","03","04"):
        path=REPO/ARCH/f"NQ_2026-09-{day}_5m.csv"
        if not path.is_file():
            raise SystemExit(f"Missing archived source: {path}")
        df=pd.read_csv(path,index_col=0,parse_dates=True)
        df.index=pd.to_datetime(df.index,utc=True)
        archived.append(df[COLS].apply(pd.to_numeric,errors="coerce"))
    prior=len(main)
    arc=pd.concat(archived).sort_index()
    merged=pd.concat([main,arc]).sort_index()
    merged=merged.loc[~merged.index.duplicated(keep="first")]
    merged=merged[(merged.index>=pd.Timestamp("2026-09-01",tz="UTC")) &
                  (merged.index<pd.Timestamp("2026-10-01",tz="UTC"))]
    bad=(merged.High<merged[["Open","Close","Low"]].max(axis=1)) | (merged.Low>merged[["Open","Close","High"]].min(axis=1))
    if bad.any():
        raise SystemExit(f"Invalid OHLC envelopes in archive: {int(bad.sum())}; REFUSING publish")
    if len(merged)<=prior: raise SystemExit("No historical coverage added")
    merged.index.name="Datetime_UTC"
    ny=merged.index.tz_convert("America/New_York")
    minutes=ny.hour*60+ny.minute
    rth=(minutes>=570)&(minutes<960)
    original=json.loads(cov_source.read_text(encoding="utf8"))
    original.update({
       "merge_sources":[str(ARCH/f"NQ_2026-09-{d}_5m.csv") for d in ("01","02","03","04")],
       "merged_utc_5m_csv":str(OUT/"NQ_2026-09_5m_UTC.csv"),
       "rows":len(merged),"added_archived_rows":len(merged)-prior,
       "first_timestamp":str(merged.index.min()),"last_timestamp":str(merged.index.max()),
       "rth_5m_bars":int(rth.sum()),"extended_non_rth_5m_bars":int((~rth).sum()),
       "observed_ny_dates":{str(d):int(v) for d,v in merged.groupby(ny.date).size().items()},
       "remaining_gap_note":"Archived daily files cover NY Sep 1-4; NY Sep 6 evening / Sep 7 Labor Day availability needs separate audit.",
       "complete_month_verified":False,
    })
    with tempfile.TemporaryDirectory(prefix="sep_archive_merge_") as temp:
        folder=Path(temp)/"repo"
        cp=subprocess.run(["git","clone","-q","--no-checkout","--shared",str(REPO),str(folder)],capture_output=True,timeout=120)
        if cp.returncode:raise SystemExit("Could not clone synced repo")
        origin=git(REPO,"remote","get-url","origin")
        if origin.returncode or "github.com" not in origin.stdout:raise SystemExit("Git origin invalid")
        for args in [("remote","set-url","origin",origin.stdout.strip()),("config","user.name","ASJR Research"),("config","user.email","asjr-research@users.noreply.github.com")]:
            if git(folder,*args).returncode:raise SystemExit("Git config failed")
        for attempt in range(4):
            if git(folder,"fetch","-q","origin","main").returncode:continue
            if git(folder,"checkout","-q","-B","sep-archive-tmp","FETCH_HEAD").returncode:continue
            target=folder/OUT;target.mkdir(parents=True,exist_ok=True)
            merged.to_csv(target/"NQ_2026-09_5m_UTC.csv")
            (target/"NQ_2026-09_coverage.json").write_text(json.dumps(original,indent=2)+"\n",encoding="utf8")
            if git(folder,"add","--",str(OUT/"NQ_2026-09_5m_UTC.csv"),str(OUT/"NQ_2026-09_coverage.json")).returncode:continue
            if git(folder,"commit","-qm","Merge archived Sep 1-4 NQ 5m into September extended dataset").returncode:continue
            if git(folder,"push","-q","origin","HEAD:refs/heads/main").returncode==0:
                print(f"NQ SEPTEMBER | PUSHED | {len(merged)} bars | {len(merged)-prior} archived bars added")
                print(f"Coverage: {merged.index.min()} .. {merged.index.max()}")
                print("AUDIT | Sep 6 evening / Sep 7 holiday not yet guaranteed")
                return
    raise SystemExit("Git publication failed; original data unchanged")

if __name__=="__main__":
    main()
