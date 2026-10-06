#!/usr/bin/env python3
"""
Standalone stock London-session breakout comparison.

Runs TWO variants on 5-minute stock data:
1) Normal Breakout
2) Breakout + Retest

Default research rules:
- London local time (DST-safe)
- Opening range: 08:00-08:30
- Breakout: completed 5m close outside opening range
- Entry: next 5m bar open
- Retest: within 6 bars, price touches broken OR level and closes back outside it
- Stop: opening-range midpoint
- Target: 2R
- Signal cutoff: 11:30 London
- Flat all positions: 12:00 London
- Max 1 long + 1 short per session
- Same-bar stop/target: STOP wins (pessimistic)
- Default stock slippage: $0.01 per side
- Default test window: latest 30 calendar days in the CSV

Examples:
  python Backtesting/SessionBreakout/stock_london_breakout_compare.py --ticker INTC
  python Backtesting/SessionBreakout/stock_london_breakout_compare.py --ticker INTC --days 365
  python Backtesting/SessionBreakout/stock_london_breakout_compare.py --ticker INTC --start 2026-09-01 --end 2026-09-30
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

NY_TZ = "America/New_York"
LONDON_TZ = "Europe/London"


@dataclass(frozen=True)
class Config:
    opening_minutes: int = 30
    rr: float = 2.0
    retest: bool = False
    max_wait_retest_bars: int = 6
    max_trades_per_direction: int = 1
    slippage: float = 0.01


def resolve_csv(root: Path, ticker: str) -> Path:
    ticker = ticker.upper()
    candidates = [
        root / "Backtesting/BacktestData/IBKR/MarketData24h/5m" / f"{ticker}_5m.csv",
        root / "Backtesting/BacktestData/IBKR/MarketData/5m" / f"{ticker}_5m.csv",
        root / "Backtesting/BacktestData/MarketData/5m" / f"{ticker}_5m.csv",
    ]
    for p in candidates:
        if p.exists() and p.stat().st_size > 0:
            return p
    raise SystemExit(
        "CSV not found. Checked:\n  " + "\n  ".join(str(p) for p in candidates)
    )


def load_5m(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    if "datetime" in df.columns:
        raw_dt = df["datetime"]
    elif "timestamp_et" in df.columns:
        raw_dt = df["timestamp_et"]
    elif "timestamp" in df.columns:
        raw_dt = df["timestamp"]
    elif {"date", "time"}.issubset(df.columns):
        raw_dt = df["date"].astype(str) + " " + df["time"].astype(str)
    else:
        raw_dt = df.iloc[:, 0]

    dt = pd.to_datetime(raw_dt, errors="coerce")

    if getattr(dt.dt, "tz", None) is None:
        # ASJR IBKR historical files are stored on an ET clock unless timezone-aware.
        dt = dt.dt.tz_localize(NY_TZ, ambiguous="infer", nonexistent="shift_forward")
    else:
        dt = dt.dt.tz_convert(NY_TZ)

    out = pd.DataFrame({"datetime": dt})

    aliases = {
        "open": ["open", "o"],
        "high": ["high", "h"],
        "low": ["low", "l"],
        "close": ["close", "c"],
        "volume": ["volume", "vol", "v"],
    }

    for target, names in aliases.items():
        source = next((n for n in names if n in df.columns), None)
        if source is None:
            if target == "volume":
                out[target] = 0.0
                continue
            raise SystemExit(f"Missing required OHLC column: {target}")
        out[target] = pd.to_numeric(df[source], errors="coerce")

    out = (
        out.dropna(subset=["datetime", "open", "high", "low", "close"])
        .sort_values("datetime")
        .drop_duplicates("datetime")
        .reset_index(drop=True)
    )

    # Normalize to exact 5-minute bars. If source is already 5m, this preserves it.
    x = out.set_index("datetime")
    bars = x.resample("5min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    bars = bars.dropna(subset=["open", "high", "low", "close"]).reset_index()
    return bars


def add_london_clock(bars: pd.DataFrame) -> pd.DataFrame:
    x = bars.copy()
    local = x["datetime"].dt.tz_convert(LONDON_TZ)
    x["session_date"] = local.dt.date
    x["local_minute"] = local.dt.hour * 60 + local.dt.minute
    return x


def slice_period(
    bars: pd.DataFrame,
    days: int | None,
    start: str | None,
    end: str | None,
) -> pd.DataFrame:
    x = bars.copy()

    if start:
        start_ts = pd.Timestamp(start, tz=LONDON_TZ).tz_convert(NY_TZ)
        x = x[x["datetime"] >= start_ts]

    if end:
        # Include whole end date in London time.
        end_ts = (
            pd.Timestamp(end, tz=LONDON_TZ)
            + pd.Timedelta(days=1)
            - pd.Timedelta(microseconds=1)
        ).tz_convert(NY_TZ)
        x = x[x["datetime"] <= end_ts]

    if not start and not end and days:
        if x.empty:
            return x
        last_london = x["datetime"].max().tz_convert(LONDON_TZ)
        first_london = last_london - pd.Timedelta(days=days)
        first_ny = first_london.tz_convert(NY_TZ)
        x = x[x["datetime"] >= first_ny]

    return x.reset_index(drop=True)


def find_retest(
    day: pd.DataFrame,
    signal_pos: int,
    direction: int,
    level: float,
    max_wait: int,
) -> int | None:
    end = min(len(day) - 1, signal_pos + max_wait)
    for j in range(signal_pos + 1, end + 1):
        r = day.iloc[j]
        if direction == 1:
            touched = r["low"] <= level
            reclaimed = r["close"] > level
        else:
            touched = r["high"] >= level
            reclaimed = r["close"] < level

        if touched and reclaimed:
            return j
    return None


def manage_trade(
    day: pd.DataFrame,
    entry_pos: int,
    direction: int,
    entry: float,
    stop: float,
    target: float,
    flat_minute: int,
    slippage: float,
):
    risk = abs(entry - stop)
    if risk <= 0:
        return None

    for j in range(entry_pos, len(day)):
        r = day.iloc[j]

        if direction == 1:
            hit_stop = r["low"] <= stop
            hit_target = r["high"] >= target
        else:
            hit_stop = r["high"] >= stop
            hit_target = r["low"] <= target

        # Conservative assumption if both touched in same candle.
        if hit_stop:
            exit_px = stop - slippage if direction == 1 else stop + slippage
            result_r = direction * (exit_px - entry) / risk
            return result_r, "STOP", r["datetime"], exit_px

        if hit_target:
            exit_px = target
            result_r = direction * (exit_px - entry) / risk
            return result_r, "TARGET", r["datetime"], exit_px

        if int(r["local_minute"]) >= flat_minute:
            exit_px = float(r["close"]) - slippage * direction
            result_r = direction * (exit_px - entry) / risk
            return result_r, "TIME", r["datetime"], exit_px

    r = day.iloc[-1]
    exit_px = float(r["close"]) - slippage * direction
    result_r = direction * (exit_px - entry) / risk
    return result_r, "DATA_END", r["datetime"], exit_px


def run_strategy(bars: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    x = add_london_clock(bars)

    OPEN = 8 * 60
    OR_END = OPEN + cfg.opening_minutes
    SIGNAL_CUTOFF = 11 * 60 + 30
    FLAT = 12 * 60

    trades = []

    for session_date, day0 in x.groupby("session_date", sort=True):
        day = day0.reset_index(drop=True)

        orb = day[
            (day["local_minute"] >= OPEN)
            & (day["local_minute"] < OR_END)
        ]

        expected = cfg.opening_minutes // 5
        if len(orb) < expected:
            continue

        or_high = float(orb["high"].max())
        or_low = float(orb["low"].min())
        if not np.isfinite(or_high) or not np.isfinite(or_low) or or_high <= or_low:
            continue

        range_mid = (or_high + or_low) / 2.0

        candidates = day.index[
            (day["local_minute"] >= OR_END)
            & (day["local_minute"] <= SIGNAL_CUTOFF)
        ].tolist()

        long_count = 0
        short_count = 0
        k = 0

        while k < len(candidates):
            i = candidates[k]
            r = day.iloc[i]
            direction = 0

            if long_count < cfg.max_trades_per_direction and r["close"] > or_high:
                direction = 1
            elif short_count < cfg.max_trades_per_direction and r["close"] < or_low:
                direction = -1

            if direction == 0:
                k += 1
                continue

            confirm_pos = i

            if cfg.retest:
                level = or_high if direction == 1 else or_low
                retest_pos = find_retest(
                    day, i, direction, level, cfg.max_wait_retest_bars
                )
                if retest_pos is None:
                    # One first-break attempt per direction; don't trigger repeatedly
                    # on every candle already outside the range.
                    if direction == 1:
                        long_count = cfg.max_trades_per_direction
                    else:
                        short_count = cfg.max_trades_per_direction
                    k += 1
                    continue
                confirm_pos = retest_pos

            entry_pos = confirm_pos + 1
            if entry_pos >= len(day):
                break

            entry_bar = day.iloc[entry_pos]
            if int(entry_bar["local_minute"]) > SIGNAL_CUTOFF:
                break

            raw_entry = float(entry_bar["open"])
            entry = raw_entry + cfg.slippage * direction
            stop = range_mid

            if direction == 1 and stop >= entry:
                k += 1
                continue
            if direction == -1 and stop <= entry:
                k += 1
                continue

            risk = abs(entry - stop)
            target = entry + direction * cfg.rr * risk

            managed = manage_trade(
                day,
                entry_pos,
                direction,
                entry,
                stop,
                target,
                FLAT,
                cfg.slippage,
            )
            if managed is None:
                k += 1
                continue

            result_r, reason, exit_time, exit_px = managed

            trades.append(
                {
                    "session_date": session_date,
                    "direction": "LONG" if direction == 1 else "SHORT",
                    "signal_time": day.iloc[confirm_pos]["datetime"],
                    "entry_time": entry_bar["datetime"],
                    "exit_time": exit_time,
                    "or_high": or_high,
                    "or_low": or_low,
                    "entry": entry,
                    "stop": stop,
                    "target": target,
                    "exit": exit_px,
                    "result_r": result_r,
                    "exit_reason": reason,
                }
            )

            if direction == 1:
                long_count += 1
            else:
                short_count += 1

            # Continue scanning only after current position has closed.
            exit_idx = day.index[day["datetime"] >= exit_time].tolist()
            if exit_idx:
                last_i = exit_idx[0]
                while k < len(candidates) and candidates[k] <= last_i:
                    k += 1
            else:
                break

    return pd.DataFrame(trades)


def summarize(name: str, trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "strategy": name,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_r": 0.0,
            "avg_r": 0.0,
            "max_dd_r": 0.0,
        }

    r = trades["result_r"].astype(float)
    wins = int((r > 0).sum())
    losses = int((r <= 0).sum())
    eq = r.cumsum()
    dd = eq - eq.cummax()

    return {
        "strategy": name,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(trades) * 100.0,
        "total_r": float(r.sum()),
        "avg_r": float(r.mean()),
        "max_dd_r": float(dd.min()),
    }


def print_summary(rows: list[dict]) -> None:
    print("\n" + "=" * 103)
    print("LONDON BREAKOUT COMPARISON")
    print("=" * 103)
    print(
        f"{'Strategy':<24}"
        f"{'Trades':>9}"
        f"{'Wins':>8}"
        f"{'Losses':>9}"
        f"{'Win Rate':>12}"
        f"{'P/L':>12}"
        f"{'Avg/Trade':>14}"
        f"{'Max DD':>12}"
    )
    print("-" * 103)
    for s in rows:
        print(
            f"{s['strategy']:<24}"
            f"{s['trades']:>9}"
            f"{s['wins']:>8}"
            f"{s['losses']:>9}"
            f"{s['win_rate']:>11.1f}%"
            f"{s['total_r']:>11.2f}R"
            f"{s['avg_r']:>13.3f}R"
            f"{s['max_dd_r']:>11.2f}R"
        )
    print("=" * 103)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="INTC")
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--rr", type=float, default=2.0)
    ap.add_argument("--slippage", type=float, default=0.01)
    ap.add_argument("--show-trades", action="store_true")
    args = ap.parse_args()

    ticker = args.ticker.upper()
    path = resolve_csv(args.root, ticker)

    print(f"Ticker : {ticker}")
    print(f"CSV    : {path}")

    bars_all = load_5m(path)
    bars = slice_period(bars_all, args.days, args.start, args.end)

    if bars.empty:
        raise SystemExit("No bars remain after date filtering.")

    london_start = bars["datetime"].min().tz_convert(LONDON_TZ)
    london_end = bars["datetime"].max().tz_convert(LONDON_TZ)

    print(f"Rows   : {len(bars):,}")
    print(f"Period : {london_start} -> {london_end}")
    print(
        f"Rules  : London 08:00 OR | 30m range | 2R={args.rr:g} | "
        f"midpoint stop | slippage=${args.slippage:.2f}"
    )

    normal_cfg = Config(
        rr=args.rr,
        retest=False,
        slippage=args.slippage,
    )
    retest_cfg = Config(
        rr=args.rr,
        retest=True,
        slippage=args.slippage,
    )

    normal = run_strategy(bars, normal_cfg)
    retest = run_strategy(bars, retest_cfg)

    summaries = [
        summarize("Normal Breakout", normal),
        summarize("Breakout + Retest", retest),
    ]

    print_summary(summaries)

    if args.show_trades:
        for name, trades in [
            ("NORMAL BREAKOUT", normal),
            ("BREAKOUT + RETEST", retest),
        ]:
            print("\n" + name)
            print("-" * 120)
            if trades.empty:
                print("No trades.")
            else:
                z = trades.copy()
                for c in ["signal_time", "entry_time", "exit_time"]:
                    z[c] = z[c].dt.tz_convert(LONDON_TZ)
                cols = [
                    "session_date",
                    "direction",
                    "signal_time",
                    "entry_time",
                    "exit_time",
                    "entry",
                    "stop",
                    "target",
                    "exit",
                    "result_r",
                    "exit_reason",
                ]
                print(z[cols].to_string(index=False))

    winner = max(summaries, key=lambda x: x["total_r"])
    print(
        f"\nBest by total R: {winner['strategy']} | "
        f"{winner['trades']} trades | {winner['win_rate']:.1f}% win | "
        f"{winner['total_r']:.2f}R"
    )


if __name__ == "__main__":
    main()
