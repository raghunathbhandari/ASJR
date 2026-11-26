#!/usr/bin/env python3
"""September 2026 ASJR original three-candle six-stock research backtest.

Frozen signal: C2 bullish with lower wick > real body, sweeps and reclaims
C1 low; C3 volume > C2 volume and C3 close > C2 close. Session: NY 9:30–16:00.
Original reference entry C2 close, stop C2 open, R=max(C2 body, 0.1% entry).
Original target-touch results are EX-POST and never count as filled trades.

Causal comparison (NEW hypothetical): enter at first 5m open AFTER C3 CLOSE,
SL=C2 open, step=max(entry-SL, 0.1% entry); if entry <= stop reject.
Fixed targets 1R/2R/3R or step trail: stop tested first in 5m OHLC;
trailing ratchet becomes active only on following 5m bar; exit at last
regular-session 5m close if not stopped/targeted. Same-bar target/stop order
unknown: mark as ambiguous and choose stop conservatively. No transaction
costs, slippage, fractional-cent rounding, order book, or position sizing.
Overlapping trade candidates assessed independently. No portfolio return.
"""
from __future__ import annotations
import argparse
import math
from pathlib import Path

import pandas as pd
from original_three_candle import historical_signals, resample_rth_15m

STOCKS = ("NVDA", "INTC", "TSLA", "PLTR", "AMD", "AAPL")
EXPECTED = {
    "NVDA": (9, 9, 9, 7),
    "INTC": (11, 11, 9, 8),
    "TSLA": (7, 7, 7, 7),
    "PLTR": (11, 11, 11, 10),
    "AMD": (8, 8, 4, 4),
    "AAPL": (8, 7, 6, 4),
}
DATA_DIR = Path(__file__).resolve().parent / "data" / "2026-09"


def read_ibkr_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = ["Datetime_UTC", "Open", "High", "Low", "Close", "Volume"]
    if not set(cols).issubset(df.columns):
        raise ValueError(f"{path}: missing input columns")
    idx = pd.DatetimeIndex(pd.to_datetime(df.Datetime_UTC, utc=True))
    candles = df[cols[1:]].apply(pd.to_numeric, errors="raise")
    candles.index = idx
    candles = candles.sort_index()
    if idx.has_duplicates or candles.isna().any().any():
        raise ValueError(f"{path}: duplicate timestamps or NaN")
    if any((candles.High < candles[["Open","Close","Low"]].max(axis=1)) |
           (candles.Low > candles[["Open","Close","High"]].min(axis=1)) |
           (candles.Volume < 0)):
        raise ValueError(f"{path}: invalid OHLC or volume")
    return candles


def simulate(five: pd.DataFrame, original_stop: float,
             target_r: int | None, step_trailing: bool) -> dict:
    if five.empty:
        return {"reason": "NO_NEXT_5M"}
    entry = float(five.iloc[0].Open)
    if entry <= original_stop:
        return {"reason": "INVALID_ENTRY", "entry": entry}
    step = max(entry - original_stop, entry * 0.001)
    stop = original_stop
    max_r = 0
    ambiguous = 0
    exit_price = None
    for moment, bar in five.iterrows():
        o, hi, lo = float(bar.Open), float(bar.High), float(bar.Low)
        next_target = entry + (target_r or max_r + 1) * step
        if lo <= stop and hi >= next_target:
            ambiguous += 1
        if o <= stop:
            exit_price, reason, exit_at = o, "GAP_STOP", moment
            break
        if lo <= stop:
            exit_price, reason, exit_at = stop, "STOP", moment
            break
        if target_r is not None and hi >= entry + target_r * step:
            exit_price, reason, exit_at = entry + target_r * step, "TARGET", moment
            break
        if step_trailing:
            reached = max(0, math.floor((hi - entry + 1e-8) / step))
            if reached > max_r:
                max_r = reached
                # This updated stop starts on NEXT bar; do not assume same-bar order.
                stop = max(stop, entry + reached * step)
    if exit_price is None:
        exit_at, exit_price, reason = five.index[-1], float(five.iloc[-1].Close), "RTH_CLOSE"
    return {
        "reason": reason, "entry": entry, "initial_stop": original_stop,
        "r_step": step, "exit": exit_price,
        "exit_uk": str(exit_at.tz_convert("Europe/London")),
        "points": exit_price - entry,
        "price_gain_pct": 100.0 * (exit_price - entry) / entry,
        "ambiguous_5m_bars": ambiguous,
    }


