#!/usr/bin/env python3
"""ASJR original three-candle equity strategy v1.1 (historical research).

Reproduces the *pattern definition* from 25 Oct 2026, not the later variants.
Input: archived 5-minute UTC OHLCV CSV files, one per ticker.
Output: retrospective same-session 1R/2R/3R target touches, NOT executable P&L.

Original C2-close entry hypothesis has look-ahead: its C3 volume/close filter
becomes known only after C3 finishes. Historical target touches do not establish
entry fills, stop-before-target sequence, realized wins or actual gain.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

TICKERS = ("AMAT", "GOOG", "INTC", "LRCX", "META", "MU",
           "NVDA", "PLTR", "SPY", "XOM")
OHLCV = ("Open", "High", "Low", "Close", "Volume")
ARCHIVED_SEPTEMBER = {
    "AMAT": (5, 5, 4, 3), "GOOG": (8, 8, 7, 3),
    "INTC": (11, 11, 9, 8), "LRCX": (10, 10, 10, 10),
    "META": (12, 12, 12, 12), "MU": (7, 7, 7, 7),
    "NVDA": (9, 9, 9, 7), "PLTR": (11, 11, 11, 10),
    "SPY": (4, 4, 0, 0), "XOM": (6, 6, 6, 4),
}


def load_five_minute_csv(path: Path) -> pd.DataFrame:
    """Archived IBKR or Yahoo CSV; timestamps are UTC (timezone-aware preferred)."""
    source = pd.read_csv(path)
    time_col = next((c for c in ("Datetime", "datetime_source")
                     if c in source.columns), None)
    if time_col is None:
        raise ValueError(f"{path}: expected Datetime or datetime_source column")
    renamed = {c: c.title() for c in source.columns
               if c.lower() in {v.lower() for v in OHLCV}}
    source = source.rename(columns=renamed)
    missing = set(OHLCV) - set(source.columns)
    if missing:
        raise ValueError(f"{path}: missing OHLCV columns {sorted(missing)}")
    timestamps = pd.to_datetime(source[time_col], utc=True, errors="raise")
    bars = source.loc[:, OHLCV].apply(pd.to_numeric, errors="coerce")
    bars.index = pd.DatetimeIndex(timestamps)
    bars = bars.dropna(subset=OHLCV).sort_index()
    if bars.index.has_duplicates:
        raise ValueError(f"{path}: duplicate 5-minute timestamps, audit input")
    return bars


def resample_rth_15m(five_min: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Anchor 15m groups at 09:30 America/New_York, never bridge RTH gaps."""
    if five_min.index.tz is None:
        raise ValueError("Input must use timezone-aware timestamps")
    if start > end:
        raise ValueError("start must be on/before end")
    ny = five_min.loc[:, OHLCV].copy().sort_index()
    ny.index = ny.index.tz_convert("America/New_York")
    ny = ny.loc[(pd.Index(ny.index.date.astype(str)) >= start) &
                (pd.Index(ny.index.date.astype(str)) <= end)]
    ny = ny.between_time("09:30", "15:59")
    groups = []
    for trading_day, day in ny.groupby(ny.index.date):
        offsets = day.index.hour * 60 + day.index.minute - 570
        valid = (offsets >= 0) & (offsets < 390) & (offsets % 5 == 0)
        day = day.loc[valid]
        offsets = offsets[valid]
        if day.empty:
            continue
        buckets = offsets // 15
        aggregate = day.groupby(buckets).agg(
            {"Open": "first", "High": "max", "Low": "min",
             "Close": "last", "Volume": "sum"})
        counts = day.groupby(buckets).size()
        # Three distinct, correctly timestamped 5m bars required.
        full = counts[counts == 3].index
        aggregate = aggregate.loc[full]
        session_start = pd.Timestamp(trading_day, tz="America/New_York")
        session_start += pd.Timedelta(hours=9, minutes=30)
        aggregate.index = pd.DatetimeIndex(
            [session_start + pd.Timedelta(minutes=15 * int(b))
             for b in aggregate.index])
        groups.append(aggregate)
    if not groups:
        return pd.DataFrame(columns=OHLCV, index=pd.DatetimeIndex([], tz="Europe/London"))
    result = pd.concat(groups).sort_index()
    result.index = result.index.tz_convert("Europe/London")
    return result


def is_original_pattern(c1: pd.Series, c2: pd.Series, c3: pd.Series) -> bool:
    """Frozen 25 October rules; bullish C2, lower wick sweep/reclaim, C3 confirm."""
    body = float(c2.Close - c2.Open)
    wick = float(c2.Open - c2.Low)
    return (body > 0 and wick > body
            and c2.Low < c1.Low and c2.Close > c1.Low
            and c2.Volume > 0 and c3.Volume > c2.Volume
            and c3.Close > c2.Close)


