"""MU September–October 2026 Rudra Three-Candle research backtest.

Requires: pip install yfinance pandas
Run: python three_candle/backtest_mu_filtered.py
Or:  python three_candle/backtest_mu_filtered.py --csv /path/to/MU_5m.csv

Research-only: BUY C1/C2/C3 and SELL C1/C2/C3/C4 pattern semantics
preserved. Enter ONLY at next 15m candle open after full confirmation,
not during C3/C4. C2 low / C3 high structural SL must be <= 0.20% from
actual executable entry. 1R is 0.20% of entry, target milestones trail
SL to last reached milestone without a fixed TP. Conservative stop-first
5m OHLC approximation, update trailing stop on NEXT 5m candle. No fees,
slippage, borrowing, spreads, partial fills or gap guarantee.

Data downloaded with Yahoo 5m (provider historical retention applies).
The download will fail rather than silently backfill missing periods.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

R = 0.002
START, END_EXCLUSIVE = "2026-09-01", "2026-10-31"
OUT = Path(__file__).resolve().parent / "results"

def download_mu():
    import yfinance as yf
    # Yahoo 5m requests often have a 60-day window; small chunks are safer.
    chunks = []
    for begin in pd.date_range(START, "2026-10-30", freq="5D", tz="UTC"):
        end = min(begin + pd.Timedelta(days=5), pd.Timestamp(END_EXCLUSIVE, tz="UTC"))
        part = yf.download("MU", start=begin.date().isoformat(),
                           end=end.date().isoformat(), interval="5m",
                           prepost=False, auto_adjust=False,
                           progress=False, threads=False)
        if part.empty:
            continue
        if isinstance(part.columns, pd.MultiIndex):
            part.columns = part.columns.get_level_values(0)
        if part.index.tz is None:
            raise ValueError("MU download missing timezone")
        chunks.append(part[["Open", "High", "Low", "Close", "Volume"]])
    if not chunks:
        raise RuntimeError("No MU 5m candles fetched; supply --csv with archived 5m OHLCV.")
    return pd.concat(chunks).sort_index().loc[
        lambda x: ~x.index.duplicated(keep="last")]

def load_csv(path):
    df = pd.read_csv(path)
    time = next((c for c in ("Datetime_UTC", "Datetime", "timestamp", "datetime", "Date") if c in df), None)
    if time is None:
        raise ValueError("CSV must contain a datetime column")
    idx = pd.to_datetime(df.pop(time), utc=True)
    df.index = idx
    df.columns = [c.title() for c in df.columns]
    return df[["Open","High","Low","Close","Volume"]].sort_index()

def prepare(raw):
    raw = raw.copy()
    raw.index = raw.index.tz_convert("America/New_York")
    raw = raw.between_time("09:30", "15:59")
    raw = raw[(raw.index.date >= pd.Timestamp(START).date()) &
              (raw.index.date < pd.Timestamp(END_EXCLUSIVE).date())]
    if raw.empty:
        raise RuntimeError("No September–October RTH 5m candles")
    if raw.isna().any().any():
        raise ValueError("Missing price or volume values")
    if ((raw.High < raw[["Open","Close","Low"]].max(axis=1)) |
        (raw.Low > raw[["Open","Close","High"]].min(axis=1))).any():
        raise ValueError("Invalid OHLC envelope")
    frames=[]
    coverage=[]
    for d,day in raw.groupby(raw.index.date):
        expected = pd.date_range(pd.Timestamp(d, tz="America/New_York") +
                pd.Timedelta(hours=9, minutes=30), periods=78, freq="5min")
        # Only complete days. Any missing bar excludes the whole session.
        if not expected.isin(day.index).all():
            coverage.append((str(d), len(day), "INCOMPLETE"))
            continue
        day=day.loc[expected]
        fifteen=pd.DataFrame({
            "Open":day.Open.resample("15min", origin=expected[0]).first(),
            "High":day.High.resample("15min", origin=expected[0]).max(),
            "Low":day.Low.resample("15min", origin=expected[0]).min(),
            "Close":day.Close.resample("15min", origin=expected[0]).last(),
            "Volume":day.Volume.resample("15min", origin=expected[0]).sum()
        }).dropna()
        if len(fifteen)==26:
            frames.append((d,day,fifteen))
            coverage.append((str(d),78,"COMPLETE"))
        else: coverage.append((str(d),len(day),"BAD_RESAMPLE"))
    if not frames:
        raise RuntimeError("Zero complete MU RTH sessions; inspect data coverage.")
    return frames,pd.DataFrame(coverage,columns=["date_et","bars_5m","status"])

def simulate(day, trigger, side, entry, structural_stop):
    """5m execution starting after full 15m confirmation."""
    after=day.loc[day.index >= trigger]
    if after.empty: return None
    first=after.iloc[0]
    # 'trigger' is actual entry timestamp, not signal candle.
    actual=float(first.Open)
    stop=float(structural_stop)
    stop_pct=100*abs(actual-stop)/actual
    if (side=="BUY" and stop>=actual) or (side=="SELL" and stop<=actual):
        return {"status":"REJECT_STOP_SIDE","stop_pct":stop_pct}
    if stop_pct>0.2+1e-8:
        return {"status":"REJECT_MAX_SL","stop_pct":stop_pct}
    direction = 1 if side=="BUY" else -1
    step=actual*R
    locked=0
    peak=0.0
    # Current stop is always available. New milestone stop activates
    # on the NEXT 5m bar; do not assume an intrabar path.
    for t,row in after.iterrows():
        o,h,l,c=map(float,(row.Open,row.High,row.Low,row.Close))
        if (direction==1 and o<=stop) or (direction==-1 and o>=stop):
            pnl=direction*(o-actual)/actual*100
            return {"status":"GAP_STOP","exit_uk":t.tz_convert("Europe/London").isoformat(),
                    "exit":o,"gain_pct":pnl,"max_milestone":peak,
                    "stop_pct":stop_pct,"entry":actual}
        if (direction==1 and l<=stop) or (direction==-1 and h>=stop):
            pnl=direction*(stop-actual)/actual*100
            return {"status":"STOP","exit_uk":t.tz_convert("Europe/London").isoformat(),
                    "exit":stop,"gain_pct":pnl,"max_milestone":peak,
                    "stop_pct":stop_pct,"entry":actual}
        favorable=(h-actual if direction==1 else actual-l)
        peak=max(peak,int(max(favorable,0)/step+1e-9))
        if peak>locked:
            locked=peak
            new_stop=actual + direction*locked*step
            stop=max(stop,new_stop) if direction==1 else min(stop,new_stop)
    last=after.iloc[-1]
    pnl=direction*(float(last.Close)-actual)/actual*100
    return {"status":"EOD","exit_uk":after.index[-1].tz_convert("Europe/London").isoformat(),
            "exit":float(last.Close),"gain_pct":pnl,"max_milestone":peak,
            "stop_pct":stop_pct,"entry":actual}

def backtest(frames):
    rows=[]
    for date,day,candles in frames:
        x=candles.reset_index()
        for i in range(2,len(x)):
            a,b,c=x.iloc[i-2],x.iloc[i-1],x.iloc[i]
            bbody=abs(b.Close-b.Open)
            cbody=abs(c.Close-c.Open)
            c3lower=(min(c.Open,c.Close)-c.Low)
            c3upper=(c.High-max(c.Open,c.Close))
            isbuy=(min(b.Open,b.Close)-b.Low>bbody and b.Low<a.Low
                   and c.Close>c.Open and c.High>min(b.Open,b.Close))
            # BUY confirms when C3 completes; enter C4 15m open.
            if isbuy and i+1<len(x):
                filt=(100*cbody/c.Close>=.06 and
                      cbody>0 and (c3upper+c3lower)/cbody<=1 and
                      100*(min(b.Open,b.Close)-b.Low)/b.Close>=.06)
                if filt:
                    entry_time=x.iloc[i+1,0]
                    result=simulate(day,entry_time,"BUY",float(x.iloc[i+1].Open),float(b.Low))
                    if result is not None:
                        rows.append(dict(date_et=str(date),side="BUY",
                          signal_uk=c.iloc[0].tz_convert("Europe/London").isoformat(),
                          entry_time_uk=entry_time.tz_convert("Europe/London").isoformat(),**result))
            # SELL confirms at C4 close; enter C5 15m open.
            if i+2<len(x):
                d=x.iloc[i+1]
                issell=(c.High>max(a.High,b.High) and d.Close<d.Open and
                        d.Low<min(c.Open,c.Close))
                if issell:
                    filt=(100*c3upper/c.Close>=.05 and
                          100*(b.High-b.Low)/b.Close>=.12)
                    if filt:
                        entry_time=x.iloc[i+2,0]
                        result=simulate(day,entry_time,"SELL",float(x.iloc[i+2].Open),float(c.High))
                        if result is not None:
                            rows.append(dict(date_et=str(date),side="SELL",
                              signal_uk=d.iloc[0].tz_convert("Europe/London").isoformat(),
                              entry_time_uk=entry_time.tz_convert("Europe/London").isoformat(),**result))
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",type=Path)
    ap.add_argument("--export-bars",action="store_true")
    args=ap.parse_args()
    raw=load_csv(args.csv) if args.csv else download_mu()
    if args.export_bars:
        data_dir=Path(__file__).resolve().parent / "data"
        data_dir.mkdir(parents=True,exist_ok=True)
        export=raw.copy()
        export.index=export.index.tz_convert("UTC")
        export.index.name="Datetime_UTC"
        export_path=data_dir / "MU_2026-09_10_5m_UTC.csv"
        export.to_csv(export_path)
        print(f"Raw MU 5m OHLCV saved: {export_path} ({len(export)} bars)")
    frames,coverage=prepare(raw)
    OUT.mkdir(exist_ok=True,parents=True)
    coverage.to_csv(OUT/"MU_2026-09_10_5m_coverage.csv",index=False)
    results=backtest(frames)
    if results.empty:
        print("No filtered MU signals; coverage and threshold may explain.")
        return
    results["month"]=results.date_et.str[:7]
    results.to_csv(OUT/"MU_2026-09_10_filtered_trades.csv",index=False)
    valid=results[results.status.isin(["STOP","GAP_STOP","EOD"])].copy()
    for group,name in [(valid,"TOTAL"),*[(g,n) for n,g in valid.groupby("month")],
                       *[(g,n) for n,g in valid.groupby("side")]]:
        if group.empty: continue
        win=(group.gain_pct>0).sum()
        print(f"{name}: trades={len(group)} wins={win}, win%={100*win/len(group):.2f} "
              f"sum_gain%={group.gain_pct.sum():+.3f}, "
              f"avg_gain%={group.gain_pct.mean():+.3f}, "
              f"worst_gain%={group.gain_pct.min():+.3f}")
    print("Rejected / valid:",results.status.value_counts().to_dict())
    print("Results:",OUT/"MU_2026-09_10_filtered_trades.csv")
    print("Coverage:",OUT/"MU_2026-09_10_5m_coverage.csv")
    print("WARNING: research-only, no spreads, commission, borrow fees, overlap or slippage.")

if __name__=="__main__":
    main()
