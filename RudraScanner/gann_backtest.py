#!/usr/bin/env python3
"""Rudra-Gann V1 research-only NQ 15m breakdown/retest backtest.
Reads CSV locally; no broker connection, orders, Chakra modifications or downloads.
All timestamps are America/New_York. 15m candle labels are bar OPEN.
"""
from __future__ import annotations
import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

DEFAULT = Path("RudraScanner/ResearchData/Gann/NQ_2026-10-16_5m.csv")
TICK = 0.25

@dataclass(frozen=True)
class Params:
    zone: float = 15.0
    retest_bars: int = 4
    stop_buffer: float = 0.25
    rr: float = 2.0
    max_break_depth: float = 250.0
    max_risk: float = 150.0
    min_risk: float = 1.0

def gann_levels(lo, hi):
    """Linear Gann odd n -> n², even n -> n²+1. Fixed 1x scale."""
    levels=[]
    for n in range(1, int(math.sqrt(max(hi,0)))+3):
        value=n*n+(1 if n%2==0 else 0)
        if lo <= value <= hi:
            levels.append((n,float(value)))
    return levels

def read_15m(path):
    df=pd.read_csv(path)
    required={"datetime_ny","Open","High","Low","Close","Volume"}
    if not required.issubset(df.columns):
        raise ValueError("missing columns: "+str(sorted(required-set(df.columns))))
    df["datetime_ny"]=pd.to_datetime(df["datetime_ny"],utc=True).dt.tz_convert("America/New_York")
    df=df.sort_values("datetime_ny").set_index("datetime_ny")
    if df.index.has_duplicates:
        raise ValueError("duplicate 5m timestamps")
    # Require real, adjacent 5m bars; do not silently interpolate missing data.
    bars=[]
    for t,g in df.groupby(df.index.floor("15min")):
        expected=pd.date_range(t,periods=3,freq="5min",tz="America/New_York")
        if len(g)!=3 or list(g.index)!=list(expected):
            continue
        bars.append({"time":t,"Open":float(g.Open.iloc[0]),
                     "High":float(g.High.max()),"Low":float(g.Low.min()),
                     "Close":float(g.Close.iloc[-1]),"Volume":float(g.Volume.sum())})
    if not bars: raise ValueError("no complete 15m bars")
    return bars

def backtest(bars,params=Params(),levels=None):
    """Short only, line crossed downward then retested from below.
    Signal generated at confirmed retest CLOSE; enter NEXT bar OPEN.
    One open position at a time. Stop-first if both exit levels touched.
    """
    if levels is None:
        low=min(b["Low"] for b in bars)-500
        high=max(b["High"] for b in bars)+500
        levels=[v for _,v in gann_levels(low,high)]
    trades=[]
    open_until=-1
    for level in sorted(levels,reverse=True):
        for i in range(1,len(bars)-2):
            before,b=bars[i-1],bars[i]
            # First breakdown through line: preceding CLOSE above or at line,
            # current CLOSE under line; no future candle information.
            if not (before["Close"]>=level and b["Close"]<level
                    and b["Close"]<b["Open"]
                    and level-b["Close"]<=params.max_break_depth):
                continue
            # First qualifying bearish retest in next 1..N bars.
            for j in range(i+1,min(i+params.retest_bars+1,len(bars)-1)):
                q=bars[j]
                if q["Close"]>=level+params.zone:
                    break   # level reclaimed decisively
                if not (abs(q["High"]-level)<=params.zone
                        and q["Close"]<level and q["Close"]<q["Open"]):
                    continue
                k=j+1
                entry=bars[k]["Open"]
                stop=math.ceil((q["High"]+params.stop_buffer)/TICK)*TICK
                risk=stop-entry
                if not params.min_risk<=risk<=params.max_risk:
                    break
                target=math.floor((entry-params.rr*risk)/TICK)*TICK
                # calculate potential exit without intra-bar assumptions
                outcome="OPEN";exit_price=bars[-1]["Close"];exit_ix=len(bars)-1
                for x in range(k,len(bars)):
                    candle=bars[x]
                    if candle["High"]>=stop:
                        outcome="SL";exit_price=stop;exit_ix=x;break
                    if candle["Low"]<=target:
                        outcome="TP";exit_price=target;exit_ix=x;break
                trades.append({"level":level,"break_time":b["time"],
                               "retest_time":q["time"],"entry_time":bars[k]["time"],
                               "entry":entry,"stop":stop,"target":target,
                               "exit_time":bars[exit_ix]["time"],"exit":exit_price,
                               "result":outcome,"R":round((entry-exit_price)/risk,3),
                               "entry_ix":k,"exit_ix":exit_ix})
                break
    # Sort chronological and disallow overlapping positions; the first event wins.
    trades.sort(key=lambda t:(t["entry_ix"],-t["level"]))
    accepted=[]
    for t in trades:
        if t["entry_ix"]<=open_until: continue
        accepted.append(t)
        open_until=t["exit_ix"]
    return accepted

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--csv",default=str(DEFAULT))
    p.add_argument("--zone",type=float,default=15)
    p.add_argument("--retest-bars",type=int,default=4)
    p.add_argument("--stop-buffer",type=float,default=.25)
    p.add_argument("--rr",type=float,default=2)
    args=p.parse_args(argv)
    params=Params(zone=args.zone,retest_bars=args.retest_bars,
                  stop_buffer=args.stop_buffer,rr=args.rr)
    if args.zone<=0 or not 1<=args.retest_bars<=12 or args.stop_buffer<TICK or args.rr<=0:
        p.error("invalid thresholds")
    bars=read_15m(args.csv)
    trades=backtest(bars,params)
    print(f"RUDRA GANN V1 | NQ | 15M | {len(bars)} complete bars | NY time")
    print(f"SETTINGS | zone ±{params.zone} | retest <= {params.retest_bars} bars | SL buffer {params.stop_buffer} | TP {params.rr}R")
    print("METHOD | Downward close cross; bearish retest near Gann; NEXT candle open entry; stop-first on ambiguous candles")
    print("LEVELS |",", ".join(str(int(x)) for _,x in gann_levels(min(b['Low'] for b in bars)-500,max(b['High'] for b in bars)+500)))
    for t in trades:
        print(f"SELL | GANN {int(t['level'])} | BREAK {t['break_time']:%H:%M} | RETEST {t['retest_time']:%H:%M} | ENTRY {t['entry_time']:%H:%M} {t['entry']:.2f} | SL {t['stop']:.2f} | TP {t['target']:.2f} | {t['result']} {t['R']:+.2f}R")
    print(f"TOTAL | {len(trades)} trades | sum {sum(t['R'] for t in trades):+.2f}R (gross, no fees/slippage)")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