def historical_signals(bars: pd.DataFrame, ticker: str, r_floor_pct: float = 0.10) -> pd.DataFrame:
    """Compute max favourable same-session prices from C3, IGNORING initial stops."""
    if r_floor_pct <= 0:
        raise ValueError("r_floor_pct must be positive")
    rows = []
    ny_dates = bars.index.tz_convert("America/New_York").date
    for trading_day, day in bars.groupby(ny_dates):
        for i in range(2, len(day)):
            if (day.index[i] - day.index[i-1] != pd.Timedelta(minutes=15)
                    or day.index[i-1] - day.index[i-2] != pd.Timedelta(minutes=15)):
                continue
            c1, c2, c3 = day.iloc[i-2], day.iloc[i-1], day.iloc[i]
            if not is_original_pattern(c1, c2, c3):
                continue
            entry = float(c2.Close)
            stop = float(c2.Open)
            step = max(entry-stop, entry * r_floor_pct / 100.0)
            future_peak = float(day.iloc[i:].High.max())
            hits = [future_peak >= entry + k * step for k in (1, 2, 3)]
            rows.append({
                "ticker": ticker,
                "trading_day_ny": str(trading_day),
                "c1_start_uk": str(day.index[i-2]),
                "c2_start_uk": str(day.index[i-1]),
                "c3_start_uk": str(day.index[i]),
                "entry_reference": entry, "initial_stop_reference": stop,
                "r_price_step": step, "c2_volume": float(c2.Volume),
                "c3_volume": float(c3.Volume), "future_peak": future_peak,
                **{f"hit_{k}R": int(hits[k-1]) for k in (1, 2, 3)},
                **{f"nominal_{k}R_gain_pct": (100*k*step/entry if hits[k-1] else 0.0)
                   for k in (1, 2, 3)},
            })
    return pd.DataFrame(rows)


def summarize(all_signals: pd.DataFrame) -> pd.DataFrame:
    """Target touch rate is an ex-post proxy; never report executed win %."""
    rows = []
    for ticker, part in all_signals.groupby("ticker", sort=True):
        n = len(part)
        row = {"ticker": ticker, "setups": n}
        for k in (1, 2, 3):
            hit = int(part[f"hit_{k}R"].sum())
            row[f"{k}R_touches"] = hit
            row[f"{k}R_touch_rate_pct"] = (100*hit/n if n else 0.0)
            row[f"{k}R_nominal_gross_pct_sum"] = part[f"nominal_{k}R_gain_pct"].sum()
        rows.append(row)
    result = pd.DataFrame(rows)
    if not result.empty:
        total = {"ticker": "TOTAL", "setups": int(result.setups.sum())}
        for k in (1, 2, 3):
            hit = int(result[f"{k}R_touches"].sum())
            total[f"{k}R_touches"] = hit
            total[f"{k}R_touch_rate_pct"] = 100*hit/total["setups"]
            total[f"{k}R_nominal_gross_pct_sum"] = result[f"{k}R_nominal_gross_pct_sum"].sum()
        result = pd.concat([result, pd.DataFrame([total])], ignore_index=True)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, required=True,
                   help="Directory holding TICKER_5m.csv archived files")
    p.add_argument("--tickers", nargs="+", default=list(TICKERS))
    p.add_argument("--start", default="2026-09-01")
    p.add_argument("--end", default="2026-09-30")
    p.add_argument("--r-floor-pct", type=float, default=0.10)
    p.add_argument("--save-dir", type=Path, help="Optional outputs: signals.csv and summary.csv")
    p.add_argument("--check-archived-september", action="store_true",
                   help="Require exact archived counts for all original 10 tickers")
    args = p.parse_args()
    if args.start > args.end:
        p.error("--start must precede --end")
    if args.check_archived_september and (
            args.start != "2026-09-01" or args.end != "2026-09-30"
            or set(args.tickers) != set(TICKERS)
            or args.r_floor_pct != 0.10):
        p.error("Archived regression requires Sep 2026, all ten tickers and 0.10% R")
    signals = []
    found = {}
    for ticker in args.tickers:
        path = args.data_dir / f"{ticker}_5m.csv"
        if not path.is_file():
            p.error(f"Missing archived CSV: {path}")
        bars = resample_rth_15m(load_five_minute_csv(path), args.start, args.end)
        found[ticker] = historical_signals(bars, ticker, args.r_floor_pct)
        if not found[ticker].empty:
            signals.append(found[ticker])
    if not signals:
        print("No original strategy setups found.")
        return
    full = pd.concat(signals, ignore_index=True)
    summary = summarize(full)
    print("\nASJR ORIGINAL THREE-CANDLE — EX-POST PRICE TOUCHES, NOT EXECUTED TRADES")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    if args.check_archived_september:
        actual = {t: (len(found[t]), *(int(found[t][f"hit_{k}R"].sum())
                      if not found[t].empty else 0 for k in (1,2,3)))
                  for t in TICKERS}
        if actual != ARCHIVED_SEPTEMBER:
            raise SystemExit(f"ARCHIVED SEPTEMBER REGRESSION FAILED:\n{actual}\n"
                             f"Expected:\n{ARCHIVED_SEPTEMBER}")
        print("ARCHIVED SEPTEMBER SETUP/TOUCH COUNTS: MATCH")
    if args.save_dir:
        args.save_dir.mkdir(parents=True, exist_ok=True)
        full.to_csv(args.save_dir / "signals.csv", index=False)
        summary.to_csv(args.save_dir / "summary.csv", index=False)
        print(f"Saved {args.save_dir / 'signals.csv'} and summary.csv")
    print("WARNING: C2-entry + later C3 filter is retrospective. "
          "No chronological fills, net gain %, realized wins or drawdown.")


if __name__ == "__main__":
    main()
