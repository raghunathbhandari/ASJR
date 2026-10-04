"""Audit candle filters against existing winning entries, without hiding misses.

Retention is a retrospective research constraint, not a guarantee of keeping
future winning trades. No candle dates or outcome labels enter signal logic.
"""
import argparse
import itertools
import json
from pathlib import Path
import pandas as pd
from research_mu import indicators, signal_mask, simulate, stats


def retention_audit(baseline, candidate):
    rows=[]
    for good in baseline[baseline.Status=='Good'].itertuples():
        exact=candidate[(candidate.CandleTimeUK==good.CandleTimeUK)&(candidate.Status=='Good')]
        overlapping=candidate[
            (pd.to_datetime(candidate.CandleTimeUK,utc=True)<=pd.Timestamp(good.ExitCandleUK)) &
            (pd.to_datetime(candidate.ExitCandleUK,utc=True)>=pd.Timestamp(good.CandleTimeUK)) &
            (candidate.Status=='Good')]
        rows.append(dict(BaselineGoodCandleUK=good.CandleTimeUK,SameEntryGood=bool(len(exact)),OverlappingGoodTrade=bool(len(overlapping)),CandidateCandles='; '.join(overlapping.CandleTimeUK.astype(str))))
    return pd.DataFrame(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--start-date',default='2026-09-01');p.add_argument('--end-date',default='2026-09-30')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    d=indicators(pd.read_csv(a.csv))
    base=dict(mode='break10',stop='signal',filters=[],slope=0)
    baseline=simulate(d,signal_mask(d,base),base,a.start_date,a.end_date)
    choices=[['bull',True],['body',.3],['upperwick',.5],['eff',.6],['rvol',1],['rsi',[60,90]],['slope',.4]]
    rows=[]
    for bits in itertools.product([False,True],repeat=len(choices)):
        for stop in ['signal','swing5']:
            c=dict(mode='break10',stop=stop,filters=[f for f,b in zip(choices,bits) if b],slope=0)
            trades=simulate(d,signal_mask(d,c),c,a.start_date,a.end_date)
            audit=retention_audit(baseline,trades)
            rows.append(dict(Config=json.dumps(c),RetainedExact=int(audit.SameEntryGood.sum()),RetainedGoodMoves=int(audit.OverlappingGoodTrade.sum()),**stats(trades)))
    trials=pd.DataFrame(rows);trials.to_csv(a.output/'candle_retention_candidates.csv',index=False)
    eligible=trials[trials.RetainedExact==int((baseline.Status=='Good').sum())].copy()
    # Prefer fewer conditions when multiple configurations produce equal results.
    eligible['FilterCount']=eligible.Config.map(lambda s:len(json.loads(s)['filters']))
    eligible=eligible.sort_values(['Success','CompoundPct','FilterCount'],ascending=[False,False,True])
    selected=json.loads(eligible.iloc[0].Config)
    (a.output/'retention_config.json').write_text(json.dumps(selected,indent=2))
    trades=simulate(d,signal_mask(d,selected),selected,a.start_date,a.end_date)
    trades.to_csv(a.output/'retention_trades.csv',index=False)
    retention_audit(baseline,trades).to_csv(a.output/'retention_audit.csv',index=False)
    print(eligible.head(5).to_string(index=False));print(trades.to_string(index=False))


if __name__=='__main__': main()
