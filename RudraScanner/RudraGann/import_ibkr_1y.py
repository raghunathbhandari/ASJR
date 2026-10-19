#!/usr/bin/env python3
"""Historical NQ futures 5m archive via IBKR, research-only.

Does not transmit orders. Downloads BACKWARDS in small chunks, writes checkpoint
locally after each chunk, and conservatively refuses silent coverage claims.
CME NQ continuous future historical contract may require permissions / exchange
subscriptions; older bars/roll adjustments depend on IBKR availability.
"""
from __future__ import annotations
import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

DEFAULT_OUT=Path("/root/trading/ASJR-Gann/RudraScanner/ResearchData/Gann/IBKR_NQ_5m_1y.csv")
def append_checkpoint(path, rows):
    if not rows:return
    path.parent.mkdir(parents=True,exist_ok=True)
    newer=pd.DataFrame(rows)
    newer["Datetime"]=pd.to_datetime(newer["Datetime"],utc=True)
    if path.exists():
        old=pd.read_csv(path)
        if not old.empty:
            old["Datetime"]=pd.to_datetime(old["Datetime"],utc=True)
            newer=pd.concat([old,newer],ignore_index=True)
    newer=newer.drop_duplicates("Datetime").sort_values("Datetime")
    tmp=path.with_suffix(".tmp")
    newer.to_csv(tmp,index=False)
    tmp.replace(path)
    print(f"CHECKPOINT | bars={len(newer)} | {newer.Datetime.min()} -> {newer.Datetime.max()}",flush=True)

async def run(args):
    try:
        from ib_async import IB, Future
    except ImportError:
        print("ERROR | ib_async is not installed in selected Python environment");return 2
    start=pd.Timestamp(args.start,tz="UTC")
    end=pd.Timestamp(args.end,tz="UTC")+pd.Timedelta(days=1)-pd.Timedelta(seconds=1)
    if not start<end:raise ValueError("start must be before end")
    output=Path(args.out)
    ib=IB()
    try:
        await ib.connectAsync(args.host,args.port,clientId=args.client_id,timeout=18,readonly=True)
        from datetime import date
        import calendar
        contracts={}
        async def contract_for(ts):
            stamp=ts.tz_convert("America/New_York")
            for year in (stamp.year,stamp.year+1):
                for month in (3,6,9,12):
                    fridays=[d for d in range(1,calendar.monthrange(year,month)[1]+1)
                             if date(year,month,d).weekday()==4]
                    cutoff=pd.Timestamp(date(year,month,fridays[2]),tz="America/New_York")-pd.Timedelta(days=8)
                    if stamp < cutoff:
                        code=f"{year}{month:02d}"
                        if code not in contracts:
                            contract=Future("NQ",code,"CME",currency="USD",includeExpired=True)
                            q=await ib.qualifyContractsAsync(contract)
                            if len(q)!=1:raise RuntimeError("Cannot qualify NQ "+code)
                            contracts[code]=q[0]
                            print("IBKR | qualified NQ "+code,flush=True)
                        return code,contracts[code]
            raise RuntimeError("No quarterly contract for "+str(stamp))
        print("IBKR | dated NQ futures | approximate 8-day-prior rollover | NOT back-adjusted",flush=True)
        if output.exists():
            saved=pd.read_csv(output,usecols=["Datetime"])
            saved["Datetime"]=pd.to_datetime(saved.Datetime,utc=True)
            cursor=saved.Datetime.min()-pd.Timedelta(seconds=1) if not saved.empty else end
            cursor=min(cursor,end)
        else:cursor=end
        count=0
        while cursor>=start and count<args.max_chunks:
            try:
                contract_code,qualified=await contract_for(cursor)
                bars=await ib.reqHistoricalDataAsync(qualified,
                      endDateTime=cursor.to_pydatetime(),durationStr="2 D",
                      barSizeSetting="5 mins",whatToShow="TRADES",
                      useRTH=False,formatDate=2,keepUpToDate=False,timeout=90)
            except Exception as exc:
                print(f"ERROR | historical request | {type(exc).__name__}: {exc}");return 2
            if not bars:
                print(f"STOP | IBKR returned 0 candles near {cursor}; history/permission/pacing may be unavailable");return 3
            rows=[]
            for b in bars:
                dt=pd.Timestamp(b.date)
                dt=dt.tz_localize("UTC") if dt.tzinfo is None else dt.tz_convert("UTC")
                if start<=dt<=end:
                    rows.append({"Datetime":dt.isoformat(),"Open":float(b.open),
                     "High":float(b.high),"Low":float(b.low),"Close":float(b.close),
                     "Volume":float(b.volume),"Contract":contract_code})
            earliest=min(pd.Timestamp(b.date).tz_convert("UTC") if pd.Timestamp(b.date).tzinfo else pd.Timestamp(b.date).tz_localize("UTC") for b in bars)
            if earliest>=cursor:
                print("ERROR | history cursor did not move backward");return 4
            append_checkpoint(output,rows)
            cursor=earliest-pd.Timedelta(seconds=1)
            count+=1
            print(f"IBKR | chunk {count}/{args.max_chunks} | contract={contract_code} | next-before={cursor}",flush=True)
            await asyncio.sleep(args.sleep)
        if cursor>=start:
            print("PARTIAL | max chunks reached; rerun same command to resume safely");return 5
        print(f"COMPLETE REQUESTED RANGE | {args.start} through {args.end} | verify gaps/rolls before strategy testing")
        return 0
    except Exception as exc:
        print(f"ERROR | {type(exc).__name__}: {exc}")
        return 2
    finally:
        if ib.isConnected():ib.disconnect()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--start",default="2025-10-17")
    ap.add_argument("--end",default="2026-10-16")
    ap.add_argument("--host",default="127.0.0.1")
    ap.add_argument("--port",type=int,default=4002,help="IB Gateway paper 4002; live 4001, TWS paper 7497, TWS live 7496, user-configurable")
    ap.add_argument("--client-id",type=int,default=87)
    ap.add_argument("--out",default=str(DEFAULT_OUT))
    ap.add_argument("--max-chunks",type=int,default=240)
    ap.add_argument("--sleep",type=float,default=1.1)
    args=ap.parse_args()
    return asyncio.run(run(args))
if __name__=="__main__":
    raise SystemExit(main())
