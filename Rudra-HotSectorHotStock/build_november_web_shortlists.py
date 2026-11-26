#!/usr/bin/env python3
"""Build 3-24 Nov 2026 per-sector historical full-day top-10 stock shortlists.

Source: market-wrap.com/daily-wrap/YYYY-MM-DD/ S&P 500 sector stock tables.
WARNING: HINDSIGHT: full-day close gainers, NOT 09:45 ET opening leaders.
Historical S&P sector coverage can differ from XL* ETF holdings.
Read-only research. No live bot edits or trading orders.
"""
import argparse
import csv
import io
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request,urlopen

try:
    from bs4 import BeautifulSoup
    from bs4.element import NavigableString,Tag
except ImportError as e:
    raise SystemExit("Install into research Python: pip install beautifulsoup4") from e

ROOT=Path("/root/trading/ASJR")
DIR="Rudra-HotSectorHotStock"
INDEX=DIR+"/november_2026_sector_leaders.csv"
MASTER=DIR+"/november_2026_daily_top10_stocks.csv"
SUMMARY=DIR+"/NOVEMBER_2026_WEB_CANDIDATES.md"
SECTORS={"XLK":("Information Technology",75),
         "XLY":("Consumer Discretionary",47),
         "XLV":("Health Care",60),
         "XLE":("Energy",21),
         "XLC":("Communication Services",19),
         "XLP":("Consumer Staples",33),
         "XLB":("Materials",24)}
OTHERS={"Utilities","Financials","Industrials","Real Estate"}
STATUS="WEB_SNP500_SECTOR_CLOSE_GAINERS_HINDSIGHT_NOT_0945"
METHOD="WEB_FULL_DAY_CLOSE_TO_CLOSE_SNP500_SECTOR"
SECTOR_NAME_RE=re.compile(r"^(.+?)\s*\(\s*(\d+)\s*\)$")
SYM=re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
PERCENT=re.compile(r"([-+]?\d+(?:\.\d+)?)\s*%")

def git(cwd,*args,check=True):
    r=subprocess.run(["git",*args],cwd=cwd,capture_output=True,text=True,timeout=120)
    if check and r.returncode:
        raise RuntimeError("Git failure "+str(args[:2])+": "+r.stderr[-300:])
    return r

