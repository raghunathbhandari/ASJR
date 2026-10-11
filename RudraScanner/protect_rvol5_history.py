#!/usr/bin/env python3
"""Migrate and validate the RVOL5 baseline before dated DataLake cleanup.

No IBKR connection; never deletes data. Safely copies newest available
snapshot to the durable state file, MERGING existing rows if present.
"""
import argparse
import os
import sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from RudraScanner.premarket_rvol import (
    _clean_reference, durable_reference_path, reference_path, FIELDS
)

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--for-day",default="2026-10-12")
    args=p.parse_args(argv)
    source=reference_path(ROOT,args.for_day)
    dest=durable_reference_path(ROOT)
    frames=[]
    for path in (dest,source):
        if path.is_file():
            frame=pd.read_csv(path)
            if not set(FIELDS).issubset(frame.columns):
                print("REFUSED: Invalid reference columns:",path)
                return 2
            frames.append(frame)
    if not frames:
        print("REFUSED: No original RVOL5 reference present.")
        return 2
    merged=_clean_reference(pd.concat(frames,ignore_index=True),args.for_day)
    if merged.empty:
        print("REFUSED: No validated prior-day RVOL5 data")
        return 2
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix(".tmp")
    tmp.write_text(merged.to_csv(index=False),encoding="utf-8")
    os.replace(tmp,dest)
    check=pd.read_csv(dest)
    if len(check)!=len(merged):
        print("ERROR: Durable reference verification failed")
        return 2
    print("RVOL5 DURABLE | SAVED",dest)
    print("ROWS:",len(check))
    summary=check.groupby(["ticker","session"])["session_date_et"].nunique()
    print("TICKERS:",check["ticker"].nunique())
    print("READY GROUPS (>=5 complete dates):",int((summary>=5).sum()))
    print("SAFE TO CLEAN DATED FILES? Durable baseline verified; audit cleanup script separately.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
