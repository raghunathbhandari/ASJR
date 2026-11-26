#!/usr/bin/env python3
"""Rudra-HotSectorHotStock Phase 2: 18 days, historical 09:45 ET top 10 stocks.

Modes: universe (freeze latest State Street ETF holdings), download (IBKR 15m,
monthly stock exports published automatically), rank (daily 09:45 rankings).
Today's holdings are a RETROSPECTIVE PROXY, NOT point-in-time Nov 2026 lists.
Historical data only; does not trade or change production bot services.
"""
import argparse
import csv
import io
import re
import subprocess
import tempfile
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, time as clock
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path("/root/trading/ASJR")
PY=Path("/root/trading/venv_new/bin/python")
DOWNLOADER=ROOT/"three_candle/ibkr_bridge_range_download.py"
WORK=Path("/root/trading/ASJR_research_logs/hot_sector/phase2")
FROZEN=WORK/"frozen_sector_holdings.csv"
SECTORS=("XLK","XLY","XLV","XLE","XLC","XLP","XLB")
DAYS=[("2026-11-02","XLY"),("2026-11-03","XLK"),("2026-11-04","XLK"),
      ("2026-11-05","XLE"),("2026-11-06","XLV"),("2026-11-09","XLY"),
      ("2026-11-10","XLK"),("2026-11-11","XLP"),("2026-11-12","XLK"),
      ("2026-11-13","XLC"),("2026-11-16","XLK"),("2026-11-17","XLB"),
      ("2026-11-18","XLY"),("2026-11-19","XLK"),("2026-11-20","XLY"),
      ("2026-11-23","XLV"),("2026-11-24","XLV"),("2026-11-25","XLE")]
NY=ZoneInfo("America/New_York")
HOLDINGS_URL=("https://www.ssga.com/us/en/intermediary/etfs/library-content/"
              "products/fund-data/etfs/us/holdings-daily-us-en-{}.xlsx")

def git(*args,check=True,cwd=ROOT):
    r=subprocess.run(["git",*args],cwd=cwd,capture_output=True,text=True)
    if check and r.returncode:raise RuntimeError("git "+str(args)+" failed: "+r.stderr[:400])
    return r

def refresh():
    git("fetch","-q","origin","main:refs/remotes/origin/main")
    return git("ls-tree","-r","--name-only","origin/main",
               "three_candle/data/ibkr_bridge").stdout.splitlines()

def universe():
    try:import pandas as pd
    except ImportError:raise RuntimeError("Pandas required to parse official XLSX")
    WORK.mkdir(parents=True,exist_ok=True)
    rows=[]
    for sector in SECTORS:
        url=HOLDINGS_URL.format(sector.lower())
        print("HOLDINGS",sector,url,flush=True)
        req=urllib.request.Request(url,headers={"User-Agent":"ASJR/1.0 research"})
        with urllib.request.urlopen(req,timeout=35) as res:payload=res.read(8_000_000)
        if not payload.startswith(b"PK"):raise RuntimeError(sector+" response is not XLSX")
        try:raw=pd.read_excel(io.BytesIO(payload),header=None,dtype=str)
        except ImportError:raise RuntimeError("Install openpyxl into VPS Python to read XLSX")
        head=None
        for i in range(min(25,len(raw))):
            if "ticker" in [str(x).strip().lower() for x in raw.iloc[i]]:
                head=i;break
        if head is None:raise RuntimeError(sector+": Ticker column not found")
        cols={str(x).strip().lower():j for j,x in enumerate(raw.iloc[head])}
        k=cols["ticker"];cur=cols.get("local currency");cls=cols.get("asset class")
        tickers=set()
        for _,rec in raw.iloc[head+1:].iterrows():
            ticker=str(rec.iloc[k]).strip().upper()
            if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}",ticker):continue
            if cur is not None and str(rec.iloc[cur]).strip().upper() not in ("USD","NAN",""):continue
            if cls is not None:
                typ=str(rec.iloc[cls]).strip().lower()
                if typ not in ("equity","equities","stock","stocks","common stock","nan",""):continue
            tickers.add(ticker)
        if len(tickers)<8:raise RuntimeError(sector+": suspiciously few holdings")
        now=datetime.now(ZoneInfo("UTC")).isoformat()
        for ticker in sorted(tickers):
            rows.append([sector,ticker,url,now,"RETROSPECTIVE_PROXY_NOT_POINT_IN_TIME"])
        print("FOUND",sector,len(tickers),flush=True)
        time.sleep(1)
    with FROZEN.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        w.writerow(["sector_etf","ticker","source_url","retrieved_utc","membership_quality"])
        w.writerows(rows)
    print("SAVED",FROZEN,"constituent rows",len(rows))
    print("WARNING: Holdings downloaded now may differ from November 2026 membership.")

