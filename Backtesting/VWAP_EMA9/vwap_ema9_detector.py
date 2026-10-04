"""Print MU 5-minute VWAP/EMA9 setup candidates and simple 1:3 outcomes.

Initial research detector, kept separate from live ASJR alerts.

Rules (all signals are evaluated at candle close):
* Buy candidates only; below VWAP is no trade and shorts are not generated.
* Candidate: RTH green candle closes above RTH VWAP and EMA9 after the previous
  candle closed at/below VWAP; EMA9 is rising; volume is at least the configured
  multiple of the median volume for that same 5-minute time slot in up to the
  previous 20 sessions (at least 10 prior observations are required).
  The signal candle's low must be above EMA9: any EMA9 touch is rejected.
* Entry: next-bar break of the signal candle high (long) / low (short), with a
  one-cent trigger buffer. Stop is beyond the signal candle low/high. Target is
  3R. If stop and target both trade in the same 5-minute bar, count the stop
  first (conservative OHLC assumption).
* A flat EMA9 or weak volume rejects the setup. The latest two months are
  measured back from the newest timestamp in the CSV, not today's system date.
  Filled intraday trades are closed by the RTH close if neither the stop, target,
  nor EMA9 exit has occurred by then.

The defaults are research starting points, not a claim of profitability. Use
--help to adjust the filters and CSV path.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_DATA = (
    Path(__file__).resolve().parents[1]
    / "BacktestData"
    / "IBKR"
    / "MarketData"
    / "5m"
    / "MU_5m.csv"
)


def _read_bars(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # IBKR canonical schema: Datetime,Open,High,Low,Close,Volume.
    by_lower = {str(c).strip().lower(): c for c in df.columns}
    dt_col = by_lower.get("datetime") or by_lower.get("date") or by_lower.get("timestamp")
    if dt_col is None:
        raise ValueError(f"No Datetime/Date/Timestamp column in {path}")
    required = {k: by_lower.get(k.lower()) for k in ("Open", "High", "Low", "Close", "Volume")}
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise ValueError(f"Missing OHLCV columns {missing}; found {list(df.columns)}")

    out = df[[dt_col, *required.values()]].copy()
    out.columns = ["Datetime", "Open", "High", "Low", "Close", "Volume"]
    # IBKR files are UTC. Naive timestamps are interpreted as UTC.
    dt = pd.to_datetime(out["Datetime"], utc=True, errors="coerce")
    out = out.loc[dt.notna()].copy()
    out["Datetime"] = dt.loc[dt.notna()]
    for col in ("Open", "High", "Low", "Close", "Volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    out = out.sort_values("Datetime").drop_duplicates("Datetime", keep="last").reset_index(drop=True)
    if out.empty:
        raise ValueError(f"No valid OHLCV rows in {path}")
    return out


def _add_indicators(df: pd.DataFrame, rvol_lookback: int, ema_slope_bars: int) -> pd.DataFrame:
    df = df.copy()
    ny = df["Datetime"].dt.tz_convert("America/New_York")
    df["Session"] = ny.dt.strftime("%Y-%m-%d")
    df["TimeBucket"] = ny.dt.strftime("%H:%M")
    minute_of_day = ny.dt.hour * 60 + ny.dt.minute
    df["RTH"] = (minute_of_day >= 570) & (minute_of_day < 960)
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    pv = typical * df["Volume"]
    # RTH VWAP resets at 09:30 New York time and excludes extended-hours bars.
    rth_pv = pv.where(df["RTH"], 0.0)
    rth_vol = df["Volume"].where(df["RTH"], 0.0)
    cum_pv = rth_pv.groupby(df["Session"]).cumsum()
    cum_vol = rth_vol.groupby(df["Session"]).cumsum().replace(0, pd.NA)
    df["VWAP"] = (cum_pv / cum_vol).where(df["RTH"])
    df["EMA9"] = df.groupby("Session")["Close"].transform(lambda s: s.ewm(span=9, adjust=False, min_periods=9).mean())
    # Compare each RTH candle with the same time-of-day in prior sessions.
    # This avoids comparing the opening bell with quiet premarket candles.
    df["VolMedian"] = df.groupby("TimeBucket")["Volume"].transform(
        lambda s: s.shift(1).rolling(rvol_lookback, min_periods=max(5, rvol_lookback // 2)).median()
    )
    df["RVOL"] = df["Volume"] / df["VolMedian"].replace(0, pd.NA)
    prev = df.groupby("Session")["Close"].shift(1)
    prev_vwap = df.groupby("Session")["VWAP"].shift(1)
    df["LongCross"] = df["RTH"] & (df["Close"] > df["VWAP"]) & (df["Close"] > df["EMA9"]) & (
        prev <= prev_vwap
    )
    df["ShortCross"] = df["RTH"] & (df["Close"] < df["VWAP"]) & (df["Close"] < df["EMA9"]) & (
        prev >= prev_vwap
    )
    df["EmaSlopePct"] = (df["EMA9"] / df.groupby("Session")["EMA9"].shift(ema_slope_bars) - 1.0)
    return df


def _outcome(df: pd.DataFrame, i: int, side: str, tick: float, reward_risk: float, max_wait: int, exit_mode: str):
    signal = df.iloc[i]
    if side == "LONG":
        trigger = float(signal["High"] + tick)
        stop = float(signal["Low"] - tick)
        risk = trigger - stop
        target = trigger + reward_risk * risk
    else:
        trigger = float(signal["Low"] - tick)
        stop = float(signal["High"] + tick)
        risk = stop - trigger
        target = trigger - reward_risk * risk
    if risk <= 0:
        return "INVALID", None, trigger, stop, target

    # Entry can only trigger after the signal candle has closed.
    entry_end = min(len(df), i + 1 + max_wait)
    entry_i = None
    for j in range(i + 1, entry_end):
        bar = df.iloc[j]
        if bar["Session"] != signal["Session"]:
            break
        if not bar["RTH"]:
            continue
        if (side == "LONG" and bar["High"] >= trigger) or (side == "SHORT" and bar["Low"] <= trigger):
            entry_i = j
            break
    if entry_i is None:
        return "POSSIBLE SIGNAL", None, trigger, stop, target

    # Once filled, manage the position through the remainder of that RTH session.
    exit_end = entry_i
    while exit_end + 1 < len(df) and df.iloc[exit_end + 1]["Session"] == signal["Session"] and df.iloc[exit_end + 1]["RTH"]:
        exit_end += 1
    for j in range(entry_i, exit_end + 1):
        bar = df.iloc[j]
        if side == "LONG":
            stop_hit, target_hit = bar["Low"] <= stop, bar["High"] >= target
        else:
            stop_hit, target_hit = bar["High"] >= stop, bar["Low"] <= target
        if stop_hit:  # If both levels occur in one OHLC bar, assume stop first.
            return "SL HIT", df.iloc[j]["Datetime"], trigger, stop, target
        if exit_mode == "3R" and target_hit:
            return "GOOD (3R)", df.iloc[j]["Datetime"], trigger, stop, target
        # The EMA9-exit variant has no profit target. Exit on a confirmed candle
        # close through EMA9; keep the setup stop as a hard protective stop.
        prev_bar = df.iloc[j - 1] if j > 0 else bar
        if side == "LONG":
            crossed_ema9 = prev_bar["Close"] >= prev_bar["EMA9"] and bar["Close"] < bar["EMA9"]
        else:
            crossed_ema9 = prev_bar["Close"] <= prev_bar["EMA9"] and bar["Close"] > bar["EMA9"]
        if exit_mode == "EMA9" and crossed_ema9:
            outcome = "GOOD (EMA9 EXIT)" if ((bar["Close"] - trigger) * (1 if side == "LONG" else -1)) > 0 else "BAD (EMA9 EXIT)"
            return outcome, df.iloc[j]["Datetime"], trigger, stop, target
    close = df.iloc[exit_end]["Close"]
    outcome = "GOOD (EOD)" if ((close - trigger) * (1 if side == "LONG" else -1)) > 0 else "BAD (EOD)"
    return outcome, df.iloc[exit_end]["Datetime"], trigger, stop, target


def generate_signals(
    bars: pd.DataFrame,
    min_rvol: float = 1.2,
    flat_slope_pct: float = 0.0003,
    rvol_lookback: int = 20,
    ema_slope_bars: int = 3,
) -> pd.DataFrame:
    """Return the single source of truth for candle signals and filters.

    The returned rows retain OHLCV, VWAP, EMA9, RVOL, slope, and a `Signal`
    column (LONG/blank). Backtests and future plots should both consume
    this output so the plotted markers always match the tested logic.
    """
    df = _add_indicators(bars, rvol_lookback, ema_slope_bars)
    df["Signal"] = ""
    df["SignalReason"] = ""
    valid = df[["VWAP", "EMA9", "RVOL", "EmaSlopePct"]].notna().all(axis=1)
    long = valid & df["LongCross"] & (df["Close"] > df["Open"])
    long_slope_ok = df["EmaSlopePct"] >= flat_slope_pct
    ema_clear = df["Low"] > df["EMA9"]
    volume_ok = df["RVOL"] >= min_rvol
    df.loc[long & long_slope_ok & volume_ok & ema_clear, "Signal"] = "LONG"

    # Keep skip explanations for review of near-miss candles like flat/quiet periods.
    df.loc[long & ~volume_ok, "SignalReason"] = "NO TRADE: weak volume"
    df.loc[long & ~long_slope_ok, "SignalReason"] = "NO TRADE: EMA9 flat/not rising"
    df.loc[long & ~ema_clear, "SignalReason"] = "NO TRADE: candle touches/below EMA9"
    df.loc[df["Signal"] == "LONG", "SignalReason"] = "LONG: VWAP/EMA9 reclaim + volume + rising EMA9"
    return df


def evaluate_signals(
    signal_bars: pd.DataFrame,
    reward_risk: float = 3.0,
    tick: float = 0.01,
    max_wait: int = 12,
    exit_mode: str = "3R",
    start_date: str | None = None,
    end_date: str | None = None,
    suppress_overlaps: bool = True,
) -> pd.DataFrame:
    """Evaluate entries/outcomes using signal rows from `generate_signals`."""
    exit_mode = exit_mode.upper()
    if exit_mode not in {"3R", "EMA9"}:
        raise ValueError("exit_mode must be '3R' or 'EMA9'")
    df = signal_bars.reset_index(drop=True)
    results = []
    last_signal_by_session = {}
    for i in range(len(df)):
        row = df.iloc[i]
        side = row["Signal"]
        if side not in {"LONG", "SHORT"}:
            continue
        if start_date and row["Session"] < start_date:
            continue
        if end_date and row["Session"] > end_date:
            continue
        if suppress_overlaps and i <= last_signal_by_session.get(row["Session"], -1):
            continue
        status, exit_dt, entry, stop, target = _outcome(df, i, side, tick, reward_risk, max_wait, exit_mode)
        results.append({
            "signal_datetime_uk": row["Datetime"].tz_convert("Europe/London").strftime("%Y-%m-%d %H:%M %Z"),
            "side": side,
            "status": status,
            "exit_mode": exit_mode,
            "entry_trigger": round(entry, 4),
            "stop": round(stop, 4),
            "target_3r": round(target, 4),
            "rvol": round(float(row["RVOL"]), 2),
            "ema9_slope_pct": round(float(row["EmaSlopePct"] * 100), 4),
            "exit_datetime_uk": exit_dt.tz_convert("Europe/London").strftime("%Y-%m-%d %H:%M %Z") if exit_dt is not None else "",
        })
        last_signal_by_session[row["Session"]] = i + max_wait
    return pd.DataFrame(results)


def scan(
    bars: pd.DataFrame,
    months: int = 2,
    min_rvol: float = 1.2,
    flat_slope_pct: float = 0.0003,
    rvol_lookback: int = 20,
    ema_slope_bars: int = 3,
    reward_risk: float = 3.0,
    tick: float = 0.01,
    max_wait: int = 12,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Return (signal_bars, outcomes); both are reusable for later plotting."""
    signal_bars = generate_signals(bars, min_rvol, flat_slope_pct, rvol_lookback, ema_slope_bars)
    cutoff = signal_bars["Datetime"].max() - pd.DateOffset(months=months)
    signal_bars = signal_bars.loc[signal_bars["Datetime"] >= cutoff].reset_index(drop=True)
    # Same generated signal frame feeds both exit comparisons and future plots.
    outcomes = pd.concat([
        evaluate_signals(signal_bars, reward_risk, tick, max_wait, "3R", start_date, end_date),
        evaluate_signals(signal_bars, reward_risk, tick, max_wait, "EMA9", start_date, end_date),
    ], ignore_index=True)
    return signal_bars, outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description="MU 5m VWAP/EMA9 setup scan and 1:3 outcome labels")
    parser.add_argument("--csv", type=Path, default=DEFAULT_DATA, help=f"Input OHLCV CSV (default: {DEFAULT_DATA})")
    parser.add_argument("--months", type=int, default=2, help="Calendar months back from latest candle")
    parser.add_argument("--start-date", help="Optional signal start date, YYYY-MM-DD (New York session date)")
    parser.add_argument("--end-date", help="Optional signal end date, YYYY-MM-DD (New York session date)")
    parser.add_argument("--min-rvol", type=float, default=1.2, help="Minimum volume / prior rolling median")
    parser.add_argument("--flat-slope-pct", type=float, default=0.0003, help="Minimum 9EMA move over slope lookback; 0.0003 = 0.03%%")
    parser.add_argument("--max-wait", type=int, default=12, help="Bars allowed for entry trigger and outcome")
    args = parser.parse_args()

    bars = _read_bars(args.csv)
    print(f"MU 5m coverage: {bars['Datetime'].min()} to {bars['Datetime'].max()} (UTC)")
    start_date, end_date = args.start_date, args.end_date
    if not start_date and not end_date:
        last_session = bars["Datetime"].max().tz_convert("America/New_York").strftime("%Y-%m-%d")
        end_date = last_session
        end_dt = pd.Timestamp(end_date).tz_localize("America/New_York")
        start_date = (end_dt - pd.DateOffset(months=args.months)).strftime("%Y-%m-%d")
    signal_bars, results = scan(bars, months=args.months, min_rvol=args.min_rvol,
                                flat_slope_pct=args.flat_slope_pct, max_wait=args.max_wait,
                                start_date=start_date, end_date=end_date)
    print(f"Signal date range (New York): {start_date} to {end_date}")
    in_range = signal_bars[signal_bars["Session"].between(start_date, end_date)]
    rejected = in_range[in_range["SignalReason"].str.startswith("NO TRADE")]
    print(f"Rejected reclaim candles (flat/weak volume): {len(rejected)}")
    if results.empty:
        print("No qualifying candidates in the selected period.")
        return
    for mode, group in results.groupby("exit_mode", sort=False):
        good = group["status"].str.startswith("GOOD").sum()
        bad = group["status"].str.startswith(("BAD", "SL HIT")).sum()
        trades = int(good + bad)
        pending = int((group["status"] == "POSSIBLE SIGNAL").sum())
        win_rate = 100.0 * good / trades if trades else 0.0
        print(f"\n{mode} | Trades {trades} | Good {good} | Bad {bad} | Success {win_rate:.1f}% | Possible signals {pending}")
        print(group[["signal_datetime_uk", "side", "status"]].to_string(index=False))


if __name__ == "__main__":
    main()
