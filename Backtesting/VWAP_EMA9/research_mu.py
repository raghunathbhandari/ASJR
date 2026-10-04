"""Reproducible, chronological MU buy-detector research.

Research only. Indicators use completed bars, entries assume signal-close fills,
and exits remain stop / close below EMA9 / session close. Never removes losing
bars or trades. Selection period is explicit; all tried candidates are exported.
September selection is in-sample research, not independent validation.
"""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import numpy as np
import pandas as pd
from buy_close_detector import generate_buy_signals


def indicators(bars):
    d = generate_buy_signals(bars)
    prev = d.Close.shift()
    tr = pd.concat([d.High-d.Low, (d.High-prev).abs(), (d.Low-prev).abs()], axis=1).max(axis=1)
    # Explicit Wilder SMA seed, then recursive smoothing.
    def rma(s, n=14):
        a = s.to_numpy(float); out = np.full(len(a), np.nan)
        valid = np.flatnonzero(np.isfinite(a))
        if not len(valid): return pd.Series(out, index=s.index)
        first = valid[0]+n-1
        if first >= len(a): return pd.Series(out, index=s.index)
        out[first] = a[first-n+1:first+1].mean()
        for i in range(first+1, len(a)):
            out[i] = (out[i-1]*(n-1)+a[i])/n
        return pd.Series(out, index=s.index)
    d['ATR'] = rma(tr)
    # CHOP measures range efficiency, not bullish direction. Use it only
    # alongside the existing above-VWAP, above-EMA BUY rules.
    span14=(d.High.rolling(14).max()-d.Low.rolling(14).min()).replace(0,np.nan)
    d['CHOP14']=100*np.log10(tr.rolling(14).sum()/span14)/np.log10(14)
    money_multiplier=((2*d.Close-d.High-d.Low)/(d.High-d.Low).replace(0,np.nan)).fillna(0)
    d['CMF20']=(money_multiplier*d.Volume).rolling(20).sum()/d.Volume.rolling(20).sum().replace(0,np.nan)
    d['CMF5']=(money_multiplier*d.Volume).rolling(5).sum()/d.Volume.rolling(5).sum().replace(0,np.nan)
    change = d.Close.diff()
    gain, loss = rma(change.clip(lower=0)), rma(-change.clip(upper=0))
    d['RSI'] = 100-100/(1+gain/loss.replace(0, np.nan))
    d.loc[(loss==0)&(gain>0), 'RSI'] = 100
    d['RSISlope3']=d.RSI-d.RSI.shift(3)
    macd=d.Close.ewm(span=12,adjust=False,min_periods=26).mean()-d.Close.ewm(span=26,adjust=False,min_periods=26).mean()
    d['MACDHistogram']=macd-macd.ewm(span=9,adjust=False,min_periods=9).mean()
    up, down = d.High.diff(), -d.Low.diff()
    plus = rma(up.where((up>down)&(up>0),0))/d.ATR*100
    minus = rma(down.where((down>up)&(down>0),0))/d.ATR*100
    d['DIPlus'], d['DIMinus'] = plus, minus
    d['DIRatio']=plus/minus.replace(0,np.nan)
    d['ADX'] = rma((plus-minus).abs()/(plus+minus).replace(0,np.nan)*100)
    d['Efficiency'] = (d.Close-d.Close.shift(5))/d.Close.diff().abs().rolling(5).sum().replace(0,np.nan)
    d['EMASlopeATR'] = (d.EMA9-d.EMA9.shift(3))/d.ATR
    d['EMAGapATR'] = (d.Close-d.EMA9)/d.ATR
    d['CloseLocation'] = (d.Close-d.Low)/(d.High-d.Low).replace(0,np.nan)
    d['RVOL'] = d.Volume/d.Volume.shift().rolling(20).median().replace(0,np.nan)
    d['Slot'] = d.Datetime.dt.tz_convert('America/New_York').dt.strftime('%H:%M')
    d['TimeRVOL'] = d.Volume/d.groupby('Slot').Volume.transform(lambda s:s.shift().rolling(20,min_periods=10).median()).replace(0,np.nan)
    # Only regular-session observations belong in the regular-volume template;
    # an early-close day's after-hours bars must not lower its historical mean.
    regular_volume=d.Volume.where(d.RTH)
    d['TimeRVOLMean']=d.Volume/regular_volume.groupby(d.Slot).transform(lambda s:s.shift().rolling(20,min_periods=10).mean()).replace(0,np.nan)
    rth_volume=d.Volume.where(d.RTH,0).groupby(d.Session).cumsum()
    d['CumulativeRVOL']=rth_volume/rth_volume.groupby(d.Slot).transform(lambda s:s.shift().rolling(20,min_periods=10).mean()).replace(0,np.nan)
    d['ATRpct']=d.ATR/d.Close*100
    d['RangeATR']=(d.High-d.Low)/d.ATR
    d['ATRExpansion']=d.ATR/d.ATR.shift(5)
    bb_width=d.Close.rolling(20).std(ddof=0)*4/d.Close.rolling(20).mean()
    d['BBExpansion']=bb_width/bb_width.shift(3).replace(0,np.nan)
    d['EMAChopCount']=(np.sign(d.Close-d.EMA9)!=np.sign(d.Close.shift()-d.EMA9.shift())).shift().rolling(12).sum()
    d['HigherLowCount5']=(d.Low>d.Low.shift()).rolling(4).sum()
    d['SwingLow5'] = d.groupby('Session').Low.transform(lambda s:s.rolling(5).min())
    d['PriorHigh3'] = d.groupby('Session').High.transform(lambda s:s.shift().rolling(3).max())
    d['Reclaim'] = (d.Close.shift()<=d.EMA9.shift()) & (d.Close>d.EMA9)
    # A recent EMA touch is an observable pullback, not a future pivot.
    d['RecentTouch'] = (d.Low<=d.EMA9).shift().rolling(3).max().eq(1)
    d['Bull'] = d.Close>d.Open
    span=(d.High-d.Low).replace(0,np.nan)
    d['BodyFraction']=(d.Close-d.Open).abs()/span
    d['UpperWickFraction']=(d.High-d[['Open','Close']].max(axis=1))/span
    d['BullEngulfing']=(d.Close>d.Open)&(d.Close.shift()<d.Open.shift())&(d.Open<=d.Close.shift())&(d.Close>=d.Open.shift())
    d['EMA21'] = d.Close.ewm(span=21,adjust=False,min_periods=21).mean()
    d['VWAPRising'] = (d.VWAP>d.VWAP.shift(3)) & d.VWAPSession.eq(d.VWAPSession.shift(3))
    d['ClearEMA'] = d.Low>d.EMA9
    d['ClearVWAP'] = d.Low>d.VWAP
    # A 15-minute bar is available only at its end, including the signal's
    # close time. No forward-filled unfinished higher-timeframe candle.
    ht=d.set_index('Datetime').resample('15min',label='right',closed='left').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
    ht['HTEMA9']=ht.Close.ewm(span=9,adjust=False,min_periods=9).mean()
    ht['HTRising']=ht.HTEMA9>ht.HTEMA9.shift(2)
    ht['HTAbove']=ht.Close>ht.HTEMA9
    aligned=pd.merge_asof(pd.DataFrame({'Available':d.Datetime+pd.Timedelta(minutes=5)}),ht.reset_index().rename(columns={'Datetime':'Available'})[['Available','HTEMA9','HTRising','HTAbove']],on='Available',direction='backward')
    d['HTRising']=aligned.HTRising.eq(True)
    d['HTAbove']=aligned.HTAbove.eq(True)
    d['SessionHigh']=d.groupby('Session').High.cummax().groupby(d.Session).shift()
    return d


