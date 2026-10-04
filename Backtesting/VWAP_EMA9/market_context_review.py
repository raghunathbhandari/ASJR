"""Causal SPY / NVDA context for MU entry research; no future alignment.

Context VWAP is explicitly RTH-only. MU's chart VWAP remains unchanged.
Missing simultaneous context data never passes a required context condition.
"""
import argparse
import itertools
import json
from pathlib import Path
import numpy as np
import pandas as pd
from market_sessions import regular_session_mask
from research_mu import indicators, signal_mask, simulate, stats


def attach_context(mu, spy_bars, nvda_bars):
    d=mu.copy()
    for symbol,bars in [('SPY',spy_bars),('NVDA',nvda_bars)]:
        c=bars.copy();c['Datetime']=pd.to_datetime(c.Datetime,utc=True)
        c=c.sort_values('Datetime').drop_duplicates('Datetime',keep='last')
        c['EMA9']=c.Close.ewm(span=9,adjust=False,min_periods=9).mean()
        c['Return5']=(c.Close/c.Close.shift(5)-1)*100
        c['Rising3']=(c.EMA9>c.EMA9.shift(3))
        c['RTH']=regular_session_mask(c.Datetime)
        c['Session']=c.Datetime.dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d')
        volume=c.Volume.where(c.RTH,0)
        pv=(c.High+c.Low+c.Close)/3*volume
        c['ContextVWAP']=pv.groupby(c.Session).cumsum()/volume.groupby(c.Session).cumsum().replace(0,np.nan)
        c['AboveEMA']=c.Close>c.EMA9;c['AboveVWAP']=c.Close>c.ContextVWAP
        c['EMA9GapPct']=(c.Close/c.EMA9-1)*100
        c['VWAPGapPct']=(c.Close/c.ContextVWAP-1)*100
        cols=['Return5','Rising3','AboveEMA','AboveVWAP','EMA9GapPct','VWAPGapPct']
        c=c[['Datetime']+cols].rename(columns={k:symbol+k for k in cols})
        # Both bars close simultaneously. Never use a later bar or fill stale
        # values through missing periods to manufacture agreement.
        d=d.merge(c,on='Datetime',how='left',validate='one_to_one')
    return d


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv',type=Path,required=True);p.add_argument('--spy-csv',type=Path,required=True);p.add_argument('--nvda-csv',type=Path,required=True)
    p.add_argument('--reference-config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    d=attach_context(indicators(pd.read_csv(a.csv)),pd.read_csv(a.spy_csv),pd.read_csv(a.nvda_csv))
    c=json.loads(a.reference_config.read_text());base=signal_mask(d,c)
    reference=simulate(d,base,c,'2025-10-01','2026-09-30');wins=set(reference.loc[reference.Status=='Good','CandleTimeUK'])
    conditions={
        'SPY above EMA9':d.SPYAboveEMA.eq(True),
        'SPY above RTH VWAP':d.SPYAboveVWAP.eq(True),
        'SPY EMA rising':d.SPYRising3.eq(True),
        'SPY 5-bar return positive':d.SPYReturn5.gt(0),
        'NVDA above EMA9':d.NVDAAboveEMA.eq(True),
        'NVDA above RTH VWAP':d.NVDAAboveVWAP.eq(True),
        'NVDA EMA rising':d.NVDARising3.eq(True),
        'NVDA 5-bar return positive':d.NVDAReturn5.gt(0)}
    rows=[];monthly=[]
    for bits in itertools.product([False,True],repeat=len(conditions)):
        selected=[k for k,b in zip(conditions,bits) if b]
        mask=base.copy()
        for k in selected:mask &= conditions[k].to_numpy()
        trades=simulate(d,mask,c,'2025-10-01','2026-09-30')
        retained=len(wins&set(trades.loc[trades.Status=='Good','CandleTimeUK'])) if not trades.empty else 0
        summaries=[];i=len(rows)
        for period in pd.period_range('2025-10','2026-09',freq='M'):
            t=trades[trades.CandleTimeUK.str.startswith(str(period))] if not trades.empty else trades
            s=stats(t);summaries.append(s);monthly.append(dict(ID=i,Month=str(period),**s))
        rows.append(dict(ID=i,Conditions=json.dumps(selected),RetainedGood=retained,ReferenceGood=len(wins),MonthsAt60=sum(s['Trades']>0 and s['Success']>=60 for s in summaries),WorstFullMonth=min(s['Success'] for s in summaries[1:]),MinFullMonthTrades=min(s['Trades'] for s in summaries[1:]),**stats(trades)))
    table=pd.DataFrame(rows);table.to_csv(a.output/'context_candidates.csv',index=False)
    pd.DataFrame(monthly).to_csv(a.output/'context_monthly.csv',index=False)
    d.loc[d.RTH,['Datetime','CandleTimeUK','SPYReturn5','NVDAReturn5','SPYAboveEMA','NVDAAboveEMA']].to_csv(a.output/'matched_context.csv',index=False)
    print('Preserving every reference winner:')
    print(table[table.RetainedGood==table.ReferenceGood].sort_values(['WorstFullMonth','Net10bpPct'],ascending=False).head(5).to_string(index=False))
    print('Monthly rank, including missed winners explicitly:')
    print(table[table.MinFullMonthTrades>=5].sort_values(['WorstFullMonth','Net10bpPct'],ascending=False).head(10).to_string(index=False))


if __name__=='__main__':main()
