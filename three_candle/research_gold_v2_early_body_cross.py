#!/usr/bin/env python3
"""Gold V2 C2 body-edge crossing research, 5m execution from completed 15m C2.

A C2-only detector enumerates potential signals at C2 close. C3 success is
recorded separately and NEVER used to authorize a body-cross entry.
Stop = OPPOSITE C2 BODY EDGE, not C2 wick extreme.
Ambiguous entry/stop within the same 5m candle is UNRESOLVED, never a win.
Research only: OHLC is not tick data; costs, contract rolls excluded.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from detect_gold_v2_swings import DEFAULT, load

def c2_candidates(b, day, lookback=8, range_atr=1.0, depth_atr=0.5, c1_body=0.4):
    close=b.Close.shift(1)
    tr=pd.concat([b.High-b.Low,(b.High-close).abs(),(b.Low-close).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14,min_periods=14).mean().shift(1)
    rows=[]
    for i in range(max(16,lookback),len(b)-1):
        c1,c2,c3=b.iloc[i-1],b.iloc[i],b.iloc[i+1]
        t1,t2,t3=b.index[i-1:i+2]
        if str(t2.date())!=day or t2-t1!=pd.Timedelta(minutes=15) or t3-t2!=pd.Timedelta(minutes=15):
            continue
        prev=b.iloc[i-lookback:i]
        vol=float(atr.iloc[i])
        if not np.isfinite(vol) or vol<=0 or c1.High<=c1.Low:
            continue
        if abs(c1.Close-c1.Open)/(c1.High-c1.Low)<c1_body:
            continue
        if (c2.High-c2.Low)/vol<range_atr:
            continue
        for side,depth in (("BUY",prev.Low.min()-c2.Low),("SELL",c2.High-prev.High.max())):
            if depth/vol<depth_atr:
                continue
            trigger=float(max(c2.Open,c2.Close) if side=="BUY" else min(c2.Open,c2.Close))
            stop=float(min(c2.Open,c2.Close) if side=="BUY" else max(c2.Open,c2.Close))
            r=100*abs(trigger-stop)/trigger
            body3=abs(c3.Close-c3.Open)/(c3.High-c3.Low) if c3.High>c3.Low else 0
            confirmed=(c3.Close>c3.Open and c3.Low>c2.Low if side=="BUY"
                       else c3.Close<c3.Open and c3.High<c2.High)
            rows.append(dict(day=day,c2=t2,side=side,c2_color="GREEN" if c2.Close>=c2.Open else "RED",
                             trigger=trigger,body_stop=stop,body_risk_pct=r,
                             swing_depth_atr=float(depth/vol),c2_range_atr=float((c2.High-c2.Low)/vol),
                             c3_confirmed=bool(confirmed and body3>=0.6),
                             c3_body_ratio=float(body3)))
    return pd.DataFrame(rows)

def backtest_one(row, raw, end="21:00", risk_max=0.20):
    d=1 if row.side=="BUY" else -1
    start=row.c2+pd.Timedelta(minutes=15)
    cutoff=pd.Timestamp(str(row.day)+"T"+end+":00Z")
    future=raw.loc[(raw.index>=start)&(raw.index<cutoff)]
    trigger,stop=float(row.trigger),float(row.body_stop)
    crossing=lambda b: b.High>=trigger if d==1 else b.Low<=trigger
    hits=future.loc[future.apply(crossing,axis=1)]
    rec=dict(trigger_time=pd.NaT,entry=np.nan,entry_risk_pct=np.nan,
             risk_eligible=False,entry_stop_ambiguous=False,
             reached_fixed_0p20=False,hit_0p20_after_entry=False,
             execution_status="NO_TRIGGER",step_gain_pct=np.nan,
             step_exit_time=pd.NaT)
    if hits.empty:return rec
    t=hits.index[0]
    bar=hits.iloc[0]
    entry=max(trigger,float(bar.Open)) if d==1 else min(trigger,float(bar.Open))
    risk=100*d*(entry-stop)/entry
    ambiguous=(bar.Low<=stop if d==1 else bar.High>=stop)
    rec.update(trigger_time=t,entry=entry,entry_risk_pct=risk,
               risk_eligible=bool(0<risk<=risk_max),
               entry_stop_ambiguous=bool(ambiguous))
    # Peak favorable movement is useful for research but not sufficient
    # to establish execution ordering on the trigger bar.
    subsequent=future.loc[future.index>=t]
    favorable=(subsequent.High.max()-entry if d==1 else entry-subsequent.Low.min())/entry*100
    rec["max_favorable_pct_unordered"]=float(favorable)
    rec["reached_fixed_0p20"]=bool(favorable>=0.20)  # descriptive excursion, NOT an executable target hit
    if ambiguous:
        rec["execution_status"]="UNRESOLVED_ENTRY_STOP_5M"
        return rec
    rec["execution_status"]="SIMULATABLE_RISK_OVER_CAP" if risk>risk_max else "SIMULATABLE_WITHIN_CAP"
    # Conservative stop-first OHLC: stop check before favorable price and
    # before adjusting trailing stop; next bar receives newly trailed stop.
    trail=stop
    step=0
    for t2,x in subsequent.iterrows():
        gap=d*(x.Open-trail)<=0
        touched=x.Low<=trail if d==1 else x.High>=trail
        if gap or touched:
            px=float(x.Open) if gap else trail
            rec["step_gain_pct"]=100*d*(px-entry)/entry
            rec["step_exit_time"]=t2
            rec["hit_0p20_after_entry"]=step>=1
            return rec
        favorable_bar=float(x.High-entry if d==1 else entry-x.Low)
        k=max(0,int(np.floor(favorable_bar/(entry*0.002)+1e-9)))
        step=max(step,k)
        if step:
            target=entry+d*step*entry*.002
            trail=max(trail,target) if d==1 else min(trail,target)
    if len(subsequent):
        rec["step_gain_pct"]=100*d*(float(subsequent.iloc[-1].Close)-entry)/entry
        rec["step_exit_time"]=subsequent.index[-1]+pd.Timedelta(minutes=5)
        rec["hit_0p20_after_entry"]=step>=1
    return rec

def run(path, day, reference_only=False, risk_max=.2):
    raw=pd.read_csv(path)
    raw.index=pd.to_datetime(raw["Datetime_UTC"],utc=True)
    raw=raw[["Open","High","Low","Close","Volume"]].astype(float).sort_index()
    patterns=c2_candidates(load(path),day)
    if reference_only and day=="2026-10-30":
        targets={("05:30","SELL"),("07:45","BUY"),("08:45","SELL")}
        patterns=patterns.loc[patterns.apply(
            lambda x:(x.c2.strftime("%H:%M"),x.side) in targets,axis=1)]
    if patterns.empty:
        return patterns
    return pd.concat([patterns.reset_index(drop=True),
                      pd.DataFrame([backtest_one(x,raw,risk_max=risk_max)
                                    for x in patterns.itertuples(index=False)])],axis=1)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv",type=Path,default=DEFAULT)
    p.add_argument("--date",default="2026-10-30")
    p.add_argument("--risk-max",type=float,default=.2)
    p.add_argument("--reference-only",action="store_true",
                   help="Show user-selected three 30-Oct references only; DO NOT use to claim unbiased win rate")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    d=run(a.csv,a.date,a.reference_only,a.risk_max)
    print("Gold V2 C2-only candidates:",len(d))
    if d.empty:return
    print(d[["c2","side","trigger_time","entry","body_stop","entry_risk_pct",
             "c3_confirmed","reached_fixed_0p20","execution_status",
             "step_gain_pct"]].to_string(index=False))
    print("Movement success (ALL C2 candidates):",int(d.reached_fixed_0p20.sum()),"/",len(d),
          "(unsequenced price excursion; NOT executed win rate)")
    confirmed=d.loc[d.c3_confirmed]
    print("C3-confirmed historical references:",len(confirmed),
          "| reached +0.20%:",int(confirmed.reached_fixed_0p20.sum()),
          "| execution unresolved:",int(confirmed.entry_stop_ambiguous.sum()))
    print("NOTE: C3 confirmation is retrospective for body entries occurring during C3.")
    evaluable=d.loc[d.execution_status.str.startswith("SIMULATABLE_")]
    print("Simulatable fills:",len(evaluable),
          "| winners:",int((evaluable.step_gain_pct>0).sum()),
          "| losses:",int((evaluable.step_gain_pct<0).sum()),
          "| unresolved:",int(d.entry_stop_ambiguous.sum()))
    valid=evaluable.loc[evaluable.risk_eligible]
    print("Within risk cap:",len(valid),"| gross step return:",round(valid.step_gain_pct.sum(),4),"%")
    print("Verified executable 3/3 win rate: NOT ESTABLISHED (5m entry/stop ordering).")
    print("WARNING: 5m OHLC cannot sequence crossing and stop inside same bar;")
    print("C2 screening at close is causal; reference-only selection is not an unbiased backtest.")
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        d.to_csv(a.out,index=False)
        print("Saved",a.out)
if __name__=="__main__":
    main()
