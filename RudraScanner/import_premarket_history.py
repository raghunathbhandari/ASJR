#!/usr/bin/env python3
"""One-off Friday FIXED + refreshed AI + saved Friday IBKR mover RVOL5 import.
No live scanners, orders, alerts, scheduler, or git push. Bot must be stopped.
"""
from __future__ import annotations
import argparse, fcntl, importlib.util, json, os, sys, time, csv
from datetime import datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from RudraScanner.discovery import read_ai_csv, EXCLUDED
from RudraScanner.universe import read_fixed_watchlist
from RudraScanner.run_now import bot_running, RUN_LOCK, CHAKRA_FILE
from RudraScanner.premarket_rvol import normalize_bars, _complete_profiles, _clean_reference, reference_path, FIELDS

def source_tickers(day):
    fixed, fs = read_fixed_watchlist(ROOT, day)
    ai, ast = read_ai_csv(ROOT / "ASJR_Analyst/config/ai_scanner_list.csv")
    friday = ROOT / "ASJR_Analyst/DataLake" / day / "raw/ibkr_gapup.csv"
    with friday.open(newline="", encoding="utf-8-sig") as fh:
        ibkr = [r["ticker"].upper().strip() for r in csv.DictReader(fh)]
    # Preserve provenance. A saved Friday mover list is NOT a fresh IBKR scan.
    values = []
    for source, names in (("FIXED", [r["ticker"] for r in fixed]),
                          ("AI", [r["ticker"] for r in ai]),
                          ("IBKR_FRIDAY_SAVED_MOVERS", ibkr)):
        for ticker in names:
            if ticker and ticker not in EXCLUDED and ticker not in [x["ticker"] for x in values]:
                values.append({"ticker": ticker, "source": source})
    return values, {"fixed": fs, "ai": ast, "ibkr_file": str(friday),
                    "ibkr_friday_count": len(ibkr)}

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--day", default="2026-10-09")
    p.add_argument("--max-tickers", type=int, default=30)
    p.add_argument("--duration", default="10 D")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if not 1 <= args.max_tickers <= 150:
        p.error("--max-tickers must be between 1 and 150")
    try:
        names, status = source_tickers(args.day)
    except (OSError, KeyError, ValueError) as exc:
        print("RUDRA IMPORT | source error:", exc); return 2
    names = names[:args.max_tickers]
    print("RUDRA IMPORT |", args.day, "|", len(names), "selected")
    print("SOURCES:", json.dumps(status, default=str))
    print("TICKERS:", ", ".join(x["ticker"] for x in names), flush=True)
    if args.dry_run: return 0
    if bot_running():
        print("RUDRA IMPORT | STOP trading_bot first; live app must not overlap"); return 2
    RUN_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOCK.open("a+") as lk:
        try: fcntl.flock(lk, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print("RUDRA IMPORT | BUSY"); return 2
        if bot_running(): return 2
        for d in (str(CHAKRA_FILE.parent.parent),str(CHAKRA_FILE.parent)):
            if d not in sys.path: sys.path.insert(0,d)
        spec = importlib.util.spec_from_file_location("chakra_history_only",CHAKRA_FILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from ASJR_Analyst.Utils.asjr_ibkr import get_ibkr_5m_batch
        app = None
        root = ROOT / "ASJR_Analyst/DataLake" / args.day
        rawdir = root / "raw/rudra_premarket_history"
        reportpath = root / "reports/rudra_premarket_backfill.json"
        rawdir.mkdir(parents=True,exist_ok=True)
        reportpath.parent.mkdir(parents=True,exist_ok=True)
        report = {"day":args.day,"sources":status,"duration":args.duration,
                  "entries":[],"mode":"HISTORY_ONLY_NO_ALERT_NO_ORDER"}
        profiles = []
        try:
            app = module.connect_ib_gateway(None)
            if app is None or not app.isConnected():
                print("RUDRA IMPORT | IBKR unavailable");return 2
            for ix, item in enumerate(names,1):
                ticker=item["ticker"]
                result={"ticker":ticker,"source":item["source"],"rows":0,
                        "complete_prior_sessions":{},"state":"NO_DATA"}
                print(f"RUDRA IMPORT | {ix}/{len(names)} {ticker}",flush=True)
                try:
                    frame=get_ibkr_5m_batch(app,[ticker],duration=args.duration,
                                             batch_size=1,wait_time=25).get(ticker)
                    if frame is not None and not frame.empty:
                        frame.reset_index().to_csv(rawdir / f"{ticker}_5m.csv",index=False)
                        values=frame.reset_index().rename(columns={"Date":"datetime",
                                                                    "Volume":"volume"})
                        values["ticker"]=ticker
                        clean=_complete_profiles(normalize_bars(values),
                                                 before_day="2026-10-12")
                        if not clean.empty:
                            profiles.append(clean)
                            count=clean.groupby("session")["session_date_et"].nunique()
                            result["complete_prior_sessions"]={str(k):int(v) for k,v in count.items()}
                        result["rows"]=len(frame)
                        result["state"]="FETCHED"
                except Exception as e:
                    result["state"]="ERROR"; result["error"]=str(e)
                report["entries"].append(result)
                reportpath.write_text(json.dumps(report,indent=2,default=str)+"\n")
                time.sleep(2)
            if profiles:
                ref=_clean_reference(pd.concat(profiles,ignore_index=True),"2026-10-12")
                if not ref.empty:
                    dest=reference_path(ROOT,"2026-10-12")
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    tmp=dest.with_suffix(".tmp")
                    tmp.write_text(ref.to_csv(index=False))
                    os.replace(tmp,dest)
                    report["reference_path"]=str(dest)
                    report["reference_rows"]=len(ref)
            reportpath.write_text(json.dumps(report,indent=2,default=str)+"\n")
            print("RUDRA IMPORT | FINISHED",reportpath,flush=True)
            return 0
        finally:
            if app is not None:
                try:app.disconnect()
                except Exception:pass

if __name__=="__main__":
    raise SystemExit(main())
