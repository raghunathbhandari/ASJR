#!/usr/bin/env python3
"""
NQ 5-minute Session Breakout research backtest.

Raw data is intentionally NOT stored in Git:
  Backtesting/BacktestData/External/NQ/Dataset_NQ_1min_2022_2025.csv

Research principles
-------------------
* Source timestamps are treated as America/New_York.
* Raw 1m bars are resampled to 5m OHLCV.
* London session clock is calculated in Europe/London (DST-safe).
* Breakout is confirmed only by a completed 5m close outside the opening range.
* Entry is next-bar open (no same-bar look-ahead).
* If stop and target are both touched in the same bar, STOP wins (pessimistic).
* Positions are flattened at the session cutoff; no overnight positions.
* Parameter search is ranked for multi-year robustness, not just total return.

This is research code, not live execution code.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

NY_TZ = "America/New_York"
LONDON_TZ = "Europe/London"

DEFAULT_DATA = Path(
    "Backtesting/BacktestData/External/NQ/Dataset_NQ_1min_2022_2025.csv"
)
DEFAULT_OUT = Path("Backtesting/SessionBreakout/results")


@dataclass(frozen=True)
class Config:
    session: str = "NY"
    opening_minutes: int = 30
    rr: float = 2.0
    stop_mode: str = "range_mid"  # range_mid | breakout_bar | atr
    body_min: float = 0.0          # breakout candle body / full range
    expansion_mult: float = 0.0    # candle range / prior 20-bar median range
    require_ema_align: bool = False
    retest: bool = False
    max_trades_per_direction: int = 1
    slippage_points: float = 0.25


def load_1m(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    if "datetime" in df.columns:
        dt = pd.to_datetime(df["datetime"], errors="coerce")
    elif {"date", "time"}.issubset(df.columns):
        dt = pd.to_datetime(
            df["date"].astype(str) + " " + df["time"].astype(str), errors="coerce"
        )
    elif "timestamp_et" in df.columns:
        dt = pd.to_datetime(df["timestamp_et"], errors="coerce")
    elif "timestamp" in df.columns:
        dt = pd.to_datetime(df["timestamp"], errors="coerce")
    else:
        dt = pd.to_datetime(df.iloc[:, 0], errors="coerce")

    # Standardize source to NY-aware timestamps.
    if getattr(dt.dt, "tz", None) is None:
        dt = dt.dt.tz_localize(NY_TZ, ambiguous="infer", nonexistent="shift_forward")
    else:
        dt = dt.dt.tz_convert(NY_TZ)

    out = pd.DataFrame({"datetime": dt})
    for c in ["open", "high", "low", "close", "volume"]:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")
        out[c] = pd.to_numeric(df[c], errors="coerce")

    out = (
        out.dropna(subset=["datetime", "open", "high", "low", "close"])
        .sort_values("datetime")
        .drop_duplicates("datetime")
        .reset_index(drop=True)
    )
    out["volume"] = out["volume"].fillna(0.0)
    return out


def resample_5m(df: pd.DataFrame) -> pd.DataFrame:
    x = df.set_index("datetime")
    bars = x.resample("5min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    bars = bars.dropna(subset=["open", "high", "low", "close"]).reset_index()

    bars["range"] = bars["high"] - bars["low"]
    bars["body_frac"] = (
        (bars["close"] - bars["open"]).abs()
        / bars["range"].replace(0, np.nan)
    ).fillna(0.0)
    bars["median_range20"] = bars["range"].shift(1).rolling(20).median()
    bars["ema20"] = bars["close"].ewm(span=20, adjust=False).mean()

    prev_close = bars["close"].shift(1)
    tr = pd.concat(
        [
            bars["high"] - bars["low"],
            (bars["high"] - prev_close).abs(),
            (bars["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    bars["atr14"] = tr.rolling(14).mean()
    return bars


def add_session_columns(bars: pd.DataFrame, session: str) -> pd.DataFrame:
    x = bars.copy()
    if session == "NY":
        local = x["datetime"].dt.tz_convert(NY_TZ)
        x["session_date"] = local.dt.date
        x["local_minute"] = local.dt.hour * 60 + local.dt.minute
        # 09:30 cash open; evaluate breakouts until 15:30 and flatten by 15:55.
        x["session_open_min"] = 9 * 60 + 30
        x["signal_cutoff_min"] = 15 * 60 + 30
        x["flat_min"] = 15 * 60 + 55
    elif session == "LONDON":
        local = x["datetime"].dt.tz_convert(LONDON_TZ)
        x["session_date"] = local.dt.date
        x["local_minute"] = local.dt.hour * 60 + local.dt.minute
        # 08:00 London open; research window through 12:00 local.
        x["session_open_min"] = 8 * 60
        x["signal_cutoff_min"] = 11 * 60 + 30
        x["flat_min"] = 12 * 60
    else:
        raise ValueError(f"Unknown session: {session}")
    return x


def stop_price(
    direction: int,
    entry: float,
    signal: pd.Series,
    or_high: float,
    or_low: float,
    cfg: Config,
) -> float | None:
    mid = (or_high + or_low) / 2.0

    if cfg.stop_mode == "range_mid":
        stop = mid
    elif cfg.stop_mode == "breakout_bar":
        stop = float(signal["low"] if direction == 1 else signal["high"])
    elif cfg.stop_mode == "atr":
        atr = float(signal["atr14"])
        if not np.isfinite(atr) or atr <= 0:
            return None
        stop = entry - atr if direction == 1 else entry + atr
    else:
        raise ValueError(cfg.stop_mode)

    if direction == 1 and stop >= entry:
        return None
    if direction == -1 and stop <= entry:
        return None
    return float(stop)


def candidate_ok(
    row: pd.Series,
    direction: int,
    or_high: float,
    or_low: float,
    cfg: Config,
) -> bool:
    if direction == 1:
        if not row["close"] > or_high:
            return False
        if cfg.require_ema_align and not row["close"] > row["ema20"]:
            return False
    else:
        if not row["close"] < or_low:
            return False
        if cfg.require_ema_align and not row["close"] < row["ema20"]:
            return False

    if row["body_frac"] < cfg.body_min:
        return False

    if cfg.expansion_mult > 0:
        med = row["median_range20"]
        if not np.isfinite(med) or med <= 0 or row["range"] < cfg.expansion_mult * med:
            return False

    return True


def find_retest_entry(
    day: pd.DataFrame,
    signal_pos: int,
    direction: int,
    level: float,
    max_wait_bars: int = 6,
) -> int | None:
    """Return the confirmation bar position; actual fill is the following bar open."""
    end = min(len(day) - 1, signal_pos + max_wait_bars)
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
    flat_min: int,
    slippage_points: float,
) -> tuple[float, str, pd.Timestamp, float]:
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("Non-positive risk")

    for j in range(entry_pos, len(day)):
        r = day.iloc[j]

        if direction == 1:
            hit_stop = r["low"] <= stop
            hit_target = r["high"] >= target
        else:
            hit_stop = r["high"] >= stop
            hit_target = r["low"] <= target

        # Pessimistic same-bar ordering.
        if hit_stop:
            exit_px = stop - slippage_points if direction == 1 else stop + slippage_points
            r_mult = direction * (exit_px - entry) / risk
            return r_mult, "STOP", r["datetime"], exit_px
        if hit_target:
            # No favorable slippage credited.
            exit_px = target
            r_mult = direction * (exit_px - entry) / risk
            return r_mult, "TARGET", r["datetime"], exit_px

        if int(r["local_minute"]) >= int(flat_min):
            exit_px = float(r["close"])
            exit_px -= slippage_points * direction
            r_mult = direction * (exit_px - entry) / risk
            return r_mult, "TIME", r["datetime"], exit_px

    r = day.iloc[-1]
    exit_px = float(r["close"]) - slippage_points * direction
    return direction * (exit_px - entry) / risk, "DATA_END", r["datetime"], exit_px


def run_config(bars: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    x = add_session_columns(bars, cfg.session)
    trades: list[dict] = []

    for session_date, day0 in x.groupby("session_date", sort=True):
        day = day0.reset_index(drop=True)
        open_min = int(day["session_open_min"].iloc[0])
        or_end = open_min + cfg.opening_minutes
        cutoff = int(day["signal_cutoff_min"].iloc[0])
        flat_min = int(day["flat_min"].iloc[0])

        orb = day[
            (day["local_minute"] >= open_min)
            & (day["local_minute"] < or_end)
        ]
        # Require the expected number of 5m bars so partial/gappy days are skipped.
        if len(orb) < cfg.opening_minutes // 5:
            continue

        or_high = float(orb["high"].max())
        or_low = float(orb["low"].min())
        if not np.isfinite(or_high) or not np.isfinite(or_low) or or_high <= or_low:
            continue

        long_count = 0
        short_count = 0
        start_candidates = day.index[
            (day["local_minute"] >= or_end)
            & (day["local_minute"] <= cutoff)
        ].tolist()

        k = 0
        while k < len(start_candidates):
            i = start_candidates[k]
            signal = day.iloc[i]
            direction = 0

            if long_count < cfg.max_trades_per_direction and candidate_ok(
                signal, 1, or_high, or_low, cfg
            ):
                direction = 1
            elif short_count < cfg.max_trades_per_direction and candidate_ok(
                signal, -1, or_high, or_low, cfg
            ):
                direction = -1

            if direction == 0:
                k += 1
                continue

            confirm_pos = i
            if cfg.retest:
                level = or_high if direction == 1 else or_low
                retest_pos = find_retest_entry(day, i, direction, level)
                if retest_pos is None:
                    # Do not repeatedly trigger from every outside candle.
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
            if int(entry_bar["local_minute"]) > cutoff:
                break

            # Adverse entry slippage.
            raw_entry = float(entry_bar["open"])
            entry = raw_entry + cfg.slippage_points * direction

            stop = stop_price(direction, entry, day.iloc[confirm_pos], or_high, or_low, cfg)
            if stop is None:
                k += 1
                continue

            risk = abs(entry - stop)
            target = entry + direction * cfg.rr * risk

            result_r, reason, exit_time, exit_px = manage_trade(
                day,
                entry_pos,
                direction,
                entry,
                stop,
                target,
                flat_min,
                cfg.slippage_points,
            )

            trades.append(
                {
                    **asdict(cfg),
                    "session_date": session_date,
                    "year": int(pd.Timestamp(session_date).year),
                    "direction": "LONG" if direction == 1 else "SHORT",
                    "signal_time": day.iloc[confirm_pos]["datetime"],
                    "entry_time": entry_bar["datetime"],
                    "exit_time": exit_time,
                    "or_high": or_high,
                    "or_low": or_low,
                    "or_width": or_high - or_low,
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

            # Only one active position at a time: continue scanning after exit.
            exit_matches = day.index[day["datetime"] >= exit_time].tolist()
            if exit_matches:
                last_i = exit_matches[0]
                while k < len(start_candidates) and start_candidates[k] <= last_i:
                    k += 1
            else:
                break

    return pd.DataFrame(trades)


def max_drawdown_r(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    eq = series.cumsum()
    dd = eq - eq.cummax()
    return float(dd.min())


def summarize(trades: pd.DataFrame, cfg: Config) -> dict:
    if trades.empty:
        return {
            **asdict(cfg),
            "trades": 0,
            "win_rate": 0.0,
            "total_r": 0.0,
            "expectancy_r": 0.0,
            "profit_factor": 0.0,
            "max_dd_r": 0.0,
            "positive_years": 0,
            "years": 0,
            "worst_year_r": 0.0,
            "robust_score": -999.0,
        }

    r = trades["result_r"]
    wins = r[r > 0].sum()
    losses = -r[r < 0].sum()
    pf = float(wins / losses) if losses > 0 else np.inf
    yearly = trades.groupby("year")["result_r"].sum()
    pos_years = int((yearly > 0).sum())
    years = int(len(yearly))
    worst_year = float(yearly.min())

    # Robustness score intentionally penalizes negative years and drawdown.
    expectancy = float(r.mean())
    dd = abs(max_drawdown_r(r))
    consistency = pos_years / years if years else 0.0
    robust_score = expectancy * 100 + min(pf, 3.0) * 5 + consistency * 20 - dd * 0.35
    if worst_year < 0:
        robust_score += worst_year * 0.5

    return {
        **asdict(cfg),
        "trades": int(len(trades)),
        "win_rate": float((r > 0).mean()),
        "total_r": float(r.sum()),
        "expectancy_r": expectancy,
        "profit_factor": pf,
        "max_dd_r": max_drawdown_r(r),
        "positive_years": pos_years,
        "years": years,
        "worst_year_r": worst_year,
        "robust_score": float(robust_score),
    }


def baseline_configs() -> list[Config]:
    return [
        Config(session="NY", opening_minutes=30, rr=2.0, stop_mode="range_mid"),
        Config(session="LONDON", opening_minutes=30, rr=2.0, stop_mode="range_mid"),
    ]


def search_configs() -> Iterable[Config]:
    # Stage 1: broad but deliberately small grid.
    for session in ["NY", "LONDON"]:
        for opening_minutes in [15, 30, 60]:
            for rr in [1.5, 2.0, 2.5, 3.0]:
                for stop_mode in ["range_mid", "breakout_bar", "atr"]:
                    for body_min in [0.0, 0.50]:
                        for expansion_mult in [0.0, 1.20]:
                            yield Config(
                                session=session,
                                opening_minutes=opening_minutes,
                                rr=rr,
                                stop_mode=stop_mode,
                                body_min=body_min,
                                expansion_mult=expansion_mult,
                                require_ema_align=False,
                                retest=False,
                            )

    # Stage 2: retest and EMA confirmation around the core 30m / 2R idea.
    for session in ["NY", "LONDON"]:
        for retest in [True, False]:
            for ema in [True, False]:
                for stop_mode in ["range_mid", "breakout_bar", "atr"]:
                    yield Config(
                        session=session,
                        opening_minutes=30,
                        rr=2.0,
                        stop_mode=stop_mode,
                        body_min=0.50,
                        expansion_mult=1.20,
                        require_ema_align=ema,
                        retest=retest,
                    )


def yearly_table(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    return (
        trades.groupby("year")["result_r"]
        .agg(["count", "sum", "mean"])
        .rename(columns={"count": "trades", "sum": "total_r", "mean": "expectancy_r"})
        .reset_index()
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--mode", choices=["baseline", "search"], default="search")
    args = ap.parse_args()

    if not args.data.exists():
        raise SystemExit(
            f"NQ dataset not found:\n  {args.data}\n\n"
            "Keep the large CSV local-only at that path; it is gitignored."
        )

    args.out.mkdir(parents=True, exist_ok=True)

    print(f"Loading: {args.data}")
    raw = load_1m(args.data)
    bars = resample_5m(raw)
    print(
        f"1m rows={len(raw):,} | 5m rows={len(bars):,} | "
        f"{bars['datetime'].min()} -> {bars['datetime'].max()}"
    )

    configs = baseline_configs() if args.mode == "baseline" else list(search_configs())
    summaries: list[dict] = []
    all_best_trades: dict[int, pd.DataFrame] = {}

    for n, cfg in enumerate(configs, start=1):
        trades = run_config(bars, cfg)
        s = summarize(trades, cfg)
        summaries.append(s)
        all_best_trades[n] = trades
        if n % 25 == 0 or n == len(configs):
            print(f"tested {n}/{len(configs)} configs")

    results = pd.DataFrame(summaries)
    # Require enough observations and prefer configs that are not dependent on one year.
    qualified = results[
        (results["trades"] >= 100)
        & (results["profit_factor"] > 1.0)
        & (results["expectancy_r"] > 0)
    ].copy()

    ranking = qualified.sort_values(
        ["positive_years", "robust_score", "profit_factor", "expectancy_r"],
        ascending=[False, False, False, False],
    )
    results.to_csv(args.out / "all_configs.csv", index=False)
    ranking.to_csv(args.out / "ranked_configs.csv", index=False)

    print("\nTOP ROBUST CONFIGS")
    if ranking.empty:
        print("No configuration passed minimum robustness gates.")
        return

    cols = [
        "session", "opening_minutes", "rr", "stop_mode", "body_min",
        "expansion_mult", "require_ema_align", "retest", "trades",
        "win_rate", "total_r", "expectancy_r", "profit_factor",
        "max_dd_r", "positive_years", "years", "worst_year_r", "robust_score",
    ]
    print(ranking[cols].head(20).to_string(index=False))

    # Re-run exact top config and save trade/year diagnostics.
    best = ranking.iloc[0]
    cfg = Config(
        session=str(best["session"]),
        opening_minutes=int(best["opening_minutes"]),
        rr=float(best["rr"]),
        stop_mode=str(best["stop_mode"]),
        body_min=float(best["body_min"]),
        expansion_mult=float(best["expansion_mult"]),
        require_ema_align=bool(best["require_ema_align"]),
        retest=bool(best["retest"]),
        max_trades_per_direction=int(best["max_trades_per_direction"]),
        slippage_points=float(best["slippage_points"]),
    )
    best_trades = run_config(bars, cfg)
    best_trades.to_csv(args.out / "best_trades.csv", index=False)
    yearly_table(best_trades).to_csv(args.out / "best_yearly.csv", index=False)

    print("\nBEST CONFIG")
    print(cfg)
    print("\nYEARLY")
    print(yearly_table(best_trades).to_string(index=False))
    print(f"\nResults written to: {args.out}")


if __name__ == "__main__":
    main()