def scan_stock(ticker: str, csv: Path) -> tuple[pd.DataFrame, list[dict], dict]:
    raw = read_ibkr_csv(csv)
    candle15 = resample_rth_15m(raw, "2026-09-01", "2026-09-30")
    original = historical_signals(candle15, ticker, 0.10)
    ny = raw.copy()
    ny.index = ny.index.tz_convert("America/New_York")
    ny = ny.between_time("09:30", "15:59")
    details = []
    for _, signal in original.iterrows():
        c3 = pd.Timestamp(signal.c3_start_uk)
        date_ny = c3.tz_convert("America/New_York").date()
        entry_start = (c3 + pd.Timedelta(minutes=15)).tz_convert("America/New_York")
        candidates = ny.loc[(ny.index.date == date_ny) & (ny.index >= entry_start)]
        row = {
            "ticker": ticker, "date_ny": str(date_ny), "c3_start_uk": str(c3),
            "c2_close_reference": float(signal.entry_reference),
            "c2_open_stop": float(signal.initial_stop_reference),
            "original_r_step": float(signal.r_price_step),
        }
        for r in (1, 2, 3):
            row[f"original_{r}R_touch"] = int(signal[f"hit_{r}R"])
            row[f"original_{r}R_nominal_gain_pct"] = float(signal[f"nominal_{r}R_gain_pct"])
        for label, target, trailing in (
                ("fixed_1R", 1, False), ("fixed_2R", 2, False),
                ("fixed_3R", 3, False), ("step_trail", None, True)):
            for key,value in simulate(candidates, row["c2_open_stop"],
                                      target, trailing).items():
                row[f"{label}_{key}"] = value
        details.append(row)
    session_counts = ny.groupby(ny.index.date).size()
    audit = {
        "ticker": ticker, "source_5m": len(raw),
        "rth_dates": len(session_counts),
        "full_78_rth_days": int((session_counts==78).sum()),
        "rth_zero_volume": int((ny.Volume==0).sum()),
        "15m_bars": len(candle15),
        "signals": len(original),
    }
    return original, details, audit


def summarize(trades: pd.DataFrame, audit: list[dict]) -> pd.DataFrame:
    rows = []
    for ticker in (*STOCKS, "TOTAL"):
        d = trades if ticker == "TOTAL" else trades.loc[trades.ticker == ticker]
        row = {"ticker": ticker, "original_setups": len(d)}
        for r in (1, 2, 3):
            hit = int(d[f"original_{r}R_touch"].sum()) if not d.empty else 0
            row[f"{r}R_touches"] = hit
            row[f"{r}R_touch_rate_pct"] = 100*hit/len(d) if len(d) else 0
            row[f"{r}R_illustrative_gain_sum_pct"] = (
                float(d[f"original_{r}R_nominal_gain_pct"].sum()) if not d.empty else 0
            )
        for label in ("fixed_1R", "fixed_2R", "fixed_3R", "step_trail"):
            valid = d.loc[d[f"{label}_points"].notna()] if not d.empty else d
            returns = valid[f"{label}_price_gain_pct"] if len(valid) else pd.Series(dtype=float)
            row[label+"_valid"] = len(valid)
            row[label+"_positive"] = int((returns > 0).sum())
            row[label+"_negative"] = int((returns < 0).sum())
            row[label+"_positive_rate_pct"] = (
                100*row[label+"_positive"]/len(valid) if len(valid) else 0
            )
            row[label+"_sum_price_gain_pct"] = float(returns.sum())
            row[label+"_average_trade_pct"] = float(returns.mean()) if len(valid) else 0
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "results")
    parser.add_argument("--verify-september", action="store_true")
    args = parser.parse_args()
    parts, audits, archived_actual = [], [], {}
    for ticker in STOCKS:
        signals, details, audit = scan_stock(
            ticker, args.data_dir / f"{ticker}_5min_UTC.csv")
        parts.extend(details)
        audits.append(audit)
        archived_actual[ticker] = (
            len(signals), *(int(signals[f"hit_{r}R"].sum()) for r in (1,2,3))
        )
    if args.verify_september and archived_actual != EXPECTED:
        raise SystemExit(f"Archived target counts mismatch: {archived_actual}")
    df = pd.DataFrame(parts)
    report = summarize(df, audits)
    print("\nORIGINAL THREE-CANDLE -- SEPTEMBER SIX STOCKS")
    print("Historical target touches only (look-ahead in C2 reference entry):")
    print(report[["ticker","original_setups","1R_touches","2R_touches","3R_touches"]].to_string(index=False))
    print("\nPost-C3 next-5m-open hypothetical results (before all trading costs):")
    print(report[["ticker","step_trail_valid","step_trail_positive",
                  "step_trail_positive_rate_pct","step_trail_sum_price_gain_pct"]]
          .to_string(index=False, float_format=lambda x:f"{x:.4f}"))
    print(f"\nSource rows: {sum(x['source_5m'] for x in audits)}")
    print("Assumptions: stop-first OHLC, new stop from next bar, RTH close exit.")
    print("Sum of trade price gains is not account or portfolio return.")
    args.out.mkdir(parents=True,exist_ok=True)
    df.to_csv(args.out / "SEPTEMBER_2026_SIX_STOCK_SIGNALS_AND_EXITS.csv",index=False)
    report.to_csv(args.out / "SEPTEMBER_2026_SIX_STOCK_SUMMARY.csv",index=False)
    pd.DataFrame(audits).to_csv(args.out / "SEPTEMBER_2026_SIX_STOCK_DATA_AUDIT.csv",index=False)
    print("Saved results to",args.out)


if __name__ == "__main__":
    main()