def groups():
    if not FROZEN.exists():raise RuntimeError("Run --mode universe first")
    g=defaultdict(set)
    for r in csv.DictReader(FROZEN.open(encoding="utf-8")):
        if r["sector_etf"] in SECTORS:g[r["sector_etf"]].add(r["ticker"])
    if any(len(g[s])<8 for s in SECTORS):raise RuntimeError("Unverified incomplete holdings")
    return g

def files(paths):
    mapping={}
    regex=re.compile(r"three_candle/data/ibkr_bridge/[^/]+/([A-Z0-9.\-]+)_2026-11-01_2026-11-25_(15min|5min)_UTC\.csv$")
    for p in paths:
        match=regex.fullmatch(p)
        if match:
            ticker,interval=match.groups()
            if ticker not in mapping or interval=="15min":mapping[ticker]=(p,interval)
    return mapping

def download(limit):
    g=groups()
    existing=files(refresh())
    missing=sorted(set.union(*g.values())-set(existing))
    todo=missing if limit==0 else missing[:limit]
    print("UNIQUE",len(set.union(*g.values())),"EXISTING",len(existing),
          "MISSING",len(missing),"THIS_RUN",len(todo))
    start=time.time_ns()//1_000_000
    ok=0
    for i,ticker in enumerate(todo):
        job="research-"+str(start+i)
        print("DOWNLOAD",ticker,job,flush=True)
        r=subprocess.run([str(PY),"-u",str(DOWNLOADER),
                          "--job-id",job,"--ticker",ticker,
                          "--start","2026-11-01","--end","2026-11-25",
                          "--timeframe","15min"],
                         cwd=ROOT,text=True,capture_output=True)
        if r.returncode==0:
            ok+=1;print("PUSH OK",ticker,r.stdout.strip()[-180:],flush=True)
        else:print("FAILED",ticker,(r.stdout+r.stderr)[-400:],flush=True)
        time.sleep(2)
    print("FINISHED",ok,"/",len(todo),"| Re-run to resume missing stocks")

def opening_bars(path,interval):
    raw=git("show","origin/main:"+path,check=False)
    if raw.returncode:return {}
    byday=defaultdict(dict)
    for r in csv.DictReader(io.StringIO(raw.stdout)):
        try:
            t=datetime.fromisoformat(r["Datetime_UTC"]).astimezone(NY)
            day=t.date().isoformat();hour=t.strftime("%H:%M")
            if hour not in ("09:30","09:35","09:40"):continue
            byday[day][hour]=(float(r["Open"]),float(r["Close"]),float(r["Volume"]))
        except (KeyError,ValueError):continue
    result={}
    for day,bars in byday.items():
        if interval=="15min":
            if "09:30" not in bars:continue
            o,c,v=bars["09:30"]
        else:
            if not all(t in bars for t in ("09:30","09:35","09:40")):continue
            o=bars["09:30"][0];c=bars["09:40"][1]
            v=sum(bars[t][2] for t in ("09:30","09:35","09:40"))
        if o>0:result[day]=(o,c,v)
    return result

