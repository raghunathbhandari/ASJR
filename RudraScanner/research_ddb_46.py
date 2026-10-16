#!/usr/bin/env python3
"""Rudra-DDB three-month multi-swing screen of fixed Oct 15 IBKR 46 list.
Research-only: no IBKR, orders, live Chakra, new network access, or git.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from RudraScanner.research_ema50_46 import NAMES, OUT, _load

def pivots(close, pct=0.065):
    """Percentage reversal zigzag; switches direction only after >=6.5% reversal.
    Daily closes only. Avoid multiple tiny pivots in volatile stocks.
    """
    v=np.asarray(close,dtype=float)
    if len(v)<3: return []
    ans=[]
    extreme=0; direction=0
    for i in range(1,len(v)):
        if direction==0:
            if v[i]>=v[extreme]*(1+pct):
                ans.append((extreme,'LOW')); extreme=i; direction=1
            elif v[i]<=v[extreme]*(1-pct):
                ans.append((extreme,'HIGH')); extreme=i; direction=-1
            elif v[i]>v[extreme] and (v[extreme]>=v[0]):
                extreme=i
            elif v[i]<v[extreme] and (v[extreme]<=v[0]):
                extreme=i
        elif direction==1:
            if v[i]>v[extreme]: extreme=i
            elif v[i]<=v[extreme]*(1-pct):
                ans.append((extreme,'HIGH')); extreme=i; direction=-1
        else:
            if v[i]<v[extreme]: extreme=i
            elif v[i]>=v[extreme]*(1+pct):
                ans.append((extreme,'LOW')); extreme=i; direction=1
    return ans

def run():
    out=[]
    for t in NAMES:
        df=_load('daily',t)
        if len(df)<45:
            out.append({'ticker':t,'status':'INSUFFICIENT','daily_bars':len(df)})
            continue
        d=df.tail(64).copy()
        c=pd.to_numeric(d['Close'],errors='coerce').ffill()
        vol=pd.to_numeric(d['Volume'],errors='coerce').fillna(0)
        if (c<=0).any() or c.nunique()<15 or vol.tail(20).mean()<200000:
            out.append({'ticker':t,'status':'ILLQUID_OR_FROZEN','daily_bars':len(df)})
            continue
        values=c.to_numpy(); last=float(values[-1]); lo=float(c.min());hi=float(c.max())
        p=pivots(values)
        confirmed_highs=[(i,float(values[i])) for i,k in p if k=='HIGH']
        confirmed_lows=[(i,float(values[i])) for i,k in p if k=='LOW']
        # Most recent peak must occur within the same rolling ~3m window.
        hiidx=int(np.argmax(values))
        peak_to_current=round((last/hi-1)*100,2)
        loc=round(100*(last-lo)/(hi-lo),1) if hi>lo else None
        e9=c.ewm(span=9,adjust=False).mean()
        e20=c.ewm(span=20,adjust=False).mean()
        recent_5_return=round((last/float(c.iloc[-6])-1)*100,2)
        r={'ticker':t,'status':'OK','daily_bars':len(df),
           'last_date':str(d.index[-1].date()),'close':round(last,3),
           'high_3m':round(hi,3),'high_date':str(d.index[hiidx].date()),
           'low_3m':round(lo,3),'low_date':str(d.index[int(np.argmin(values))].date()),
           'drawdown_from_high_pct':peak_to_current,
           'range_position_pct':loc,
           'swing_reversals_6p5pct':len(p),
           'confirmed_highs':len(confirmed_highs),
           'confirmed_lows':len(confirmed_lows),
           'last5_return_pct':recent_5_return,
           'ema9_up_5d':bool(e9.iloc[-1]>e9.iloc[-6]),
           'ema20_up_5d':bool(e20.iloc[-1]>e20.iloc[-6]),
           'above_ema9':bool(c.iloc[-1]>e9.iloc[-1]),
           'above_ema20':bool(c.iloc[-1]>e20.iloc[-1]),
           'swing_trace':'; '.join(f"{str(d.index[i].date())}:{k}:{values[i]:.2f}" for i,k in p[-8:])}
        r['ddb_price_candidate']=bool(len(p)>=3 and peak_to_current<=-15 and loc<=30)
        r['bottom_confirming']=bool(r['ddb_price_candidate'] and recent_5_return>0 and
                         r['ema9_up_5d'] and r['above_ema9'])
        out.append(r)
    frame=pd.DataFrame(out)
    path=OUT/'DDB_3MONTH_MULTI_SWING_46.csv'
    frame.to_csv(path,index=False)
    cands=frame.loc[frame.get('ddb_price_candidate',pd.Series(dtype=bool)).eq(True)].copy()
    cands=cands.sort_values(['bottom_confirming','range_position_pct','swing_reversals_6p5pct'],
                             ascending=[False,True,False])
    lines=['# Rudra-DDB: 3-month multiple-swing / near-bottom screen',
           '',
           'Data: stored daily Yahoo history ending 2026-10-15; **not** an October 16 live quote.',
           'A material reversal is a >=6.5% daily-close change from a running swing extreme.',
           'Candidate requires >=3 confirmed pivots, >=15% off 3-month high and',
           'price in the bottom 30% of its 3-month closing range.',
           'Confirmation proxy: last 5 sessions positive, EMA9 5-day slope positive, close above EMA9.',
           '**Proxy is not a confirmed CHOCH, liquidity sweep or safe bottom.**',
           'This is a PRICE screen only; fundamental durability, $2B+ cap,',
           'sector relative strength, earnings and dated catalysts need separate verification.',
           '',
           f'Valid daily datasets: {(frame.status=="OK").sum()}/46',
           f'Price candidates: {len(cands)}',
           f'Positive momentum proxy: {int(cands.bottom_confirming.sum()) if len(cands) else 0}',
           '',
           '| Ticker | 3m high | Current | Drawdown | Range position | Confirmed swings | Recovery proxy |',
           '|---|---:|---:|---:|---:|---:|---|']
    for _,r in cands.iterrows():
        lines.append(f"| {r.ticker} | {r.high_3m:.2f} | {r.close:.2f} | "
                     f"{r.drawdown_from_high_pct:.1f}% | {r.range_position_pct:.1f}% | "
                     f"{int(r.swing_reversals_6p5pct)} | {'YES' if r.bottom_confirming else 'NO'} |")
    lines+=['','See CSV for full 46 names, dates, indicator flags and dated swing trace.',
            'Zigzag is descriptive and threshold-sensitive; validate candle structure.',
            'Do not classify missing/illiquid names as qualifying.']
    (OUT/'DDB_3MONTH_MULTI_SWING_46.md').write_text('\n'.join(lines)+'\n')
    print(f"DDB 3M | {len(frame)} stocks | price candidates {len(cands)} "
          f"| recovery proxies {int(cands.bottom_confirming.sum()) if len(cands) else 0}",flush=True)
    return 0

if __name__=='__main__':
    raise SystemExit(run())
