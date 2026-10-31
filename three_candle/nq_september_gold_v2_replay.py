#!/usr/bin/env python3
"""NQ September cross-asset research using Gold V2 monthly replay: same execution rules as frozen_three_reference.py.

RESEARCH, NOT LIVE-VALIDATED: C3-confirmed signals are selected retrospectively,
but C2-body crossing may execute DURING C3. This creates selection lookahead.
Gross summed trade percentages are not compounded account returns; simultaneous
positions, costs, slips, session gaps and tick sequencing not fully modelled.
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from detect_gold_v2_swings import load, detect

DEFAULT=Path(__file__).resolve().parent/"data/multi_asset_5m/NQ_20260901_20261031_5m_UTC.csv"

def monthly(csv,month):
    raw=pd.read_csv(csv)
    raw.index=pd.to_datetime(raw["Datetime_UTC"],utc=True)
    raw=raw[["Open","High","Low","Close","Volume"]].astype(float).sort_index()
    b=load(csv)
    start=pd.Timestamp(month+"-01T00:00:00Z")
    stop_month=start+pd.offsets.MonthBegin(1)
    days=sorted(set(t.strftime("%Y-%m-%d") for t in b.index if start<=t<stop_month))
    signals=pd.concat([detect(b,day) for day in days],ignore_index=True)
    results=[]
    for signal in signals.itertuples(index=False):
        c2=b.loc[signal.c2]
        side=signal.side
        d=1 if side=="BUY" else -1
        level=float(max(c2.Open,c2.Close) if d==1 else min(c2.Open,c2.Close))
        initial_stop=float(c2.Low if d==1 else c2.High)  # frozen version uses WICK stop
        start_at=signal.c2+pd.Timedelta(minutes=15)
        cutoff=pd.Timestamp(signal.c2.strftime("%Y-%m-%d")+"T21:00:00Z")
        after=raw.loc[(raw.index>=start_at)&(raw.index<cutoff)]
        hits=after.loc[after.High>=level if d==1 else after.Low<=level]
        record=dict(C2=signal.c2,Side=side,EntryTime=pd.NaT,Entry=np.nan,
                    WickSL=initial_stop,InitialRiskPct=np.nan,
                    EntryStopAmbiguous=False,ExitTime=pd.NaT,Exit=np.nan,
                    SwingGainPct=np.nan,Status="NO_TRIGGER")
        if hits.empty:
            results.append(record);continue
        entry_time=hits.index[0]
        first=hits.iloc[0]
        entry=float(max(level,first.Open) if d==1 else min(level,first.Open))
        record.update(EntryTime=entry_time,Entry=entry,
                      InitialRiskPct=100*d*(entry-initial_stop)/entry,
                      EntryStopAmbiguous=bool(first.Low<=initial_stop if d==1 else first.High>=initial_stop))
        trail=initial_stop
        exit_t=None;exit_p=None
        for t,bar in after.loc[after.index>=entry_time].iterrows():
            if t.minute%15==0:
                done=b.loc[b.index+pd.Timedelta(minutes=15)<=t]
                for k in range(2,len(done)-2):
                    p=done.iloc[k]
                    if done.index[k]<entry_time:continue
                    neighbors=done.iloc[k-2:k+3]
                    pivot=(p.Low<min(neighbors.iloc[0].Low,neighbors.iloc[1].Low,neighbors.iloc[3].Low,neighbors.iloc[4].Low)
                           if d==1 else p.High>max(neighbors.iloc[0].High,neighbors.iloc[1].High,neighbors.iloc[3].High,neighbors.iloc[4].High))
                    if pivot:
                        next_stop=float(p.Low-.2 if d==1 else p.High+.2)
                        if d*(next_stop-trail)>0 and d*(float(bar.Open)-next_stop)>0:
                            trail=next_stop
            gap=d*(float(bar.Open)-trail)<=0
            touched=bool(bar.Low<=trail if d==1 else bar.High>=trail)
            if gap or touched:
                exit_t=t;exit_p=float(bar.Open) if gap else trail
                break
        if exit_p is None:
            exit_t=after.index[-1]+pd.Timedelta(minutes=5)
            exit_p=float(after.iloc[-1].Close)
        record.update(ExitTime=exit_t,Exit=exit_p,
                      SwingGainPct=100*d*(exit_p-entry)/entry,Status="SIMULATED")
        results.append(record)
    return pd.DataFrame(results)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",type=Path,default=DEFAULT)
    p.add_argument("--month",default="2026-09")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    df=monthly(a.csv,a.month)
    if df.empty:
        print("No C3-confirmed candidates");return
    fmt=df.copy()
    for name in ["C2","EntryTime","ExitTime"]:
        fmt[name]=fmt[name].dt.strftime("%Y-%m-%d %H:%M").fillna("-")
    for name in ["Entry","WickSL","Exit","InitialRiskPct","SwingGainPct"]:
        fmt[name]=fmt[name].round(4)
    print(fmt.to_string(index=False))
    trades=df.loc[df.Status=="SIMULATED"]
    wins=int((trades.SwingGainPct>0).sum())
    compliant=trades.loc[(trades.InitialRiskPct>0)&(trades.InitialRiskPct<=.2)&(~trades.EntryStopAmbiguous)]
    print("\nNQ TEST (GOLD V2 RULES) EARLY BODY ENTRY + WICK SL + SWING TRAIL",a.month)
    print(f"Signals={len(df)} | Filled={len(trades)} | Wins={wins} | Losses={int((trades.SwingGainPct<0).sum())}")
    print(f"Gross summed gain={trades.SwingGainPct.sum():+.4f}% | Win rate={100*wins/len(trades):.2f}%")
    print(f"Risk-compliant simulated trades={len(compliant)} | Gross sum={compliant.SwingGainPct.sum():+.4f}%")
    key=trades.loc[trades.C2.dt.strftime("%Y-%m-%d")=="2026-10-30"]
    if False: # Gold-only 30-Oct consistency check not applicable to NQ
        print("30 October consistency check:")
        for z in key.itertuples(index=False):
            print(z.C2.strftime("%H:%M"),z.Side,f"{z.SwingGainPct:+.4f}%")
        if len(key)==3:
            total=key.SwingGainPct.sum()
            print("30 October total:",f"{total:+.4f}%")
            assert abs(total-2.5764)<.002,"Monthly output does not reproduce frozen reference"
    print("CAUTION: historical C3 selection leaks into earlier C2-body entries. Not a causal tradable win rate.")
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        df.to_csv(a.out,index=False)
        print("Saved",a.out)
if __name__=="__main__":
    main()
