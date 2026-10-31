#!/usr/bin/env python3
"""Gold V2 turning-area C2 detector. Detect first; evaluate entry separately.

No future bar can contribute to identifying C2 sweep depth/ATR; C3 confirms
only after the 15-minute C3 candle has closed. Reference day: 2026-10-30.
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

DEFAULT=Path(__file__).parent/"data/multi_asset_5m/GOLD_20260901_20261031_5m_UTC.csv"

def load(path):
    d=pd.read_csv(path)
    d.index=pd.to_datetime(d["Datetime_UTC"],utc=True)
    d=d[["Open","High","Low","Close","Volume"]].astype(float).sort_index()
    g=d.resample("15min")
    o=g.agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"})
    o=o[g.size().eq(3)].dropna()
    return o

def detect(b, day, lookback=8, min_range_atr=1.0, min_depth_atr=.5,
           min_c1_body=.4, min_c3_body=.6):
    prev=b.Close.shift(1)
    tr=pd.concat([b.High-b.Low,(b.High-prev).abs(),(b.Low-prev).abs()],axis=1).max(axis=1)
    # ATR before C2: no information from C2 or later used for volatility baseline
    atr=tr.rolling(14,min_periods=14).mean().shift(1)
    out=[]
    for i in range(max(lookback,16),len(b)-1):
        c1,c2,c3=b.iloc[i-1],b.iloc[i],b.iloc[i+1]
        t1,t2,t3=b.index[i-1],b.index[i],b.index[i+1]
        if t2.strftime("%Y-%m-%d")!=day or t2-t1!=pd.Timedelta(minutes=15) or t3-t2!=pd.Timedelta(minutes=15):
            continue
        pre=b.iloc[i-lookback:i]  # prior bars only
        av=atr.iloc[i]
        if pd.isna(av) or av<=0:continue
        r1=c1.High-c1.Low; r2=c2.High-c2.Low; r3=c3.High-c3.Low
        if min(r1,r2,r3)<=0:continue
        body1=abs(c1.Close-c1.Open)/r1; body3=abs(c3.Close-c3.Open)/r3
        hi=pre.High.max();lo=pre.Low.min()
        for side,depth,confirm in (
            ("BUY",lo-c2.Low,c3.Close>c3.Open and c3.Low>c2.Low),
            ("SELL",c2.High-hi,c3.Close<c3.Open and c3.High<c2.High),
        ):
            if depth<min_depth_atr*av or r2<min_range_atr*av or body1<min_c1_body or body3<min_c3_body or not confirm:
                continue
            # Next candle open is informational only; risk is NOT a detection filter.
            next_open=float(b.iloc[i+2].Open) if i+2<len(b) and b.index[i+2]-t3==pd.Timedelta(minutes=15) else np.nan
            stop=float(c2.Low if side=="BUY" else c2.High)
            risk=100*abs(next_open-stop)/next_open if not np.isnan(next_open) else np.nan
            out.append(dict(side=side,c1=t1,c2=t2,c3=t3,confirmed_at=t3+pd.Timedelta(minutes=15),
                            c2_range=float(r2),atr14_pre=float(av),range_atr=float(r2/av),
                            swing_depth=float(depth),sweep_atr=float(depth/av),
                            c1_body_ratio=float(body1),c3_body_ratio=float(body3),
                            c2_volume=float(c2.Volume),next_open=next_open,
                            structural_stop=stop,structural_risk_pct=risk,
                            risk_eligible=bool(not np.isnan(risk) and
                                               (next_open>stop if side=="BUY" else next_open<stop)
                                               and risk<=.2)))
    return pd.DataFrame(out)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",type=Path,default=DEFAULT)
    p.add_argument("--date",default="2026-10-30")
    p.add_argument("--lookback",type=int,default=8)
    p.add_argument("--range-atr",type=float,default=1.)
    p.add_argument("--depth-atr",type=float,default=.5)
    p.add_argument("--c1-body",type=float,default=.4)
    p.add_argument("--c3-body",type=float,default=.6)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    d=detect(load(a.csv),a.date,a.lookback,a.range_atr,a.depth_atr,a.c1_body,a.c3_body)
    print("Gold V2 C2 swing-turn detector |",a.date,"| detected",len(d))
    if not d.empty:
        print(d[["side","c2","range_atr","sweep_atr","c1_body_ratio","c3_body_ratio",
                 "structural_risk_pct","risk_eligible"]].to_string(index=False))
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        d.to_csv(a.out,index=False)
        print("Saved",a.out)
if __name__=="__main__":main()
