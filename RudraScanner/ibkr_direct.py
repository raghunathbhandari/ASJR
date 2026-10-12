#!/usr/bin/env python3
"""On-demand read-only 4-code IBKR scanner. Independent short-lived connection.

SSH or existing Discord allowlisted scan_now.py --ibkr-direct.
NEVER starts a Chakra round, writes DataLake, or places an order.
"""
from __future__ import annotations
import argparse
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

CODES=("TOP_PERC_GAIN","TOP_PERC_LOSE","HOT_BY_VOLUME","MOST_ACTIVE")
UK=ZoneInfo("Europe/London")


def run_direct(host="127.0.0.1",port=4002,client_id=682,limit=10,timeout=12):
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.scanner import ScannerSubscription
    from ibapi.tag_value import TagValue

    class Reader(EWrapper,EClient):
        def __init__(self):
            EClient.__init__(self,self)
            self.ready=threading.Event()
            self.done={code:threading.Event() for code in CODES}
            self.requests={}
            self.rows={code:[] for code in CODES}
            self.failures=[]
        def nextValidId(self,orderId):
            self.ready.set()
        def scannerData(self,reqId,rank,contractDetails,distance,benchmark,projection,legsStr):
            code=self.requests.get(reqId)
            if code:
                name=str(contractDetails.contract.symbol).upper()
                self.rows[code].append((int(rank)+1,name))
        def scannerDataEnd(self,reqId):
            code=self.requests.get(reqId)
            if code:
                self.done[code].set()
        def error(self,reqId,errorCode,errorString,advancedOrderRejectJson=""):
            if errorCode in (2104,2106,2158,2107,2108):
                return
            self.failures.append((reqId,errorCode,str(errorString)[:160]))
            code=self.requests.get(reqId)
            if code and errorCode in (162,200,321,354,10167,10168):
                self.done[code].set()

    app=Reader()
    try:
        app.connect(host,port,client_id)
        worker=threading.Thread(target=app.run,daemon=True)
        worker.start()
        if not app.ready.wait(timeout=min(timeout,8)):
            return "IBKR DIRECT | CONNECTION NOT READY\n" + str(app.failures[:3]) + "\n"
        lines=["IBKR DIRECT | 4 SCANNERS | "+datetime.now(UK).strftime("%H:%M UK")]
        # Request all four scanners together so Discord stays under its 30s limit.
        for i,code in enumerate(CODES):
            req=960000+i
            app.requests[req]=code
            sub=ScannerSubscription()
            sub.instrument="STK"
            sub.locationCode="STK.US.MAJOR"
            sub.scanCode=code
            sub.numberOfRows=50
            sub.stockTypeFilter="CORP"
            filters=[TagValue("marketCapAbove1e6","500"),
                     TagValue("usdPriceAbove","5"),
                     TagValue("avgVolumeAbove","1000000")]
            try:
                app.reqScannerSubscription(req,sub,[],filters)
            except Exception as exc:
                app.failures.append((req,"SEND",type(exc).__name__))
                app.done[code].set()
        deadline=time.monotonic()+timeout
        for code in CODES:
            app.done[code].wait(max(0,deadline-time.monotonic()))
        for i,code in enumerate(CODES):
            req=960000+i
            status="DONE" if app.done[code].is_set() else "TIMEOUT"
            values=sorted(set(app.rows[code]),key=lambda r:r[0])
            lines.append(f"{code} | {status} | {len(values)} returned")
            lines.extend(f" {rank}. {sym}" for rank,sym in values[:limit]
                         if sym not in {"BEAT","ONDS"})
            try: app.cancelScannerSubscription(req)
            except Exception: pass
        if app.failures:
            lines.append("API ERRORS | "+str(app.failures[:5]))
        lines.append("DIRECT IBKR | NO TRADE ORDERS | NO SAVED DATA")
        return "\n".join(lines)+"\n"
    finally:
        try: app.disconnect()
        except Exception: pass


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=4002)
    parser.add_argument("--client-id",type=int,default=682)
    parser.add_argument("--limit",type=int,default=10)
    parser.add_argument("--timeout",type=int,default=12)
    args=parser.parse_args(argv)
    if not 1<=args.limit<=50 or not 2<=args.timeout<=20:
        parser.error("limit 1..50 and timeout 2..20")
    print(run_direct(args.host,args.port,args.client_id,args.limit,args.timeout),end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