def signal_mask(d, c):
    base = d.RTH & (d.Close>d.VWAP) & (d.Close>d.EMA9) & (d.Volume>0)
    # Retain five-bar positive high/low movement to avoid flat ranges.
    trend = d.Trend5 & (d.EMASlopeATR>=c.get('slope',0))
    mode = c['mode']
    if mode=='break10': m=base & trend & d.EMA9Rising & d.RangeBreak
    elif mode=='break3': m=base & trend & d.EMA9Rising & (d.Close>d.PriorHigh3)
    elif mode=='trend': m=base & trend & d.EMA9Rising
    elif mode=='pullback': m=base & trend & d.RecentTouch & d.Bull
    elif mode=='reclaim': m=base & d.Reclaim & (d.EMA9>d.EMA9.shift()) & d.Trend5
    elif mode=='early': m=base & trend & (d.EMA9>d.EMA9.shift()) & (d.Close>d.PriorHigh3) & d.Bull
    else: raise ValueError(mode)
    for name, value in c.get('filters',[]):
        if name=='eff': m &= d.Efficiency>=value
        elif name=='rvol': m &= d.TimeRVOL>=value
        elif name=='adx': m &= (d.ADX>=value)&(d.DIPlus>d.DIMinus)
        elif name=='rsi': m &= d.RSI.between(*value)
        elif name=='location': m &= d.CloseLocation>=value
        elif name=='gap': m &= d.EMAGapATR<=value
        elif name=='vwapgap': m &= (d.Close-d.VWAP)/d.ATR<=value
        elif name=='time': m &= d.Slot.between(*value)
        elif name=='adxmax': m &= d.ADX<=value
        elif name=='move': m &= d.TrendMovePct5>=value
        elif name=='slope': m &= d.EMASlopeATR>=value
        elif name=='ema21': m &= (d.EMA9>d.EMA21)&(d.EMA21>d.EMA21.shift(3))
        elif name=='vwaprise': m &= d.VWAPRising
        elif name=='clearema': m &= d.ClearEMA
        elif name=='clearvwap': m &= d.ClearVWAP
        elif name=='ht': m &= d.HTRising & d.HTAbove
        elif name=='sessionbreak': m &= d.Close>d.SessionHigh
        elif name=='bull': m &= d.Bull
        elif name=='body': m &= d.BodyFraction>=value
        elif name=='upperwick': m &= d.UpperWickFraction<=value
        elif name=='chop': m &= d.CHOP14<=value
        elif name=='cmf': m &= d.CMF20>=value
        elif name=='di': m &= d.DIRatio>=value
        elif name=='rvolmean': m &= d.TimeRVOLMean>=value
        elif name=='cumvol': m &= d.CumulativeRVOL>=value
        elif name=='atrpct': m &= d.ATRpct.between(*value)
        elif name=='rangeatr': m &= d.RangeATR.between(*value)
        elif name=='atrexpand': m &= d.ATRExpansion>=value
        elif name=='bbexpand': m &= d.BBExpansion>=value
        elif name=='emacrosses': m &= d.EMAChopCount<=value
        elif name=='higherlows': m &= d.HigherLowCount5>=value
        elif name=='cmf5': m &= d.CMF5>=value
        elif name=='macdhist': m &= d.MACDHistogram>=value
        elif name=='rsislope': m &= d.RSISlope3>=value
        elif name=='dirange': m &= d.DIRatio.between(*value)
        else: raise ValueError(name)
    return m.fillna(False).to_numpy()