def csvtext(rows,columns):
    f=io.StringIO(newline="")
    w=csv.DictWriter(f,fieldnames=columns,lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return f.getvalue()

def extract_table(tag):
    head=[x.get_text(" ",strip=True).lower() for x in tag.find_all("th")]
    if head[:2]!=["ticker","name"] or "daily" not in head:
        return []
    idx=head.index("daily")
    items=[]
    for tr in tag.find_all("tr"):
        cells=tr.find_all("td")
        if len(cells)<max(6,idx+1):continue
        sym=cells[0].get_text(" ",strip=True).upper().replace(" ","")
        gain=cells[idx].get_text(" ",strip=True).replace("−","-")
        m=PERCENT.search(gain)
        if not SYM.fullmatch(sym) or not m:continue
        name=cells[1].get_text(" ",strip=True)
        items.append((sym,name,float(m.group(1))))
    return items

def parse_sector(html,etf):
    soup=BeautifulSoup(html,"html.parser")
    target=SECTORS[etf][0]
    allnames={x[0] for x in SECTORS.values()}|OTHERS
    found=[]
    heading_count=0
    # Walk actual text nodes and tables in DOM order: works for div,
    # summary or heading-based sector titles. No sector is inferred from ticker.
    seen_breakdown=False
    current=None
    for node in soup.descendants:
        if isinstance(node,NavigableString):
            s=" ".join(str(node).strip().split())
            if "Full breakdown" in s and "sector" in s.lower():
                seen_breakdown=True
                continue
            if seen_breakdown and "Sector & Industry Wrap" in s:
                break
            if seen_breakdown:
                m=SECTOR_NAME_RE.fullmatch(s)
                if m and m.group(1) in allnames:
                    current=m.group(1)
                    if current==target: heading_count=int(m.group(2))
        elif isinstance(node,Tag) and node.name=="table" and seen_breakdown and current==target:
            found.extend(extract_table(node))

    # Fallback: sector headings might split their text across child spans;
    # read heading/summary text as a whole while visiting tables in document order.
    if not found or not heading_count:
        found=[]
        heading_count=0
        current=None
        seen_breakdown=False
        for node in soup.find_all(["h1","h2","h3","h4","h5","summary","table"]):
            if node.name!="table":
                s=" ".join(node.get_text(" ",strip=True).split())
                if "Full breakdown" in s and "sector" in s.lower():
                    seen_breakdown=True
                    continue
                if seen_breakdown and "Sector & Industry Wrap" in s:break
                if seen_breakdown:
                    m=SECTOR_NAME_RE.fullmatch(s)
                    if m and m.group(1) in allnames:
                        current=m.group(1)
                        if current==target:heading_count=int(m.group(2))
            elif seen_breakdown and current==target:
                found.extend(extract_table(node))

    byticker={}
    for row in found:
        if row[0] in byticker and row[2]!=byticker[row[0]][2]:
            raise ValueError("Conflicting duplicate ticker: "+row[0])
        byticker[row[0]]=row
    ranked=sorted(byticker.values(),key=lambda x:(-x[2],x[0]))
    expected=SECTORS[etf][1]
    if not heading_count:
        raise ValueError("Missing historical S&P sector heading "+target)
    if heading_count<len(ranked)-2 or len(ranked)<max(10,int(expected*.8)):
        raise ValueError("Sector parse coverage suspicious: "+str(len(ranked))+"/"+str(heading_count))
    if len(ranked)<heading_count-2:
        raise ValueError("Missing stock rows: "+str(len(ranked))+"/"+str(heading_count))
    return ranked,heading_count

def get_archive(date):
    url="https://www.market-wrap.com/daily-wrap/"+date+"/"
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; ASJR research)","Accept":"text/html"})
    with urlopen(req,timeout=35) as response:
        html=response.read(3_000_000).decode("utf-8",errors="replace")
    if ("For "+date) not in BeautifulSoup(html,"html.parser").get_text(" ",strip=True):
        raise ValueError("Wrong archive date or redirect: "+date)
    return url,html

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--dry-run",action="store_true",help="Audit web results without GitHub push")
    parser.add_argument("--only-date",help="Process one pending date")
    args=parser.parse_args()

    # Sync refs only: production working tree is not changed.
    git(ROOT,"fetch","-q","origin","main:refs/remotes/origin/main")
    leader_text=git(ROOT,"show","origin/main:"+INDEX).stdout
    leader_rows=list(csv.DictReader(io.StringIO(leader_text)))
    pending=[r for r in leader_rows if r["date_us"] not in ("2026-11-02","2026-11-25")]
    if args.only_date:
        pending=[r for r in pending if r["date_us"]==args.only_date]
        if not pending:parser.error("Date is not one of the 16 pending days.")

    results={}
    errors={}
    for r in pending:
        date,sector=r["date_us"],r["leader_etf"]
        print("SEARCH",date,sector,flush=True)
        try:
            url,html=get_archive(date)
            ranked,n=parse_sector(html,sector)
            results[date]=(sector,url,ranked[:10],len(ranked),n)
            print("VALID",date,"sector coverage",len(ranked),"/",n,
                  "TOP 10",",".join(x[0] for x in ranked[:10]),flush=True)
        except Exception as e:
            errors[date]=str(e)
            print("PENDING",date,str(e),flush=True)
        time.sleep(1)

    if not results:
        print("No verified top-10 lists. CSVs unchanged.")
        return 1
    if args.dry_run:
        print("DRY RUN",len(results),"validated",len(errors),"unresolved")
        return 0 if not errors else 1

    origin=git(ROOT,"remote","get-url","origin").stdout.strip()
    if "github.com" not in origin:raise RuntimeError("Unexpected Git origin")
    with tempfile.TemporaryDirectory(prefix="asjr_web_top10_") as td:
        temp=Path(td); checkout=temp/"checkout"
        git(temp,"clone","-q","--depth","1","--branch","main",origin,str(checkout))
        git(checkout,"config","user.name","ASJR Sector Research")
        git(checkout,"config","user.email","asjr-sector-research@localhost")
        for attempt in range(3):
            git(checkout,"fetch","-q","origin","main")
            git(checkout,"checkout","-f","-B","asjr-web-research","FETCH_HEAD")
            masterfile=checkout/MASTER
            indexfile=checkout/INDEX
            previous=list(csv.DictReader(masterfile.open(encoding="utf-8",newline="")))
            columns=list(csv.DictReader(io.StringIO(masterfile.read_text(encoding="utf-8"))).fieldnames)
            idx=list(csv.DictReader(indexfile.open(encoding="utf-8",newline="")))
            icols=list(idx[0])
            if "top10_candidates_csv" not in icols or "research_status" not in columns:
                raise RuntimeError("Unexpected master or sector index schema")
            combined=[r for r in previous if r["date_us"] not in results]
            written=[]
            for date,(sector,url,stocks,coverage,count) in sorted(results.items()):
                dest=DIR+"/data/"+date+"/"+sector.lower()+"_web_close_gainers_top10.csv"
                daylist=[]
                for rank,(ticker,company,gain) in enumerate(stocks,1):
                    combined.append({
                        "date_us":date,"sector_etf":sector,
                        "sector_first_15min_gain_pct":next(z["leader_first_15m_pct"] for z in leader_rows if z["date_us"]==date),
                        "rank":str(rank),"ticker":ticker,"rank_method":METHOD,
                        "web_full_day_gain_pct":format(gain,".2f"),
                        "ibkr_first_15min_gain_pct":"",
                        "ibkr_first_15min_shares":"",
                        "ibkr_max_upside_after_1445_pct":"",
                        "ibkr_stock_5min_csv":"",
                        "web_source_url":url,"research_status":STATUS,
                    })
                    daylist.append({
                        "rank":rank,"session_date":date,"sector_etf":sector,
                        "ticker":ticker,"company":company,
                        "full_day_gain_pct":format(gain,".2f"),
                        "rank_basis":METHOD,"source_url":url,"status":STATUS,
                    })
                file=checkout/dest
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_text(csvtext(daylist,list(daylist[0])),encoding="utf-8")
                written.append(dest)
                for row in idx:
                    if row["date_us"]==date:
                        row["top10_stock_status"]="WEB_FULL_DAY_TOP10_SHORTLIST_ONLY"
                        row["top10_candidates_csv"]=dest
            combined.sort(key=lambda x:(x["date_us"],int(x["rank"])))
            masterfile.write_text(csvtext(combined,columns),encoding="utf-8")
            indexfile.write_text(csvtext(idx,icols),encoding="utf-8")
            lines=[
                "# November 2026 — Historical web sector-gainer shortlists",
                "",
                "**WARNING:** All rankings on this page use **full-day close-to-close returns**. "
                "These were unknowable at 09:45 ET and must not be used as unbiased "
                "opening-momentum backtest signals. Archive covers S&P 500 sector "
                "companies, not necessarily the exact ETF holdings on every day.",
                "",
                "Source: [Market Wrap daily archives](https://www.market-wrap.com/daily-wrap/). "
                "Our daily winning ETF comes from completed 09:30–09:45 ET IBKR candle data.",
                "",
                "| Date | Sector | Web universe | Top 10 by full-day gain | Source |",
                "|---|---|---:|---|---|",
            ]
            for row in leader_rows:
                date=row["date_us"]
                if date in results:
                    sector,url,stocks,covered,n=results[date]
                    picks=", ".join(t+" "+format(g,"+.2f")+"%" for t,_,g in stocks)
                    lines.append("| "+date+" | "+sector+" | "+str(covered)+"/"+str(n)+
                                 " | "+picks+" | [Daily CSV](data/"+date+"/"+
                                 sector.lower()+"_web_close_gainers_top10.csv) |")
                elif date in errors:
                    lines.append("| "+date+" | "+row["leader_etf"]+
                                 " | Pending | Unverified: "+errors[date].replace("|","/")+" | — |")
                else:
                    lines.append("| "+date+" | "+row["leader_etf"]+
                                 " | Separate/unchanged | See master CSV | — |")
            lines.extend(["","[Master top-10 stock CSV](november_2026_daily_top10_stocks.csv)",
                          "","Next step: download IBKR first 15-minute candles to "
                          "re-rank without end-of-day hindsight."])
            (checkout/SUMMARY).write_text("\n".join(lines)+"\n",encoding="utf-8")
            git(checkout,"add","--",*written,MASTER,INDEX,SUMMARY)
            git(checkout,"commit","-m","Add November sector web full-day gainer shortlists")
            push=git(checkout,"push","origin","HEAD:refs/heads/main",check=False)
            if not push.returncode:
                print("PUBLISHED",len(results),"days",len(results)*10,
                      "candidate rows; unresolved",len(errors),flush=True)
                return 0 if not errors else 1
            time.sleep(attempt+1)
        raise RuntimeError("GitHub push not accepted after 3 retries")

if __name__=="__main__":
    raise SystemExit(main())
