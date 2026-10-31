#!/usr/bin/env python3
"""FROZEN Gold V2 30-Oct-2026 three-reference research result.

This replays the historical BODY-CROSS-ENTRY + C2-WICK-STOP + causal
2-left/2-right 15m swing trailing version (not the later BODY-STOP engine).
The reference C2 timestamps were hand-selected after C3 confirmation.
3/3 reached +0.20% favorable movement (NOT 3/3 winning fills).
Swing-trail aggregate is ~+2.576%, with 2 positive and 1 negative exits.
5m OHLC execution is only approximate; not an unbiased deployable backtest.
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

DEFAULT=Path(__file__).resolve().parent/"data/multi_asset_5m/GOLD_20260901_20261031_5m_UTC.csv"
REFERENCES=[("05:30","SELL"),("07:45","BUY"),("08:45","SELL")]

def run(csv, day="2026-10-30"):
    raw=pd.read_csv(csv)
    raw.index=pd.to_datetime(raw["Datetime_UTC"], utc=True)
    raw=raw[["Open","High","Low","Close","Volume"]].astype(float).sort_index()
    groups=raw.resample("15min")
    b=groups.agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"})
    b=b[groups.size().eq(3)].dropna()
    end=pd.Timestamp(day+"T21:00:00Z")
    output=[]
    for clock,side in REFERENCES:
        t2=pd.Timestamp(day+"T"+clock+":00Z")
        c2=b.loc[t2]
        direction=1 if side=="BUY" else -1
        entry_level=float(max(c2.Open,c2.Close) if direction==1 else min(c2.Open,c2.Close))
        stop=float(c2.Low if direction==1 else c2.High) # original WICK stop version
        after=raw.loc[(raw.index>=t2+pd.Timedelta(minutes=15))&(raw.index<end)]
        crossing=after.High>=entry_level if direction==1 else after.Low<=entry_level
        matches=after.loc[crossing]
        if matches.empty:
            output.append(dict(C2=clock,Side=side,Status="NO_TRIGGER"))
            continue
        entry_time=matches.index[0]
        first=matches.iloc[0]
        entry=float(max(entry_level,first.Open) if direction==1 else min(entry_level,first.Open))
        initial_risk=direction*(entry-stop)/entry*100
        # Swing pivot confirmed ONLY after 2 full candles to the right.
        trailing=stop
        exit_time=None
        exit_price=None
        favorable=0.0
        ambig=bool(first.Low<=stop if direction==1 else first.High>=stop)
        for t,bar in after.loc[after.index>=entry_time].iterrows():
            if t.minute%15==0:
                completed=b.loc[b.index+pd.Timedelta(minutes=15)<=t]
                # For a pivot at index k, two right-hand bars must already be completed.
                for k in range(2,len(completed)-2):
                    p=completed.iloc[k]
                    if completed.index[k]<entry_time:continue
                    neighbor=completed.iloc[k-2:k+3]
                    is_pivot=(p.Low<min(neighbor.iloc[0].Low,neighbor.iloc[1].Low,neighbor.iloc[3].Low,neighbor.iloc[4].Low)
                              if direction==1 else
                              p.High>max(neighbor.iloc[0].High,neighbor.iloc[1].High,neighbor.iloc[3].High,neighbor.iloc[4].High))
                    if is_pivot:
                        candidate=float(p.Low-0.2 if direction==1 else p.High+0.2)
                        if direction*(candidate-trailing)>0 and direction*(float(bar.Open)-candidate)>0:
                            trailing=candidate
            gap=direction*(float(bar.Open)-trailing)<=0
            touched=bar.Low<=trailing if direction==1 else bar.High>=trailing
            if gap or touched:
                exit_price=float(bar.Open) if gap else trailing
                exit_time=t
                break
            favorable=max(favorable,float(bar.High-entry if direction==1 else entry-bar.Low))
        if exit_price is None:
            exit_price=float(after.iloc[-1].Close)
            exit_time=after.index[-1]+pd.Timedelta(minutes=5)
        gain=100*direction*(exit_price-entry)/entry
        # Historical favorable excursion (even if execution is unresolved).
        future=after.loc[after.index>=entry_time]
        max_excursion=(float(future.High.max())-entry if direction==1 else entry-float(future.Low.min()))/entry*100
        output.append(dict(C2=clock,Side=side,EntryTime=entry_time.strftime("%H:%M"),
                           Entry=round(entry,2),WickSL=round(stop,2),InitialRiskPct=round(initial_risk,3),
                           EntryStopAmbiguous=ambig,MaxFavorablePct=round(max_excursion,3),
                           ReachedFixed0p20=bool(max_excursion>=.20),
                           ExitTime=exit_time.strftime("%H:%M"),Exit=round(exit_price,2),
                           SwingGainPct=round(gain,4),Status="RETROSPECTIVE_ONLY"))
    df=pd.DataFrame(output)
    return df

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--csv",type=Path,default=DEFAULT)
    p.add_argument("--date",default="2026-10-30")
    args=p.parse_args()
    result=run(args.csv,args.date)
    print("GOLD V2 FROZEN 3-REFERENCE SWING REPLAY |",args.date)
    print(result.to_string(index=False))
    print("Historical +0.20% favorable-movement rate:",int(result.ReachedFixed0p20.sum()),"/",len(result))
    print("Swing-trail outcomes:",int((result.SwingGainPct>0).sum()),"wins /",int((result.SwingGainPct<0).sum()),"losses")
    print("Sum gross swing gain:",round(result.SwingGainPct.sum(),4),"%")
    print("NOT a 100% executed-trade win rate. Body-stop model is a separate version.")