def simulate(d, mask, c, start, end):
    ids=np.flatnonzero((d.Session.between(start,end)&d.RTH).to_numpy())
    o,h,l,cl,ema,atr,sw=(d[x].to_numpy(float)[ids] for x in ['Open','High','Low','Close','EMA9','ATR','SwingLow5'])
    ses=d.Session.to_numpy()[ids]; sig=mask[ids]; trades=[]; i=0
    while i<len(ids)-1:
        if not sig[i] or ses[i]!=ses[i+1]: i+=1; continue
        stop=l[i]-.01 if c['stop']=='signal' else sw[i]-.01 if c['stop']=='swing5' else min(sw[i]-.01,cl[i]-atr[i])
        j=i+1
        while j<len(ids):
            if o[j]<=stop: price,reason=o[j],'SL gap'
            elif l[j]<=stop: price,reason=stop,'SL hit'
            elif cl[j]<ema[j]: price,reason=cl[j],'EMA9 exit'
            elif j==len(ids)-1 or ses[j]!=ses[j+1]: price,reason=cl[j],'RTH end'
            else: j+=1; continue
            ret=(price/cl[i]-1)*100
            trades.append(dict(CandleTimeUK=str(d.CandleTimeUK.iloc[ids[i]]),Entry=cl[i],Stop=stop,ExitCandleUK=str(d.CandleTimeUK.iloc[ids[j]]),Exit=price,Reason=reason,Status='Good' if ret>0 else 'Bad' if ret<0 else 'Flat',GainPct=ret,R=(price-cl[i])/(cl[i]-stop),MFEpct=(h[i+1:j+1].max()/cl[i]-1)*100,MAEpct=(l[i+1:j+1].min()/cl[i]-1)*100))
            break
        i=j+1
    return pd.DataFrame(trades)


