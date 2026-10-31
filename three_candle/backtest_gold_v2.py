#!/usr/bin/env python3
"""Rudra-Gold V2: independent, causal 15m C2 sweep / C3 confirmation study.

This is research software, NOT a validated live strategy. The 5m feed is Yahoo
GC=F (continuous futures); it may differ from TradingView COMEX:GC1!.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import numpy as np

DEFAULT_CSV = Path(__file__).parent / "data/multi_asset_5m/GOLD_20260901_20261031_5m_UTC.csv"


def load_bars(path: Path):
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    dt = "Datetime_UTC" if "Datetime_UTC" in df.columns else "Datetime"
    df.index = pd.to_datetime(df[dt], utc=True)
    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
    df = df[~df.index.duplicated()].sort_index()
    if df.empty or df.isna().any().any():
        raise ValueError("Empty data or missing OHLCV values")
    agg = {"Open": "first", "High": "max", "Low": "min",
           "Close": "last", "Volume": "sum"}
    groups = df.resample("15min", origin="start_day", label="left", closed="left")
    bars15 = groups.agg(agg)
    counts = groups.size()
    # Do not fabricate 15m bars if the source lacks any constituent 5m bar.
    bars15 = bars15.loc[counts.eq(3)]
    return df, bars15


def candidates(bars: pd.DataFrame, day: str, min_sweep_atr: float,
               require_c3_extreme: bool):
    atr = (pd.concat([bars.High - bars.Low,
                      (bars.High - bars.Close.shift()).abs(),
                      (bars.Low - bars.Close.shift()).abs()], axis=1)
           .max(axis=1).rolling(14, min_periods=14).mean())
    vol_average = bars.Volume.shift(1).rolling(20, min_periods=20).mean()
    records = []
    for i in range(1, len(bars) - 2):
        c1, c2, c3, c4 = (bars.iloc[j] for j in (i-1, i, i+1, i+2))
        t1, t2, t3, t4 = (bars.index[j] for j in (i-1, i, i+1, i+2))
        if str(t2.date()) != day or any(
                (y-x) != pd.Timedelta(minutes=15) for x,y in
                ((t1,t2), (t2,t3), (t3,t4))):
            continue
        for side in ("BUY", "SELL"):
            long = side == "BUY"
            sweep = (c1.Low-c2.Low) if long else (c2.High-c1.High)
            if sweep <= 0 or pd.isna(atr.iloc[i]) or atr.iloc[i] <= 0:
                continue
            if sweep / atr.iloc[i] < min_sweep_atr:
                continue
            # C2 can close outside the prior range (Type B).
            # C3 must have a directional body and a lower high / higher low
            # relative to C2; it need NOT fully reclaim C1.
            directional = c3.Close > c3.Open if long else c3.Close < c3.Open
            extreme = c3.Low > c2.Low if long else c3.High < c2.High
            if not directional or (require_c3_extreme and not extreme):
                continue
            entry = float(c4.Open)
            stop = float(c2.Low if long else c2.High)
            risk = ((entry-stop)/entry if long else (stop-entry)/entry)*100
            if not 0 < risk <= 0.2:
                continue
            vratio = c2.Volume / vol_average.iloc[i] if vol_average.iloc[i]>0 else np.nan
            records.append(dict(day=day, side=side, c1=t1, c2=t2, c3=t3,
                                entry_time=t4, entry=entry, structural_stop=stop,
                                risk_pct=risk, sweep=float(sweep),
                                sweep_atr=float(sweep/atr.iloc[i]),
                                c2_rvol20=float(vratio), c2_volume=float(c2.Volume),
                                c3_volume=float(c3.Volume),
                                c2_reclaimed=bool(c2.Close>c1.Low if long else c2.Close<c1.High)))
    return pd.DataFrame(records)


def pivot_updates(bars15: pd.DataFrame, entry_time: pd.Timestamp,
                  now: pd.Timestamp, side: str, offset: float):
    # A 2-left / 2-right pivot is *available only after* two following 15m bars
    # have closed. Exclude pivots that occurred before entry.
    done = bars15.loc[bars15.index + pd.Timedelta(minutes=15) <= now]
    changes = []
    for i in range(2, len(done)-2):
        p = done.iloc[i]
        if done.index[i] < entry_time:
            continue
        if side == "SELL":
            good = p.High > max(done.High.iloc[i-2:i].max(),
                                done.High.iloc[i+1:i+3].max())
            if good: changes.append(float(p.High)+offset)
        else:
            good = p.Low < min(done.Low.iloc[i-2:i].min(),
                               done.Low.iloc[i+1:i+3].min())
            if good: changes.append(float(p.Low)-offset)
    return changes


def simulate(row, bars5, bars15, mode: str, session_end: str,
             pivot_offset: float, partial_fraction: float):
    entry, stop, side = float(row.entry), float(row.structural_stop), row.side
    direction = 1 if side == "BUY" else -1
    cutoff = pd.Timestamp(str(row.day) + "T" + session_end + ":00Z")
    window = bars5.loc[(bars5.index >= row.entry_time) & (bars5.index < cutoff)]
    if window.empty:
        return dict(outcome="NO_DATA", gain_pct=np.nan)
    stage = 0
    partial_taken = False
    locked_pct = 0.0
    previous_update = None
    history = []
    for t, x in window.iterrows():
        # Trail only using candles confirmed BEFORE this 5m bar.
        if mode in ("swing", "partial_swing") and t.minute % 15 == 0:
            options = pivot_updates(bars15, row.entry_time, t, side, pivot_offset)
            for candidate in options:
                if (side == "SELL" and candidate < stop and candidate > x.Open) or (
                    side == "BUY" and candidate > stop and candidate < x.Open):
                    stop = candidate
                    history.append(f"{t.isoformat()} pivot stop={stop:.3f}")
        # Conservative: any stop touched within a 5m bar wins priority over
        # targets/trailing changes inside that same 5m bar.
        stopped_open = direction*(x.Open-stop) <= 0
        stopped_bar = (x.Low <= stop if side == "BUY" else x.High >= stop)
        if stopped_open or stopped_bar:
            price = float(x.Open if stopped_open else stop)
            remaining = 1-partial_fraction if partial_taken else 1
            gain = locked_pct + remaining * direction*(price-entry)/entry*100
            return dict(outcome="WIN" if gain>0 else "LOSS" if gain<0 else "FLAT",
                        exit_time=t, exit_price=price, gain_pct=gain,
                        stop_at_exit=stop, events="; ".join(history))
        favorable = (x.High-entry if side == "BUY" else entry-x.Low)
        if mode == "step":
            k = max(0, int(np.floor(favorable/(entry*.002)+1e-9)))
            stage = max(k, stage)
            if stage:
                level = entry + direction*stage*entry*.002
                stop = max(stop, level) if side=="BUY" else min(stop, level)
        elif mode == "partial_swing" and not partial_taken and favorable >= entry*.002:
            partial_taken = True
            locked_pct = partial_fraction*.2
            stop = max(stop,entry) if side=="BUY" else min(stop,entry)
            history.append(f"{t.isoformat()} partial +0.20%")
    price = float(window.iloc[-1].Close)
    remaining = 1-partial_fraction if partial_taken else 1
    gain = locked_pct + remaining*direction*(price-entry)/entry*100
    return dict(outcome="WIN" if gain>0 else "LOSS" if gain<0 else "FLAT",
                exit_time=window.index[-1]+pd.Timedelta(minutes=5),
                exit_price=price,gain_pct=gain,stop_at_exit=stop,
                events="; ".join(history), exit_reason="SESSION_MARK")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    p.add_argument("--date", default="2026-10-30")
    p.add_argument("--mode", choices=["step","swing","partial_swing"], default="swing")
    p.add_argument("--min-sweep-atr", type=float, default=0.0)
    p.add_argument("--no-c3-extreme", action="store_true")
    p.add_argument("--daily-cap", type=int, default=0,
                   help="0: all qualifying trades; positive: first N chronological, not hindsight best N")
    p.add_argument("--session-end", default="21:00", help="UTC HH:MM")
    p.add_argument("--pivot-offset", type=float, default=0.2, help="Gold dollars")
    p.add_argument("--partial-fraction", type=float, default=0.5)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    b5,b15 = load_bars(args.csv)
    signals = candidates(b15, args.date, args.min_sweep_atr, not args.no_c3_extreme)
    if args.daily_cap:
        signals = signals.sort_values("entry_time").head(args.daily_cap)
    result=[]
    for row in signals.itertuples(index=False):
        result.append({**row._asdict(), **simulate(row,b5,b15,args.mode,
                          args.session_end,args.pivot_offset,args.partial_fraction)})
    d = pd.DataFrame(result)
    print(f"Rudra-Gold V2 | {args.date} | mode={args.mode} | raw eligible={len(signals)}")
    if d.empty:
        print("No eligible trades.")
        return
    print(d[["side","c2","entry_time","entry","structural_stop","risk_pct",
             "sweep_atr","c2_rvol20","exit_time","exit_price","gain_pct",
             "outcome"]].to_string(index=False))
    print(f"Win rate: {100*(d.gain_pct>0).sum()/len(d):.2f}% "
          f"({(d.gain_pct>0).sum()}/{len(d)}) | "
          f"summed gain: {d.gain_pct.sum():+.4f}% | "
          "gross, before costs; overlapping signals treated independently")
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        d.to_csv(args.out,index=False)
        print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
