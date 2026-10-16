#!/usr/bin/env python3
"""Independent DDB out-of-phase research; never touches Chakra or IBKR.
Universe: S&P 500 + Nasdaq 100 + fixed 46 + DDB user stocks; no arbitrary top-N discovery cutoff.
Uses Yahoo historical close daily 3 months, index constituent endpoints, saves audit files.
"""
from __future__ import annotations
import re, time
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'RudraScanner'/'ResearchData'/'DDB_OPPOSITE_2026-10-16'
OUT.mkdir(parents=True,exist_ok=True)
CORE="INTC WDC AKAM ORCL KLAC LRCX AMAT ASML TSM MU QCOM AVGO SNDK ACN SHOP VEEV CDNA NTSK PMI SVRN DNA AEHL VNCE".split()
try:
    from RudraScanner.research_ema50_46 import NAMES
except Exception:
    NAMES=[]
ETFS="SPY QQQ XLK XLE XLV XLF XLI XLY XLP XLU XLB SOXX SMH IGV XBI IWM".split()

def universe():
    names=set(CORE+NAMES+ETFS)
    sources=[]
    for url,kind in [('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies','sp500'),
                     ('https://en.wikipedia.org/wiki/Nasdaq-100','nasdaq100')]:
        try:
            tabs=pd.read_html(url)
            for tab in tabs:
                cols={str(c).strip().lower():c for c in tab.columns}
                key=next((cols[s] for s in ['symbol','ticker'] if s in cols),None)
                if key is None or len(tab)<70:continue
                new=set()
                for v in tab[key].astype(str):
                    t=v.replace('.','-').strip().upper()
                    if re.fullmatch(r'[A-Z]{1,6}(?:-[A-Z])?',t):new.add(t)
                if len(new)>=70:
                    names|=new
                    sources.append(f'{kind}={len(new)}')
                    break
        except Exception as exc:print(f'UNIVERSE ERROR {kind} {type(exc).__name__}: {str(exc)[:70]}',flush=True)
    if not sources:
        raise RuntimeError('Both broad universe sources inaccessible; refuse to claim broad-market coverage')
    (OUT/'UNIVERSE_SOURCE.txt').write_text('Sources: '+', '.join(sources)+'\nSymbols: '+str(len(names))+'\n')
    return sorted(names), sources

def price_history(names):
    result={}
    for k in range(0,len(names),20):
        group=names[k:k+20]
        try:
            x=yf.download(' '.join(group),period='120d',interval='1d',auto_adjust=True,progress=False,threads=False,group_by='ticker')
            for s in group:
                try:
                    f=x[s] if isinstance(x.columns,pd.MultiIndex) else x
                    c=pd.to_numeric(f['Close'],errors='coerce').dropna()
                    c.index=pd.to_datetime(c.index).tz_localize(None).normalize()
                    c=c.loc[c.index<=pd.Timestamp('2026-10-15')].tail(64)
                    if len(c)>=45 and c.iloc[-1]>2 and (c>0).all():result[s]=c
                except Exception:pass
        except Exception as exc: print(f'PRICE ERROR {group[0]} {type(exc).__name__}',flush=True)
        print(f'BATCH {min(k+20,len(names))}/{len(names)} usable={len(result)}',flush=True)
        time.sleep(0.8)
    for s in NAMES:
        if s not in result:
            try:
                from RudraScanner.research_ema50_46 import _load
                f=_load('daily',s)
                c=f['Close'].copy();c.index=pd.to_datetime(c.index).tz_localize(None).normalize()
                c=c.loc[c.index<=pd.Timestamp('2026-10-15')].tail(64)
                if len(c)>=45 and c.nunique()>15:result[s]=c
            except Exception:pass
    return pd.DataFrame(result).sort_index()

