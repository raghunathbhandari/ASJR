#!/usr/bin/env python3
"""MES October 2026; original 15m equity pattern on MES plus NEW causal-entry replay.

The original C2-close plus C3 filter is retrospective (look-ahead). This
replay instead enters on the next 5m OPEN after completed C3, with the original
C2-open structural stop, a minimum 0.10% R step, and stop-first OHLC sequencing.
Not verified live execution; commission, slippage and tick path are excluded.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from original_three_candle import historical_signals, resample_rth_15m

DEFAULT_CSV = (Path(__file__).resolve().parent.parent /
               "three_candle/data/MESZ2026_IBKR_5m_2026-10.csv")


def load_data(csv_path: Path) -> pd.DataFrame:
    data = pd.read_csv(csv_path)
    required = ["Datetime_UTC", "Open", "High", "Low", "Close", "Volume"]
    missing = sorted(set(required) - set(data.columns))
    if missing:
        raise ValueError("Missing columns: " + ",".join(missing))
    idx = pd.DatetimeIndex(pd.to_datetime(data["Datetime_UTC"], utc=True))
    bars = data[required[1:]].apply(pd.to_numeric, errors="raise")
    bars.index = idx
    if bars.isna().any().any() or bars.index.has_duplicates:
        raise ValueError("Missing data or duplicated timestamps")
    return bars.sort_index()


def simulate(bars: pd.DataFrame, stop: float,
             fixed_r: int | None = None, trailing: bool = False) -> dict:
    if bars.empty:
        return {"status": "NO_NEXT_5M"}
    entry = float(bars.iloc[0].Open)
    if entry <= stop:
        return {"status": "INVALID_ENTRY", "entry": entry}
    step = max(entry-stop, entry*.001)
    active = stop
    highest_r = 0
    ambiguities = 0
    price = None
    for ts, bar in bars.iterrows():
        op, hi, lo = float(bar.Open), float(bar.High), float(bar.Low)
        next_milestone = entry + ((fixed_r or highest_r+1) * step)
        if lo <= active and hi >= next_milestone:
            ambiguities += 1
        if op <= active:
            price, reason, end_time = op, "GAP_STOP", ts
            break
        if lo <= active:
            price, reason, end_time = active, "STOP", ts
            break
        if fixed_r is not None and hi >= entry+fixed_r*step:
            price, reason, end_time = entry+fixed_r*step, "TARGET", ts
            break
        if trailing:
            reached = max(0, int((hi-entry+1e-9) // step))
            if reached > highest_r:
                highest_r = reached
                active = max(active, entry+reached*step)
    if price is None:
        price, reason, end_time = float(bars.iloc[-1].Close), "RTH_CLOSE", bars.index[-1]
    return {"status":reason,"entry":entry,"initial_stop":stop,"r_step":step,
            "exit":price,"exit_uk":str(end_time.tz_convert("Europe/London")),
            "points":price-entry,"trade_price_return_pct":100*(price-entry)/entry,
            "one_mes_gross_usd":5*(price-entry),
            "ambiguous_5m":ambiguities}


def run(csv_path: Path, start: str, end: str):
    raw = load_data(csv_path)
    candle15 = resample_rth_15m(raw,start,end)
    signals = historical_signals(candle15,"MES",.1)
    five = raw.copy()
    five.index = five.index.tz_convert("America/New_York")
    five = five.between_time("09:30","15:59")
    rows = []
    for _,s in signals.iterrows():
        c3 = pd.Timestamp(s.c3_start_uk)
        date = c3.tz_convert("America/New_York").date()
        after = five.loc[(five.index.date == date) &
                         (five.index >= (c3+pd.Timedelta(minutes=15)).tz_convert("America/New_York"))]
        row = {"trade_day":str(date),"c3_start_uk":str(c3),
               "original_entry":float(s.entry_reference),
               "original_stop":float(s.initial_stop_reference),
               **{f"original_{k}R_touch":int(s[f"hit_{k}R"]) for k in (1,2,3)}}
        for name, target, trail in (
                ("fixed_1R",1,False),("fixed_2R",2,False),
                ("fixed_3R",3,False),("step_trail",None,True)):
            for key,value in simulate(after,float(s.initial_stop_reference),
                                      target,trail).items():
                row[name+"_"+key] = value
        rows.append(row)
    return signals,pd.DataFrame(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv",type=Path,default=DEFAULT_CSV)
    p.add_argument("--start",default="2026-10-01")
    p.add_argument("--end",default="2026-10-30")
    p.add_argument("--verify-october",action="store_true")
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    signals,outcomes=run(args.csv,args.start,args.end)
    count=len(signals)
    print("MES original 15m pattern; EX-POST only:",count,"setups")
    touches=[int(signals[f"hit_{k}R"].sum()) if count else 0 for k in (1,2,3)]
    print("Historical touches 1R/2R/3R:",touches)
    if args.verify_october and (args.start,args.end,count,*touches)!=(
            "2026-10-01","2026-10-30",8,7,5,2):
        raise SystemExit("Archived MES October historical touch counts mismatch")
    for name in ("fixed_1R","fixed_2R","fixed_3R","step_trail"):
        key=name+"_points"
        if key not in outcomes:
            continue
        v=outcomes[key].dropna()
        print(name, "trades",len(v),"positive",int((v>0).sum()),
              "negative",int((v<0).sum()),"points",round(v.sum(),3),
              "gross USD/1 MES",round(5*v.sum(),2),
              "sum price return pct",round(outcomes[name+"_trade_price_return_pct"].sum(),4))
    if args.out:
        args.out.mkdir(parents=True,exist_ok=True)
        signals.to_csv(args.out/"MES_October_original_signals.csv",index=False)
        outcomes.to_csv(args.out/"MES_October_post_C3_replay.csv",index=False)
    print("WARNING: Historical touch rate != trading win rate. No transaction costs.")


if __name__ == "__main__":
    main()
