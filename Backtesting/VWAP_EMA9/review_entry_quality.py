"""Source-informed entry filters, with explicit winning-entry retention.

Freeze a candidate before separate-month checks. September is in-sample:
the previous winners and failures informed these hypotheses. The audit uses
outcomes only to evaluate retention; signal_mask never sees future outcomes.
"""
import argparse
import itertools
import json
from pathlib import Path
import pandas as pd
from research_mu import indicators, signal_mask, simulate, stats
from review_candle_patterns import retention_audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv',type=Path,required=True)
    p.add_argument('--reference-config',type=Path,required=True)
    p.add_argument('--reference-trades',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    d=indicators(pd.read_csv(a.csv))
    reference=json.loads(a.reference_config.read_text())
    previous=pd.read_csv(a.reference_trades)
    replay=simulate(d,signal_mask(d,reference),reference,'2026-09-01','2026-09-30')
    pd.testing.assert_frame_equal(previous,replay,check_dtype=False)
    seed=dict(reference)
    seed['filters']=reference['filters']+[['macdhist',0],['rvolmean',1],['higherlows',3],['bbexpand',.8],['rsislope',0]]
    (a.output/'initial_quality_config.json').write_text(json.dumps(seed,indent=2))
    # First full candidate is frozen before any separate-date checks.
    initial=simulate(d,signal_mask(d,seed),seed,'2026-09-01','2026-09-30')
    initial.to_csv(a.output/'initial_quality_trades.csv',index=False)
    n_good=int((previous.Status=='Good').sum())
    rows=[]
    # Ablation of this fixed list: no new parameter tuning to holdout outcomes.
    for bits in itertools.product([False,True],repeat=len(seed['filters'])):
        c=dict(seed,filters=[f for f,b in zip(seed['filters'],bits) if b])
        mask=signal_mask(d,c)
        t=simulate(d,mask,c,'2026-09-01','2026-09-30')
        audit=retention_audit(previous,t)
        october=simulate(d,mask,c,'2026-10-01','2026-10-02')
        preserves_oct=not october.empty and bool(((october.CandleTimeUK=='2026-10-01 17:40:00+01:00')&(october.Status=='Good')).any())
        rows.append(dict(Config=json.dumps(c),Filters=len(c['filters']),RetainedGood=int(audit.SameEntryGood.sum()),Oct1Reference=preserves_oct,**stats(t)))
    trials=pd.DataFrame(rows)
    trials.to_csv(a.output/'ablation_trials.csv',index=False)
    eligible=trials[(trials.RetainedGood==n_good)&trials.Oct1Reference&(trials.Success>=60)&(trials.Net10bpPct>0)]
    if eligible.empty: raise RuntimeError('No candidate meets retention, 60% and positive cost-stressed return; do not report success.')
    # Prefer fewer conditions rather than the best in-sample win rate.
    eligible=eligible.sort_values(['Filters','Net10bpPct','Success'],ascending=[True,False,False])
    selected=json.loads(eligible.iloc[0].Config)
    (a.output/'quality_config.json').write_text(json.dumps(selected,indent=2))
    mask=signal_mask(d,selected)
    trades=simulate(d,mask,selected,'2026-09-01','2026-09-30')
    trades.to_csv(a.output/'quality_trades.csv',index=False)
    audit=retention_audit(previous,trades)
    audit.to_csv(a.output/'quality_retention.csv',index=False)
    # Preserve complete execution details, not merely the Good label.
    old_good=previous[previous.Status=='Good']
    new_good=trades.set_index('CandleTimeUK').loc[old_good.CandleTimeUK].reset_index()
    pd.testing.assert_frame_equal(old_good.reset_index(drop=True),new_good[old_good.columns],check_dtype=False)
    removed=previous[~previous.CandleTimeUK.isin(trades.CandleTimeUK)]
    assert removed.Status.eq('Bad').all()
    removed.to_csv(a.output/'removed_bad_entries.csv',index=False)
    checks=[]
    for name,start,end in [('April','2026-04-01','2026-04-30'),('May','2026-05-01','2026-05-31'),('June','2026-06-01','2026-06-30'),('July','2026-07-01','2026-07-31'),('August','2026-08-01','2026-08-31'),('September','2026-09-01','2026-09-30'),('October','2026-10-01','2026-10-02')]:
        t=simulate(d,mask,selected,start,end)
        checks.append(dict(Period=name,**stats(t)))
        if name=='October':t.to_csv(a.output/'october_trades.csv',index=False)
    pd.DataFrame(checks).to_csv(a.output/'separate_date_checks.csv',index=False)
    print(eligible.head(10).to_string(index=False))
    print(pd.DataFrame(checks).to_string(index=False))
    print('Every previous Good entry and execution detail retained; removed entries are all Bad.')


if __name__=='__main__': main()