def go():
    names,sources=universe()
    px=price_history(names)
    px.to_csv(OUT/'DAILY_CLOSES_3M.csv',float_format='%.5f')
    returns=px.pct_change(fill_method=None)
    rows=[]
    for s in px.columns:
        c=px[s].dropna()
        if len(c)<45:continue
        high=c.max(); low=c.min()
        rows.append({'ticker':s,'last':round(c.iloc[-1],3),'range_position_pct':round(100*(c.iloc[-1]-low)/(high-low),1) if high>low else np.nan,
                     'drawdown_pct':round(100*(c.iloc[-1]/high-1),1),
                     'return_10d_pct':round(100*(c.iloc[-1]/c.iloc[-11]-1),1) if len(c)>=11 else np.nan,
                     'high_date':str(c.idxmax().date()),'low_date':str(c.idxmin().date()),
                     'sessions':len(c)})
    phase=pd.DataFrame(rows).sort_values('range_position_pct')
    phase.to_csv(OUT/'ALL_STOCK_PHASES.csv',index=False)
    # Mechanistic non-overlapping groups A bottom, B top. They are candidates,
    # not necessarily negatively correlated! Require measured evidence below.
    bottom=phase[(phase.range_position_pct<=30)&(phase.drawdown_pct<=-15)&(~phase.ticker.isin(ETFS))]
    top=phase[(phase.range_position_pct>=70)&(~phase.ticker.isin(ETFS))]
    pairs=[]
    for a in bottom.ticker:
        for b in top.ticker:
            x=returns[[a,b]].dropna()
            if len(x)<40:continue
            corr=x[a].corr(x[b])
            active=(x[a]!=0)&(x[b]!=0)
            opp=((x.loc[active,a]*x.loc[active,b])<0).mean() if active.any() else np.nan
            # A moving 10-session lead/lag score, not a prediction.
            ca=(1+x[a]).rolling(10).apply(np.prod,raw=True)-1
            cb=(1+x[b]).rolling(10).apply(np.prod,raw=True)-1
            corr10=ca.corr(cb)
            pairs.append({'bottom_ticker':a,'top_ticker':b,'sessions':len(x),
                          'daily_return_corr':round(float(corr),3),'ten_day_return_corr':round(float(corr10),3),
                          'opposite_day_share':round(float(opp),3),
                          'bottom_range_pct':float(phase.set_index('ticker').loc[a,'range_position_pct']),
                          'top_range_pct':float(phase.set_index('ticker').loc[b,'range_position_pct'])})
    frame=pd.DataFrame(pairs)
    if len(frame):
        frame=frame.sort_values(['ten_day_return_corr','daily_return_corr'])
    frame.to_csv(OUT/'BOTTOM_TOP_OPPOSITE_PAIRS.csv',index=False)
    strong=frame[(frame.ten_day_return_corr<-.25)&(frame.opposite_day_share>.52)] if len(frame) else frame
    # Avoid forming "groups" from one lucky pair, test sector groups on same data.
    sector={}
    for s in ETFS:
        if s in returns:sector[s]=returns[s]
    sectorcorr=pd.DataFrame(sector).corr(min_periods=40)
    sectorcorr.to_csv(OUT/'SECTOR_ETF_CORRELATIONS.csv')
    lines=['# Rudra DDB — Two Opposite-Phase Stock Groups', '',
       '**Exploratory historical scan, NOT a proven reliable trading rotation.**',
       'All percentages use completed daily closes through 2026-10-15.',
       'No current day quote, fundamentals, market cap, or CHOCH confirmation is implied.',
       f'Universe source: {", ".join(sources)} + 46 IBKR + user DDB symbols',
       f'Unique universe: {len(names)}; adequate prices: {len(phase)};',
       f'Bottom side: {len(bottom)}; top side: {len(top)};',
       f'Comparative pairs: {len(frame)}; stronger opposite candidates: {len(strong)}.',
       '',
       '## Bottom group: lower 30% of three-month range AND >=15% below 3m high',
       '| Ticker | Range percentile | 3m drawdown | 10d return |',
       '|---|---:|---:|---:|']
    for _,r in bottom.head(40).iterrows():
        lines.append(f'| {r.ticker} | {r.range_position_pct:.0f}% | {r.drawdown_pct:.1f}% | {r.return_10d_pct:+.1f}% |')
    lines+=['','## Top group: upper 30% of three-month range',
       '| Ticker | Range percentile | 10d return |','|---|---:|---:|']
    for _,r in top.sort_values('range_position_pct',ascending=False).head(40).iterrows():
        lines.append(f'| {r.ticker} | {r.range_position_pct:.0f}% | {r.return_10d_pct:+.1f}% |')
    lines+=['','## Out-of-phase shortlist (negative 10-day correlation and opposite daily returns)',
            '| Bottom | Top | Daily corr | 10d corr | Opposite days |',
            '|---|---|---:|---:|---:|']
    for _,r in strong.head(40).iterrows():
        lines.append(f'| {r.bottom_ticker} | {r.top_ticker} | {r.daily_return_corr:.2f} | {r.ten_day_return_corr:.2f} | {r.opposite_day_share:.0%} |')
    lines+=['', 'Pairs may both decline in market stress; anti-correlation can disappear.',
       'Before any trade verify both businesses and market caps, compare drawdown and rally histories,',
       'sector context and pending earnings, plus liquidity sweep and bullish CHOCH at attractive price.',
       'Avoid implying that selling one group is required to buy the other.',
       'Full all-stock outputs and sector ETF return correlations are saved alongside this report.']
    (OUT/'DDB_TWO_GROUPS_REPORT.md').write_text('\n'.join(lines)+'\n')
    print(f'DDB PHASE FINISHED universe={len(names)} usable={len(phase)} bottom={len(bottom)} top={len(top)} opposite={len(strong)}',flush=True)

if __name__=='__main__':go()
