#!/usr/bin/env python3
"""Gold V2 experimental EARLY C2 body-cross entry (does NOT wait for C3).

Research only. Uses completed C2 at t+15m and first subsequent 5m break of
C2 body OPEN (BUY above / SELL below). Never treat a C3-close result as
available for the earlier entry. Enforces 0.20% structural C2-extreme risk.
"""
import argparse
from pathlib import Path
import pandas as pd
from detect_gold_v2_swings import DEFAULT, load, detect

def early_entries(path, day):
    raw=pd.read_csv(path)
    raw.index=pd.to_datetime(raw["Datetime_UTC"],utc=True)
    raw=raw[["Open","High","Low","Close","Volume"]].astype(float).sort_index()
    b15=load(path)
    # Detector currently includes C3 confirmation, therefore this list is
    # retrospective setup identification; NOT a causal entry signal.
    sig=detect(b15,day)
    rows=[]
    for z in sig.itertuples(index=False):
        c2=b15.loc[z.c2]
        boundary=float(c2.Open)
        # Historical body-cross: earliest crossing after C2 closes, search in C3.
        start=z.c2+pd.Timedelta(minutes=15)
        window=raw.loc[(raw.index>=start)&(raw.index<start+pd.Timedelta(minutes=15))]
        chosen=None
        for t,v in window.iterrows():
            crossed=v.High>=boundary if z.side=="BUY" else v.Low<=boundary
            if crossed:
                price=(float(v.Open) if (v.Open>=boundary if z.side=="BUY" else v.Open<=boundary) else boundary)
                chosen=(t,price,float(v.Low),float(v.High))
                break
        if chosen is None:
            rows.append(dict(c2=z.c2,side=z.side,trigger=boundary,early_time=pd.NaT,
                             early_entry=float("nan"),risk_pct=float("nan"),
                             risk_eligible=False,remarks="C3 did not cross body open"))
            continue
        t,price,bar_low,bar_high=chosen
        stop=float(c2.Low if z.side=="BUY" else c2.High)
        risk_pct=100*((price-stop) if z.side=="BUY" else (stop-price))/price
        # Intrabar OHLC ambiguity: if crossing 5m candle also touches original SL,
        # sequencing cannot be established; reject pending lower timeframe data.
        ambiguous=(bar_low<=stop if z.side=="BUY" else bar_high>=stop)
        rows.append(dict(c2=z.c2,side=z.side,trigger=boundary,early_time=t,
                         early_entry=price,structural_stop=stop,risk_pct=risk_pct,
                         risk_eligible=bool(0<risk_pct<=0.2 and not ambiguous),
                         ambiguous_bar=ambiguous,
                         remarks=("AMBIGUOUS_WITHIN_5M" if ambiguous else
                                  "OVER_0.20%_RISK" if risk_pct>.2 else "ELIGIBLE")))
    return pd.DataFrame(rows)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--csv",type=Path,default=DEFAULT)
    p.add_argument("--date",default="2026-10-30")
    a=p.parse_args()
    d=early_entries(a.csv,a.date)
    print(d.to_string(index=False) if not d.empty else "No turning-area candidates")
    print("WARNING: detected candidates use future C3 confirmation. Early-entry results are")
    print("RETROSPECTIVE. Build C2-only causal screening before live alerts/backtest P&L.")