def stats(t):
    if t.empty: return dict(Trades=0,Good=0,Bad=0,Success=0,CompoundPct=0,Net10bpPct=0,NetSuccess=0,ProfitFactor=0)
    r=t.GainPct
    return dict(Trades=len(t),Good=int((r>0).sum()),Bad=int((r<0).sum()),Success=float((r>0).mean()*100),CompoundPct=float(((1+r/100).prod()-1)*100),Net10bpPct=float(((1+(r-.1)/100).prod()-1)*100),NetSuccess=float((r>.1).mean()*100),ProfitFactor=float(r.clip(lower=0).sum()/(-r.clip(upper=0).sum())) if (r<0).any() else float('inf'))


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--csv',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--selection',choices=['Development','September'],default='Development')
    p.add_argument('--minimum-trades',type=int,default=12)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    d=indicators(pd.read_csv(a.csv))
    periods={'Development':('2026-09-01','2026-09-18'),'SeptemberCheck':('2026-09-21','2026-09-30'),'September':('2026-09-01','2026-09-30'),'May':('2026-05-01','2026-05-31'),'June':('2026-06-01','2026-06-30'),'July':('2026-07-01','2026-07-31'),'August':('2026-08-01','2026-08-31'),'October':('2026-10-01','2026-10-02')}
    options=[[],[('eff',.5)],[('eff',.7)],[('rvol',1)],[('rvol',1.5)],[('adx',20)],[('rsi',[50,70])],[('rsi',[55,75])],[('location',.75)],[('gap',1)],[('gap',1.5)],[('vwapgap',2)],[('time',['09:50','12:00'])],[('time',['12:00','15:30'])],[('eff',.5),('gap',1.5)],[('rvol',1),('eff',.5)]]
    # Second review: finite, interpretable momentum/trend hypotheses. This
    # revision follows examination of the first separate-date check, so those
    # dates are no longer an untouched holdout. June is final fresh check.
    more=[[('eff',.9)],[('rsi',[60,80])],[('rsi',[65,80])],[('adxmax',25)],[('move',.5)],[('move',.75)],[('slope',.75)],[('slope',1)],[('ema21',True)],[('vwaprise',True)],[('clearema',True)],[('clearvwap',True)],[('ht',True)],[('sessionbreak',True)]]
    options += more + [a+b for a,b in itertools.combinations(more,2)]
    configs=[dict(mode=mode,stop=stop,filters=f,slope=0) for mode,stop,f in itertools.product(['break10','break3','trend','pullback','reclaim','early'],['signal','swing5','swingATR'],options)]
    # Recorded follow-up thresholds and combinations tested after chart review.
    for slope,cap,mode,clear in itertools.product([.4,.5,.6],[20,25,30],['trend','break10'],[False,True]):
        configs.append(dict(mode=mode,stop='swing5',filters=[['slope',slope],['adxmax',cap]]+([['clearema',True]] if clear else []),slope=0))
    for mode in ['trend','break10','break3']:
        for f in [[],[('eff',.5)],[('eff',.7)],[('clearvwap',True)],[('clearema',True)],[('rvol',1)],[('rvol',1.5)],[('location',.75)],[('ht',True)],[('ema21',True)],[('time',['09:50','15:30'])],[('eff',.7),('clearema',True)],[('eff',.7),('clearvwap',True)]]:
            configs.append(dict(mode=mode,stop='swing5',filters=[['adxmax',25],['slope',.6]]+f,slope=0))
    rows=[]
    for n,c in enumerate(configs):
        mask=signal_mask(d,c)
        row=dict(ID=n,Config=json.dumps(c,sort_keys=True))
        # Evaluate only the requested selection window during candidate search.
        row.update({'Development_'+k:v for k,v in stats(simulate(d,mask,c,*periods['Development'])).items()});rows.append(row)
        if a.selection=='September': row.update({'September_'+k:v for k,v in stats(simulate(d,mask,c,*periods['September'])).items()})
    ranked=pd.DataFrame(rows)
    eligible=ranked[ranked[a.selection+'_Trades']>=a.minimum_trades].sort_values([a.selection+'_Success',a.selection+'_Net10bpPct'],ascending=False)
    ranked.to_csv(a.output/'all_candidates.csv',index=False)
    selected=int(eligible.iloc[0].ID) if len(eligible) else 0
    selected_c=configs[selected]
    review_ids=list(dict.fromkeys([0,selected]+eligible.ID.head(10).tolist()))
    reviewed=[]
    for n in review_ids:
        c=configs[n]; mask=signal_mask(d,c)
        for label,period in periods.items():
            t=simulate(d,mask,c,*period)
            reviewed.append(dict(ID=n,Period=label,Config=json.dumps(c,sort_keys=True),**stats(t)))
            if n in [0,selected]: t.to_csv(a.output/f'{"baseline" if n==0 else "selected"}_{label}.csv',index=False)
    pd.DataFrame(reviewed).to_csv(a.output/'separate_date_checks.csv',index=False)
    meta=dict(data_sha256=hashlib.sha256(a.csv.read_bytes()).hexdigest(),bars=len(d),coverage=[str(d.Datetime.min()),str(d.Datetime.max())],candidates=len(configs),selection=f'Highest {a.selection} win rate, minimum {a.minimum_trades} trades; net return tie breaker',selected_id=selected,selected_config=selected_c,periods=periods,assumptions='BUY RTH; signal-close hypothetical fills; signal low / swing stop; EMA9 close exit; no fixed target; raw and 10bp round-trip cost stress test; UTC midnight VWAP provisional; MFE/MAE include exit bar, whose intrabar sequence is unknown')
    (a.output/'manifest.json').write_text(json.dumps(meta,indent=2))
    print(eligible.head(15).to_string(index=False))
    print(pd.DataFrame(reviewed).query('ID==@selected').to_string(index=False))
    d.to_pickle(a.output/'indicators.pkl')


if __name__=='__main__': main()
