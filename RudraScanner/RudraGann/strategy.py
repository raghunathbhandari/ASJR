#!/usr/bin/env python3
"""Research-only deterministic Gann 5m signal scanner. No look-ahead or orders."""
from __future__ import annotations
import math
from pathlib import Path
import pandas as pd

SOURCE=Path("RudraScanner/ResearchData/Gann/NQ_2026-10-16_5m.csv")
def levels(lo,hi):
    return [float(n*n+(n%2==0)) for n in range(1,int(math.sqrt(hi))+3)
            if lo-30 <= n*n+(n%2==0) <= hi+30]
def load(path=SOURCE):
    d=pd.read_csv(path)
    d["datetime_ny"]=pd.to_datetime(d["datetime_ny"],utc=True).dt.tz_convert("America/New_York")
    return d.sort_values("datetime_ny").reset_index(drop=True)

def pattern(row,body_ratio=.40,close_zone=.35):
    o,h,l,c=(float(row[k]) for k in ("Open","High","Low","Close"))
    rng=h-l
    return rng>0 and c<o and (o-c)/rng >= body_ratio and (c-l)/rng<=close_zone

def scan(d,zone=15,overshoot=25,lookback=24,confirm_bars=4,
         body_ratio=.40,close_zone=.35,sl_buffer=.25,rr=2,max_risk=150):
    """One trade at a time; 5m patterns are confirmed at candle CLOSE.
    Signal candle cannot be executed at its OPEN using its finished OHLC.
    """
    assert zone>0 and overshoot>=0 and lookback>=1 and confirm_bars>=0 and sl_buffer>=.25 and rr>0
    ls=levels(float(d.Low.min()),float(d.High.max()))
    armed={}
    pending=[]
    candidates=[]
    for i in range(1,len(d)-1):
        b=d.iloc[i];prev=d.iloc[i-1]
        for level in ls:
            if prev.Close>=level and b.Close<level:
                armed[level]={"break_ix":i,"retest_ix":None}
            state=armed.get(level)
            if not state:continue
            if i-state["break_ix"]>lookback or b.Close>level+overshoot:
                armed.pop(level,None);continue
            if i<=state["break_ix"]:continue
            if state["retest_ix"] is None:
                if level-zone <= b.High <= level+overshoot and b.Close<level:
                    state["retest_ix"]=i
                else:continue
            if i-state["retest_ix"]>confirm_bars:
                armed.pop(level,None);continue
            if pattern(b,body_ratio,close_zone) and b.Close<level:
                nxt=d.iloc[i+1]
                entry=float(nxt.Open)
                stop=math.ceil((float(b.High)+sl_buffer)*4)/4
                risk=stop-entry
                if .25<=risk<=max_risk:
                    candidates.append({"level":level,"break_ix":state["break_ix"],
                        "retest_ix":state["retest_ix"],"signal_ix":i,
                        "entry_ix":i+1,"signal_time":str(b.datetime_ny),
                        "entry_time":str(nxt.datetime_ny),"entry":entry,"stop":stop,
                        "target":math.floor((entry-rr*risk)*4)/4})
                armed.pop(level,None)
    accepted=[];busy_until=-1
    for t in sorted(candidates,key=lambda x:(x["entry_ix"],-x["level"])):
        if t["entry_ix"]<=busy_until:continue
        outcome="EOD";exit_ix=len(d)-1;exit_price=float(d.iloc[-1].Close)
        for j in range(t["entry_ix"],len(d)):
            b=d.iloc[j]
            if float(b.High)>=t["stop"]:
                outcome="SL";exit_ix=j;exit_price=t["stop"];break
            if float(b.Low)<=t["target"]:
                outcome="TP";exit_ix=j;exit_price=t["target"];break
        t={**t,"result":outcome,"exit_ix":exit_ix,"exit_price":exit_price,
           "exit_time":str(d.iloc[exit_ix].datetime_ny),
           "R":round((t["entry"]-exit_price)/(t["stop"]-t["entry"]),3)}
        accepted.append(t);busy_until=exit_ix
    return accepted

def main():
    if not SOURCE.exists():
        print("RUDRA GANN | DATA MISSING |",SOURCE);return 2
    d=load()
    trades=scan(d)
    print(f"RUDRA GANN | SELL | 5M candle confirmation | {len(d)} bars | {len(trades)} trades")
    print("GANN |",levels(d.Low.min(),d.High.max()))
    for t in trades:
        print(f"SELL | {t['signal_time']} | G{t['level']:.0f} | entry {t['entry']:.2f} | SL {t['stop']:.2f} | TP {t['target']:.2f} | {t['result']} | {t['R']:+.2f}R")
    print(f"TOTAL | {sum(t['R'] for t in trades):+.2f}R gross | not live or filled orders")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
