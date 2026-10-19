#!/usr/bin/env python3
"""Rudra-DDB expanded research: two independently retested price boundaries.
Read-only prices, optional public fundamentals. Never contacts trading infrastructure.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

OUT=Path(__file__).resolve().parents[1]/'RudraScanner'/'ResearchData'/'DDB_OPPOSITE_2026-10-16'
PX=pd.read_csv(OUT/'DAILY_CLOSES_3M.csv',index_col=0,parse_dates=True).sort_index()
PX=PX.loc[PX.index<=pd.Timestamp('2026-10-15')].tail(64)
RET=PX.pct_change(fill_method=None)
CORE={'INTC','AKAM','WDC','STX','KLAC','CBOE','ZTS','V','CME','CDW'}
def pivots(v,t=.065):
    direction=0; ext=0; ans=[]
    for i in range(1,len(v)):
        if direction==0:
            if v[i]>=v[ext]*(1+t):ans.append((ext,'L'));ext=i;direction=1
            elif v[i]<=v[ext]*(1-t):ans.append((ext,'H'));ext=i;direction=-1
            elif v[i]>v[ext] and v[ext]>=v[0]:ext=i
            elif v[i]<v[ext] and v[ext]<=v[0]:ext=i
        elif direction==1:
            if v[i]>v[ext]:ext=i
            elif v[i]<=v[ext]*(1-t):ans.append((ext,'H'));ext=i;direction=-1
        else:
            if v[i]<v[ext]:ext=i
            elif v[i]>=v[ext]*(1+t):ans.append((ext,'L'));ext=i;direction=1
    return ans
def distinct(p,spacing=5):
    a=[]
    for i in p:
        if not a or i-a[-1]>=spacing:a.append(i)
    return a
def fit(t):
    c=PX[t].dropna();v=c.to_numpy()
    if len(c)<50 or v[-1]<2 or c.nunique()<20:return None
    pv=pivots(v); lows=[i for i,k in pv if k=='L']; highs=[i for i,k in pv if k=='H']
    # Candidate support and resistance levels arise ONLY from two independently
    # confirmed reversals. Allow 7% price tolerance and >=5-day spacing.
    candidates=[]
    for lowsrc in lows:
        ls=distinct([i for i in lows if abs(v[i]/v[lowsrc]-1)<=.07])
        if len(ls)<2:continue
        for hsrc in highs:
            hs=distinct([i for i in highs if abs(v[i]/v[hsrc]-1)<=.07])
            if len(hs)<2:continue
            bottom=float(np.median(v[ls]));top=float(np.median(v[hs]))
            if bottom<=0 or top<=bottom:continue
            amplitude=100*(top/bottom-1)
            if amplitude<25 or amplitude>50:continue
            # Require ≥ 2 observed complete 25%-50% cross-zone traversals;
            # alternating lows/highs at matching levels (not raw adjacent candles).
            tests=sorted([(i,'L') for i in ls]+[(i,'H') for i in hs])
            clean=[]
            for i,k in tests:
                if not clean or k!=clean[-1][1]:clean.append((i,k))
            transitions=[]
            for (i,k),(j,z) in zip(clean,clean[1:]):
                size=100*(v[j]/v[i]-1)
                if 25<=abs(size)<=50:transitions.append((i,j,size))
            if len(transitions)<2:continue
            candidates.append(dict(ticker=t,support=round(bottom,2),resistance=round(top,2),
              bottom_test_count=len(ls),top_test_count=len(hs),
              swing_cycles=len(transitions),swing_amplitude_pct=round(amplitude,1),
              last_close=round(float(v[-1]),2),range_position_pct=round(100*(v[-1]-bottom)/(top-bottom),1),
              dated_tests='; '.join(str(c.index[i].date())+':'+k+':'+str(round(float(v[i]),2)) for i,k in tests),
              dates_of_major_legs='; '.join(str(c.index[a].date())+'>'+str(c.index[b].date())+':'+str(round(x,1))+'%' for a,b,x in transitions)))
    if not candidates:return None
    candidates.sort(key=lambda x:(x['swing_cycles'],x['bottom_test_count']+x['top_test_count'],-abs(x['range_position_pct']-50)),reverse=True)
    return candidates[0]
rows=[]
for t in PX:
    q=fit(t)
    if q:rows.append(q)
df=pd.DataFrame(rows)
if not df.empty:
    df=df.sort_values(['swing_cycles','swing_amplitude_pct'],ascending=[False,False])
df.to_csv(OUT/'DDB_VALIDATED_RANGES_3M.csv',index=False)
print('TWO-SIDED RETESTED RANGES',len(df),'from',len(PX.columns),'symbols',flush=True)
# Fundamentals are gate: no data means pending, never assume PASS.
fund=[]
for i,t in enumerate(df.ticker if not df.empty else []):
    item={'ticker':t,'fundamental':'PENDING','market_cap':None,'sector':'UNVERIFIED','operating_cashflow':None,'net_income':None}
    try:
        info=yf.Ticker(t).info
        mc=info.get('marketCap'); revenue=info.get('totalRevenue')
        ni=info.get('netIncomeToCommon');oc=info.get('operatingCashflow')
        debt=info.get('totalDebt');cash=info.get('totalCash')
        item.update({'market_cap':mc,'sector':info.get('sector') or 'UNVERIFIED',
                     'operating_cashflow':oc,'net_income':ni,'revenue':revenue})
        if (mc and mc>=2e9 and revenue and revenue>=5e8 and
            ((ni is not None and ni>0) or (oc is not None and oc>0)) and
            (debt is None or cash is None or debt<=4*max(oc or 0,1)+cash)):
            item['fundamental']='PROVISIONAL_PASS'
        elif mc is not None and mc<2e9:item['fundamental']='FAIL_SMALL_CAP'
        elif revenue is not None and revenue<5e8:item['fundamental']='FAIL_REVENUE'
    except Exception as e:
        print('FUNDAMENTAL_FETCH_UNAVAILABLE',t,type(e).__name__,flush=True)
    fund.append(item)
f=pd.DataFrame(fund);f.to_csv(OUT/'DDB_VALIDATED_RANGE_FUNDAMENTALS.csv',index=False)
if not df.empty:
    m=df.merge(f,on='ticker',how='left')
    m['tier']=np.where(m.fundamental=='PROVISIONAL_PASS','PRIMARY_RESEARCH_PENDING_AUDIT','SECONDARY')
    m.to_csv(OUT/'DDB_PRIMARY_SECONDARY_CANDIDATES.csv',index=False)
    # Pair ONLY different reported sectors, and test daily and 10d return correlations.
    pairs=[]
    for _,a in m.iterrows():
        for _,b in m.iterrows():
            if a.ticker>=b.ticker:continue
            if a.sector=='UNVERIFIED' or b.sector=='UNVERIFIED' or a.sector==b.sector:continue
            x=RET[[a.ticker,b.ticker]].dropna()
            if len(x)<40:continue
            corr=x.iloc[:,0].corr(x.iloc[:,1])
            r10=(1+x).rolling(10).apply(np.prod,raw=True)-1
            c10=r10.iloc[:,0].corr(r10.iloc[:,1])
            share=float(((x.iloc[:,0]*x.iloc[:,1])<0).mean())
            if np.isfinite(c10):
                pairs.append(dict(ticker_a=a.ticker,ticker_b=b.ticker,
                    sector_a=a.sector,sector_b=b.sector,
                    daily_corr=round(corr,3),ten_day_corr=round(c10,3),
                    opposite_days_pct=round(share*100,1),
                    bottom_a_pct=a.range_position_pct,bottom_b_pct=b.range_position_pct,
                    tier_a=a.tier,tier_b=b.tier))
    pair=pd.DataFrame(pairs)
    if not pair.empty:pair=pair.sort_values('ten_day_corr')
    pair.to_csv(OUT/'DDB_VALIDATED_RANGES_INVERSE_PAIRS.csv',index=False)
else:
    m=pd.DataFrame()
    pd.DataFrame().to_csv(OUT/'DDB_PRIMARY_SECONDARY_CANDIDATES.csv',index=False)
    pd.DataFrame().to_csv(OUT/'DDB_VALIDATED_RANGES_INVERSE_PAIRS.csv',index=False)
primary=int((m.tier=='PRIMARY_RESEARCH_PENDING_AUDIT').sum()) if not m.empty else 0
lines=['# Rudra-DDB strict repeated range validation across broader US universe','',
       'Prices: 64 completed US daily sessions through 2026-10-15. Full original',
       'broad universe is S&P 500 plus supplemental tickers and sector ETFs.',
       'Both support and resistance must have >=2 independent confirmed turning-point tests (>=5 sessions apart),',
       'within 7% price tolerance. At least TWO 25%-50% completed alternating',
       'support-to-resistance or resistance-to-support price legs are required.',
       'The screener uses daily-close zigzag pivots with 6.5% reversal confirmation.',
       'This is deliberately stricter than counting annual 25%+ swing legs.',
       '',
       f'**Retested ranges passing price gate: {len(df)} / {len(PX.columns)}**',
       f'**Provisional fundamental pass requiring manual audit: {primary}**',
       'PROVISIONAL_PASS is NOT a verified fundamental pass or trading recommendation.',
       'Missing or weak company data remains SECONDARY. Sector classification from company metadata.',
       'If zero pass, do not weaken rules without user permission.',
       '',
       '| Ticker | Sector | Support zone center | Resistance zone center | Bottom tests | Top tests | Completed legs | 25-50% span | Tier |',
       '|---|---|---:|---:|---:|---:|---:|---:|---|']
if not m.empty:
    for _,r in m.iterrows():
        lines.append(f'| {r.ticker} | {r.sector} | ${r.support:.2f} | ${r.resistance:.2f} | {int(r.bottom_test_count)} | {int(r.top_test_count)} | {int(r.swing_cycles)} | {r.swing_amplitude_pct:.1f}% | {r.tier} |')
lines+=['','## Opposite-phase validated-range pairs',
        'Measured negative correlations are exploratory and not assured forward; never assume two sectors consistently alternate.',
        '| A | B | 10d correlation | Opposite days |',
        '|---|---|---:|---:|']
if not m.empty and not pair.empty:
    for _,r in pair.head(25).iterrows():
        lines.append(f'| {r.ticker_a} | {r.ticker_b} | {r.ten_day_corr:.2f} | {r.opposite_days_pct:.0f}% |')
lines+=['','**Caution:** The 64-day sample may be too short to confirm two full 25-50% cycles among durable large caps.',
'Do not replace strict tested levels with single-year extreme or simulated AOIs.',
'Expanded stock universes beyond the original 46 are tracked in DAILY_CLOSES_3M.csv.',
'Independent fundamental audit, earnings and CHOCH remain necessary before trade.']
(OUT/'DDB_STRICT_RETESTED_GROUPS_REPORT.md').write_text('\n'.join(lines)+'\n')
print('FINISHED',len(df),'validated ranges,',primary,'provisional fundamentals',flush=True)
