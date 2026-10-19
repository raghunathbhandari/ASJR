#!/usr/bin/env python3
"""Research-only DDB Group A/B: 1y swing legs, support and historic upside.
No orders, no bot interactions.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'RudraScanner'/'ResearchData'/'DDB_OPPOSITE_2026-10-16'
OUT.mkdir(parents=True,exist_ok=True)
A=['INTC','AKAM','WDC','STX','KLAC']
B=['CBOE','ZTS','V','CME','CDW']
SECTOR={'INTC':'Semiconductors','AKAM':'Cybersecurity','WDC':'Storage','STX':'Storage','KLAC':'Semiconductor equipment','CBOE':'Financials','ZTS':'Health care','V':'Financials','CME':'Financials','CDW':'Technology'}
END=pd.Timestamp('2026-10-15')
def zigzag(values,threshold=.065):
    v=np.asarray(values,dtype=float); direction=0; extreme=0; piv=[]
    for i in range(1,len(v)):
        if direction==0:
            if v[i]>=v[extreme]*(1+threshold): piv.append((extreme,'LOW'));extreme=i;direction=1
            elif v[i]<=v[extreme]*(1-threshold):piv.append((extreme,'HIGH'));extreme=i;direction=-1
            elif v[i]>v[extreme] and v[extreme]>=v[0]:extreme=i
            elif v[i]<v[extreme] and v[extreme]<=v[0]:extreme=i
        elif direction==1:
            if v[i]>v[extreme]:extreme=i
            elif v[i]<=v[extreme]*(1-threshold):piv.append((extreme,'HIGH'));extreme=i;direction=-1
        else:
            if v[i]<v[extreme]:extreme=i
            elif v[i]>=v[extreme]*(1+threshold):piv.append((extreme,'LOW'));extreme=i;direction=1
    return piv
def main():
    rows=[];details=[]
    for group,tickers in [('A',A),('B',B)]:
        for t in tickers:
            try:
                d=yf.download(t,period='2y',interval='1d',auto_adjust=True,progress=False,threads=False)
                if isinstance(d.columns,pd.MultiIndex):d.columns=d.columns.get_level_values(0)
                c=pd.to_numeric(d['Close'],errors='coerce').dropna()
                c.index=pd.to_datetime(c.index).tz_localize(None).normalize()
                c=c.loc[c.index<=END].tail(253)
                if len(c)<180:raise ValueError('Insufficient 1-year bars')
                one_year=c.to_numpy();p=zigzag(one_year)
                legs=[(a,b,100*(one_year[b]/one_year[a]-1)) for (a,_),(b,_) in zip(p,p[1:])]
                major=[v for v in legs if abs(v[2])>=25]
                tail=c.tail(64); recent20=c.tail(20)
                # Historical support is a *reference band* not confirmed future bottom.
                # Lowest 10-20 closing values within latest 64 sessions define a lower zone.
                lows=tail.nsmallest(min(10,len(tail)))
                bot_lo=float(lows.min()); bot_hi=float(lows.max())
                target=float(tail.max()); last=float(tail.iloc[-1])
                lo_potential=100*(target/bot_hi-1) if bot_hi else np.nan
                hi_potential=100*(target/bot_lo-1) if bot_lo else np.nan
                rows.append(dict(group=group,ticker=t,sector=SECTOR[t],
                    swings_25pct_1y=len(major),
                    swing_up_25pct_1y=sum(x[2]>0 for x in major),
                    swing_down_25pct_1y=sum(x[2]<0 for x in major),
                    possible_bottom_low=round(bot_lo,2),possible_bottom_high=round(bot_hi,2),
                    previous_3m_high=round(target,2),upside_from_bottom_min_pct=round(lo_potential,1),
                    upside_from_bottom_max_pct=round(hi_potential,1),
                    last_close=round(last,2),date=str(tail.index[-1].date()),sessions_1y=len(c),status='OK'))
                for a,b,pct in major:
                    details.append({'ticker':t,'group':group,'start':str(c.index[a].date()),'end':str(c.index[b].date()),'change_pct':round(pct,2)})
                print('DONE',t,len(major),flush=True)
            except Exception as e:
                rows.append({'group':group,'ticker':t,'sector':SECTOR[t],'status':f'ERROR:{type(e).__name__}'})
                print('ERROR',t,repr(e),flush=True)
    df=pd.DataFrame(rows);df.to_csv(OUT/'RUDRA_DDB_GROUPS_1Y_SWINGS_AOI.csv',index=False)
    pd.DataFrame(details).to_csv(OUT/'RUDRA_DDB_GROUPS_1Y_MAJOR_LEGS.csv',index=False)
    lines=['# Rudra-DDB — Group A/B one-year major swing counts and bottom AOIs','',
        'Historical daily adjusted closes ending no later than October 15, 2026; not live.',
        '**Major swing definition:** completed zigzag price leg >=25%, direction change threshold 6.5%, based on adjusted daily closes.',
        '**Possible bottom area:** span of the 10 lowest closing values in the latest 64 trading sessions; exploratory historical support, not verified reversal support. Can lie below or above current price.',
        '**Future top:** historical 64-session highest daily close, NOT an expected price or a forecast.',
        '**Potential upside:** distance from either edge of bottom zone to the 64-session historical high. Does not incorporate a stop loss or confirmation.',
        'All prices are USD; revalidate adjustments, volatility, corporate actions, catalysts and actual reversal structure.',
        '',
        '| Group | Ticker (sector) | Swings 25%+ in 1Y | Possible bottom area | Historical high upside from bottom |',
        '|---|---|---:|---:|---:|']
    for _,r in df.iterrows():
        if r.status!='OK':
            lines.append(f"| {r.group} | {r.ticker} ({r.sector}) | — | — | — |")
        else:
            lines.append(f"| {r.group} | {r.ticker} ({r.sector}) | {int(r.swings_25pct_1y)} | ${r.possible_bottom_low:.2f}–${r.possible_bottom_high:.2f} | +{r.upside_from_bottom_min_pct:.1f}% to +{r.upside_from_bottom_max_pct:.1f}% |")
    lines+=['','**Note:** A high-side Group B name may not be near its candidate bottom zone. Group labels are historical phases, not buy/sell signals.',
            'Fundamental verification and bullish CHOCH are mandatory before considering entry.']
    (OUT/'RUDRA_DDB_GROUPS_1Y_SWINGS_AOI.md').write_text('\n'.join(lines)+'\n')
    print('GROUPS SUMMARY',df[['ticker','status','swings_25pct_1y']].to_string(index=False),flush=True)
if __name__=='__main__':main()
