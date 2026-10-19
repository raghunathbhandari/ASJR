#!/usr/bin/env python3
"""READ-ONLY 1-year NQ CSV archive coverage and integrity audit; no strategies."""
from pathlib import Path
import pandas as pd
ROOT=Path("RudraScanner/ResearchData/Gann")
SOURCES=[ROOT/"Source/BARS/NQ_1min_2025-01-01_2025-12-31_stitched.csv",ROOT/"Source/BARS/NQ_1min_2026-01-01_2026-10-08_stitched.csv"]
def main():
    failed=False
    for path in SOURCES:
        if not path.exists():
            print("MISSING |",path);failed=True;continue
        d=pd.read_csv(path)
        required={"datetime","open","high","low","close"}
        if not required.issubset(d.columns):
            print("INVALID HEADERS |",path,d.columns.tolist());failed=True;continue
        ts=pd.to_datetime(d.datetime,utc=True,errors="coerce")
        bad=int(ts.isna().sum())
        duplicates=int(ts.duplicated().sum())
        out_of_order=int((ts.diff().dropna()<pd.Timedelta(0)).sum())
        ohlc=d[["open","high","low","close"]].apply(pd.to_numeric,errors="coerce")
        invalid=int((ohlc.isna().any(axis=1)|(ohlc.high<ohlc.low)|(ohlc.high<ohlc[["open","close"]].max(axis=1))|(ohlc.low>ohlc[["open","close"]].min(axis=1))).sum())
        month=ts.dt.tz_convert("America/New_York").dt.to_period("M").astype(str).value_counts().sort_index()
        print("FILE |",path.name,"| rows",len(d),"| first",ts.iloc[0],"| last",ts.iloc[-1],"| bad_ts",bad,"| duplicates",duplicates,"| ordering",out_of_order,"| invalid_ohlc",invalid)
        print("MONTHS |",", ".join(f"{k}:{v}" for k,v in month.items()))
        if bad or duplicates or out_of_order or invalid:failed=True
    sessions=sorted(ROOT.glob("NQ_2026-??-??_5m.csv"))
    print("ASJR 5M SESSION FILES |",len(sessions),"| first",sessions[0].name if sessions else "-","| last",sessions[-1].name if sessions else "-")
    for file in sessions:
        d=pd.read_csv(file)
        needed={"datetime_ny","Open","High","Low","Close"}
        if not needed.issubset(d.columns) or d.empty:
            failed=True;print("INVALID SESSION |",file.name)
    print("AUDIT |", "FAIL" if failed else "PASS (basic structure only; roll/gap audit separate)")
    return int(failed)
if __name__=="__main__":raise SystemExit(main())
