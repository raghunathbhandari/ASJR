#!/usr/bin/env python3
"""Research-only expanded DDB: full 39-stock one-year swing counts.
Writes new evidence files, never trading commands or signals.
"""
from pathlib import Path
import pandas as pd
import yfinance as yf
from RudraScanner.research_ddb_groups_1y import zigzag

OUT=Path(__file__).resolve().parent/"ResearchData"/"DDB_OPPOSITE_2026-10-16"
A="INTC AKAM WDC STX KLAC CIEN TER LRCX VRT PANW AMD QCOM TSM SWKS CRWD ETN KEYS FLEX GLW COHR ASML AMAT".split()
B="CBOE ZTS V CME CDW PGR AJG JKHY O YUM VRSK MRSH NSC PEP PAYX NEE MCK".split()
CUTOFF=pd.Timestamp("2026-10-15")
def main():
    rows=[];legs=[]
    for group,names in [("A",A),("B",B)]:
        for ticker in names:
            try:
                raw=yf.download(ticker,period="2y",interval="1d",auto_adjust=True,progress=False,threads=False)
                if isinstance(raw.columns,pd.MultiIndex):
                    raw.columns=raw.columns.get_level_values(0)
                c=pd.to_numeric(raw["Close"],errors="coerce").dropna()
                c.index=pd.to_datetime(c.index).tz_localize(None).normalize()
                c=c.loc[c.index<=CUTOFF].tail(253)
                if len(c)<180: raise ValueError("INSUFFICIENT_HISTORY")
                v=c.to_numpy();p=zigzag(v,.065)
                confirmed=[]
                for (a,_),(b,_) in zip(p,p[1:]):
                    pct=float(100*(v[b]/v[a]-1))
                    if abs(pct)>=7:
                        legs.append(dict(group=group,ticker=ticker,start=str(c.index[a].date()),end=str(c.index[b].date()),change_pct=round(pct,2),ge_25=abs(pct)>=25))
                        confirmed.append(pct)
                rows.append(dict(group=group,ticker=ticker,sessions=len(c),last_date=str(c.index[-1].date()),one_year_legs_7pct=sum(abs(x)>=7 for x in confirmed),one_year_legs_10pct=sum(abs(x)>=10 for x in confirmed),one_year_legs_15pct=sum(abs(x)>=15 for x in confirmed),one_year_legs_25pct=sum(abs(x)>=25 for x in confirmed),one_year_min_close=round(float(c.min()),2),one_year_max_close=round(float(c.max()),2),one_year_range_pct=round(100*(c.max()/c.min()-1),1),status="OK"))
            except Exception as exc:
                rows.append(dict(group=group,ticker=ticker,status="ERROR:"+type(exc).__name__))
            print(group,ticker,rows[-1]["status"],flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT/"DDB_39_1Y_SWING_COUNTS_2026-10-16.csv",index=False)
    pd.DataFrame(legs).to_csv(OUT/"DDB_39_1Y_DATED_LEGS_2026-10-16.csv",index=False)
    print("SUMMARY",len(rows),"ok",sum(r["status"]=="OK" for r in rows),flush=True)
if __name__=="__main__":
    main()
