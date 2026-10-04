"""Evaluate a fixed candidate pool against EVERY observed calendar month.

Never promotes September-only success as annual success. Tables separately
audit reviewed September winners and all winners of the reference rule.
This is retrospective rule research, not an untouched validation dataset.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from research_mu import indicators, signal_mask, simulate, stats


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv',type=Path,required=True);p.add_argument('--candidate-table',type=Path,required=True)
    p.add_argument('--ablation-table',type=Path,required=True);p.add_argument('--reference-config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    d=indicators(pd.read_csv(a.csv))
    months=pd.period_range('2025-10','2026-09',freq='M')
    reference=json.loads(a.reference_config.read_text())
    ref=simulate(d,signal_mask(d,reference),reference,'2025-10-01','2026-09-30')
    ref.to_csv(a.output/'reference_annual_trades.csv',index=False)
    good_times=set(ref.loc[ref.Status=='Good','CandleTimeUK'])
    sep_good={t for t in good_times if t.startswith('2026-09')}
    # Fixed pools from prior research, deduplicated exactly. No calendar date
    # is a signal condition, and no outcome flag enters signal_mask.
    configs=[reference]
    for table in [a.candidate_table,a.ablation_table]:
        configs += [json.loads(s) for s in pd.read_csv(table).Config]
    additions=[['chop',61.8],['chop',50],['chop',38.2],['cmf',0],['cmf',.05],['cmf5',0],['di',1.5],['di',2],['dirange',[1,5]],['rvolmean',1],['cumvol',1],['atrpct',[.2,.6]],['rangeatr',[.5,2.5]],['atrexpand',1],['bbexpand',1],['emacrosses',3],['higherlows',3],['rsislope',0],['macdhist',0]]
    for mode in ['break10','break3','trend','pullback','early','reclaim']:
        for stop in ['signal','swing5','swingATR']:
            for filters in [[]]+[[f] for f in additions]:
                configs.append(dict(mode=mode,stop=stop,filters=filters,slope=0))
    unique={json.dumps(c,sort_keys=True):c for c in configs}
    rows=[];month_rows=[]
    for i,c in enumerate(unique.values()):
        mask=signal_mask(d,c)
        annual=simulate(d,mask,c,'2025-10-01','2026-09-30')
        good=set(annual.loc[annual.Status=='Good','CandleTimeUK']) if not annual.empty else set()
        summaries=[]
        for period in months:
            t=annual[annual.CandleTimeUK.str.startswith(str(period))] if not annual.empty else annual
            s=stats(t);summaries.append(s);month_rows.append(dict(ID=i,Month=str(period),Partial=(str(period)=='2025-10'),**s))
        full=summaries[1:]
        rows.append(dict(ID=i,Config=json.dumps(c,sort_keys=True),RetainedGood=len(good_times&good),ReferenceGood=len(good_times),RetainedSeptemberGood=len(sep_good&good),SeptemberReferenceGood=len(sep_good),MonthsAt60=sum(s['Trades']>0 and s['Success']>=60 for s in summaries),WorstFullMonth=min(s['Success'] for s in full),MinFullMonthTrades=min(s['Trades'] for s in full),**stats(annual)))
        if i%250==0: print(f'Evaluated {i}/{len(unique)} candidates',flush=True)
    ranked=pd.DataFrame(rows)
    ranked.to_csv(a.output/'annual_candidates.csv',index=False)
    pd.DataFrame(month_rows).to_csv(a.output/'monthly_candidates.csv',index=False)
    # Rank on the worst monthly result, then overall cost-stressed return.
    eligible=ranked[(ranked.RetainedGood==ranked.ReferenceGood)&(ranked.MinFullMonthTrades>=1)]
    ordered=eligible.sort_values(['WorstFullMonth','MonthsAt60','Net10bpPct'],ascending=False)
    best=ordered.iloc[0]
    selected=json.loads(best.Config)
    (a.output/'best_retaining_all_months_config.json').write_text(json.dumps(selected,indent=2))
    t=simulate(d,signal_mask(d,selected),selected,'2025-10-01','2026-09-30')
    t.to_csv(a.output/'best_retaining_all_months_trades.csv',index=False)
    pd.DataFrame(month_rows).query('ID==@best.ID').to_csv(a.output/'best_retaining_all_months_results.csv',index=False)
    print('BEST RETAINING EVERY REFERENCE WINNER')
    print(ordered.head(10).to_string(index=False))
    print('BEST RETAINING REVIEWED SEPTEMBER WINNERS')
    print(ranked[(ranked.RetainedSeptemberGood==ranked.SeptemberReferenceGood)&(ranked.MinFullMonthTrades>=1)].sort_values(['WorstFullMonth','MonthsAt60','Net10bpPct'],ascending=False).head(10).to_string(index=False))
    print('Unconstrained monthly rank (missed winners remain explicit):')
    print(ranked[ranked.MinFullMonthTrades>=5].sort_values(['WorstFullMonth','MonthsAt60','Net10bpPct'],ascending=False).head(10).to_string(index=False))


if __name__=='__main__':main()
