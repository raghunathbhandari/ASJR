"""Research learner: train only on earlier months, then score next-month BUYs.

Never uses dates, absolute prices, or future returns as prediction features.
Future returns appear only in historical training targets, with an explicit
exit-before-test-period purge. Three months are reserved for initial learning.
ModelScore is an uncalibrated model estimate, not a guaranteed win probability.
This experiment can fail the required retention and monthly success tests.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from research_mu import indicators, simulate, stats
from review_candle_patterns import retention_audit

FEATURES=['RSI','ADX','DIRatio','DIPlus','DIMinus','Efficiency','EMASlopeATR','EMAGapATR','TrendMovePct5','CloseLocation','BodyFraction','UpperWickFraction','TimeRVOL','TimeRVOLMean','CumulativeRVOL','ATRpct','RangeATR','ATRExpansion','BBExpansion','EMAChopCount','HigherLowCount5','RSISlope3','CHOP14','CMF20','CMF5','MACDHistATR','VWAPGapATR','HighSlopeATR','LowSlopeATR','MinutesFromOpen']


def feature_matrix(d):
    x=d.copy()
    x['MACDHistATR']=x.MACDHistogram/x.ATR
    x['VWAPGapATR']=(x.Close-x.VWAP)/x.ATR
    x['HighSlopeATR']=x.HighSlope5/x.ATR
    x['LowSlopeATR']=x.LowSlope5/x.ATR
    ny=x.Datetime.dt.tz_convert('America/New_York')
    x['MinutesFromOpen']=ny.dt.hour*60+ny.dt.minute-570
    return x[FEATURES].astype(float).replace([np.inf,-np.inf],np.nan)


def individual_labels(d, candidate):
    # These are hypothetical independently labelled setups, not a portfolio.
    # Executable one-position results are evaluated separately with simulate.
    ids=np.flatnonzero(d.RTH.to_numpy())
    o,l,cl,ema,sw=(d[k].to_numpy(float)[ids] for k in ['Open','Low','Close','EMA9','SwingLow5'])
    ses=d.Session.to_numpy()[ids]; rows=[]
    for i in range(len(ids)-1):
        if not candidate[ids[i]] or ses[i]!=ses[i+1]:continue
        stop=sw[i]-.01
        for j in range(i+1,len(ids)):
            if o[j]<=stop: price=o[j]
            elif l[j]<=stop: price=stop
            elif cl[j]<ema[j]: price=cl[j]
            elif j==len(ids)-1 or ses[j]!=ses[j+1]: price=cl[j]
            else:continue
            rows.append(dict(Row=ids[i],Session=ses[i],ExitDatetime=d.Datetime.iloc[ids[j]]+pd.Timedelta(minutes=5),Good=int(price>cl[i]),GainPct=(price/cl[i]-1)*100))
            break
    return pd.DataFrame(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv',type=Path,required=True);p.add_argument('--reference-trades',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    d=indicators(pd.read_csv(a.csv));x=feature_matrix(d)
    candidate=(d.BaseBuy&d.Trend5&(d.Volume>0)).to_numpy()
    labels=individual_labels(d,candidate)
    labels.to_csv(a.output/'historical_training_labels.csv',index=False)
    score=np.full(len(d),np.nan);training=[]
    # Architecture and thresholds are fixed before any test-month evaluation.
    for period in pd.period_range('2026-01','2026-09',freq='M'):
        start=str(period.start_time.date());end=str(period.end_time.date())
        cutoff=pd.Timestamp(start,tz='America/New_York').tz_convert('UTC')
        tr=labels[(labels.Session<start)&(labels.ExitDatetime<cutoff)]
        test=np.flatnonzero(d.Session.between(start,end).to_numpy()&candidate)
        assert (tr.ExitDatetime<cutoff).all()
        if len(tr)<150 or tr.Good.nunique()<2:continue
        model=HistGradientBoostingClassifier(max_depth=3,max_iter=150,min_samples_leaf=40,learning_rate=.05,l2_regularization=1,early_stopping=False,random_state=0)
        model.fit(x.iloc[tr.Row],tr.Good)
        if len(test): score[test]=model.predict_proba(x.iloc[test])[:,1]
        training.append(dict(Month=str(period),Samples=len(tr),LatestTargetExit=str(tr.ExitDatetime.max()),FirstTestTime=str(cutoff)))
        print(f'{period}: trained on {len(tr)} earlier setups',flush=True)
    pd.DataFrame(training).to_csv(a.output/'training_cutoffs.csv',index=False)
    d['ModelScore']=score
    d.loc[candidate,['Datetime','CandleTimeUK','ModelScore']].to_csv(a.output/'walkforward_scores.csv',index=False)
    previous=pd.read_csv(a.reference_trades)
    rows=[]
    for threshold in [.5,.6,.7,.8]:
        mask=candidate&np.isfinite(score)&(score>=threshold)
        c=dict(stop='swing5')
        t=simulate(d,mask,c,'2026-01-01','2026-09-30')
        t.to_csv(a.output/f'trades_score_{threshold}.csv',index=False)
        # simulate can return a completely empty table; keep months visible.
        for period in pd.period_range('2025-10','2026-09',freq='M'):
            month=str(period)
            part=t[t.CandleTimeUK.str.startswith(month)] if not t.empty else t
            reference=previous[previous.CandleTimeUK.str.startswith(month)]
            if t.empty: retained=0
            else: retained=int(retention_audit(reference,part).SameEntryGood.sum())
            rows.append(dict(Threshold=threshold,Month=month,Status='Initial training period; no OOS prediction' if month<'2026-01' else 'Walk-forward test',RetainedReferenceGood=retained,ReferenceGood=int(reference.Status.eq('Good').sum()),**stats(part)))
    table=pd.DataFrame(rows);table.to_csv(a.output/'monthly_walkforward_results.csv',index=False)
    (a.output/'model_manifest.json').write_text(json.dumps(dict(features=FEATURES,training='Expanding window; completed targets strictly earlier than test month',initial_training_months=['2025-10','2025-11','2025-12'],thresholds=[.5,.6,.7,.8],model='HistGradientBoostingClassifier: depth3,150iterations,40 minimum leaf samples,rate0.05,L2=1,seed0',warning='Scores uncalibrated; no live deployment; first 3 months cannot be OOS tested without earlier data'),indent=2))
    print(table.to_string(index=False))


if __name__=='__main__':main()