def rank():
    g=groups();inventory=files(refresh())
    stock_data={}
    needed=sorted(set.union(*g.values()))
    for i,ticker in enumerate(needed,1):
        if ticker in inventory:
            path,tf=inventory[ticker]
            stock_data[ticker]=(opening_bars(path,tf),path)
        if i%25==0:print("LOADED",i,"/",len(needed),flush=True)
    output={}
    summary=["# November 2026 — daily sector stock top 10 at 09:45 ET","",
             "**WARNING:** Universe is a retrospective State Street holdings snapshot, "
             "not verified point-in-time November membership. Incomplete rows are "
             "rankings of observed stocks only, not confirmed sector-wide top 10.","",
             "| Date | Winning ETF | Covered | Top 3 by 15m growth | Volume winner | Data status |",
             "|---|---|---:|---|---|---|"]
    for day,sector in DAYS:
        rows=[]
        for ticker in sorted(g[sector]):
            item=stock_data.get(ticker)
            if not item or day not in item[0]:continue
            (o,c,v),path=item[0][day],item[1]
            rows.append((ticker,100*(c/o-1),int(v),o,c,path))
        rows.sort(key=lambda x:(-x[1],-x[2],x[0]))
        covered=len(rows);total=len(g[sector])
        complete=covered==total
        top3=rows[:3]
        chosen=max(top3,key=lambda x:x[2])[0] if len(top3)==3 else "NONE"
        print("DAY",day,sector,f"{covered}/{total}","TOP3",",".join(x[0] for x in top3),"VOLUME",chosen,flush=True)
        path=f"Rudra-HotSectorHotStock/data/{day}/top10_opening_15m.csv"
        buf=io.StringIO();w=csv.writer(buf)
        w.writerow(["rank","date","sector","ticker","first15m_gain_pct","first15m_shares",
                    "open_0930_ET","close_0945_ET","ibkr_source_csv",
                    "coverage","membership_quality"])
        for i,(ticker,pct,v,o,c,src) in enumerate(rows[:10],1):
            w.writerow([i,day,sector,ticker,round(pct,6),v,o,c,src,
                        "COMPLETE_BARS" if complete else "INCOMPLETE_BARS",
                        "RETROSPECTIVE_PROXY"])
        output[path]=buf.getvalue()
        summary.append(f"| {day} | {sector} | {covered}/{total} | "
                       f"{', '.join(x[0] for x in top3)} | {chosen} | "
                       f"{'COMPLETE_BARS' if complete else 'INCOMPLETE_BARS'} |")
    output["Rudra-HotSectorHotStock/NOVEMBER_2026_TOP10_STOCKS.md"]="\n".join(summary)+"\n"
    output["Rudra-HotSectorHotStock/data/sector_universe_retrospective_snapshot.csv"]=FROZEN.read_text(encoding="utf-8")
    # Publish only these research outputs using a separate temporary git checkout.
    with tempfile.TemporaryDirectory(prefix="asjr_top10_") as directory:
        target=Path(directory)/"repo"
        origin=git("remote","get-url","origin").stdout.strip()
        git("clone","-q","--depth","1","--branch","main",origin,str(target),cwd=Path(directory))
        git("config","user.name","ASJR Sector Research",cwd=target)
        git("config","user.email","asjr-research@localhost",cwd=target)
        for attempt in range(3):
            git("fetch","origin","main",cwd=target)
            git("checkout","-f","-B","research","FETCH_HEAD",cwd=target)
            for path,body in output.items():
                p=target/path;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(body,encoding="utf-8")
            git("add","--",*output,cwd=target)
            r=git("commit","-m","Record November daily opening top10 stock research",
                  check=False,cwd=target)
            if r.returncode:raise RuntimeError("Commit: "+r.stderr[-300:])
            push=git("push","origin","HEAD:refs/heads/main",check=False,cwd=target)
            if push.returncode==0:
                print("REPORTS PUSHED",len(output),"files");return
            time.sleep(attempt+2)
        raise RuntimeError("Could not push ranks after 3 attempts")

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",required=True,choices=("universe","download","rank"))
    parser.add_argument("--limit",type=int,default=15,
                        help="download mode: number of new tickers this run; 0=all")
    args=parser.parse_args()
    WORK.mkdir(parents=True,exist_ok=True)
    if args.mode=="universe":universe()
    elif args.mode=="download":download(args.limit)
    else:rank()
