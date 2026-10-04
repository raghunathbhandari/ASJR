"""Regular-hours buy research: entry at signal close, exit below EMA9.

VWAP uses available full-session bars and a temporary 0.5% entry buffer.
Five consecutive RTH candles need positive high/low slopes and a meaningful
overall midpoint rise; individual candles may pull back.
Closing-price fills are research assumptions; fees/slippage are excluded.
"""
from pathlib import Path
import argparse
import pandas as pd

DEFAULT_DATA = Path(__file__).resolve().parents[1] / "BacktestData/IBKR/MarketData/5m/MU_5m.csv"


def generate_buy_signals(bars, *, vwap_buffer_pct=0.5, trend_min_move_pct=0.2, require_range_break=True):
    """Return indicators and reusable candle markers, without future data."""
    if vwap_buffer_pct < 0 or trend_min_move_pct < 0:
        raise ValueError("VWAP buffer and trend threshold must be nonnegative")
    df = bars.copy()
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)
    df = df.sort_values("Datetime").drop_duplicates("Datetime", keep="last").reset_index(drop=True)
    ny = df.Datetime.dt.tz_convert("America/New_York")
    df["Session"] = ny.dt.strftime("%Y-%m-%d")
    df["CandleTimeUK"] = df.Datetime.dt.tz_convert("Europe/London")
    minutes = ny.dt.hour * 60 + ny.dt.minute
    df["RTH"] = minutes.between(570, 959)
    df["EMA9"] = df.Close.ewm(span=9, adjust=False, min_periods=9).mean()
    pv = (df.High + df.Low + df.Close) / 3 * df.Volume
    volume = df.Volume.groupby(df.Session).cumsum().replace(0, float("nan"))
    df["VWAP"] = pv.groupby(df.Session).cumsum() / volume
    df["VWAPEntryLevel"] = df.VWAP * (1 + vwap_buffer_pct / 100)
    df["EMA9Rising"] = (
        (df.EMA9 > df.EMA9.shift(1))
        & (df.EMA9.shift(1) > df.EMA9.shift(2))
        & (df.EMA9.shift(2) > df.EMA9.shift(3))
    )
    # Least-squares slope for five equally spaced points: x = [-2,-1,0,1,2].
    def slope(values):
        return (-2 * values[0] - values[1] + values[3] + 2 * values[4]) / 10
    df["HighSlope5"] = df.High.rolling(5).apply(slope, raw=True)
    df["LowSlope5"] = df.Low.rolling(5).apply(slope, raw=True)
    midpoint = (df.High + df.Low) / 2
    df["TrendMovePct5"] = (midpoint / midpoint.shift(4) - 1) * 100
    trend = (df.HighSlope5 > 0) & (df.LowSlope5 > 0) & (df.TrendMovePct5 >= trend_min_move_pct)
    # Do not bridge a session boundary or missing 5-minute bars.
    consecutive = df.Datetime.diff().eq(pd.Timedelta(minutes=5)).rolling(4, min_periods=4).sum().eq(4)
    same_session = df.Session.eq(df.Session.shift(4))
    five_rth = df.RTH.rolling(5, min_periods=5).sum().eq(5)
    df["Trend5"] = trend & consecutive & same_session & five_rth
    df["BaseBuy"] = df.RTH & (df.Close > df.EMA9) & (df.Close > df.VWAPEntryLevel) & df.EMA9Rising
    # Exclude the signal candle itself: only already-completed highs form the range.
    df["PriorHigh10"] = df.groupby("Session").High.transform(
        lambda s: s.shift(1).rolling(10, min_periods=10).max()
    )
    df["RangeBreak"] = df.Close > df.PriorHigh10
    df["BuySignal"] = df.BaseBuy & df.Trend5
    if require_range_break:
        df["BuySignal"] &= df.RangeBreak
    return df


def evaluate_buys(signals, *, start_date, end_date, stop_buffer=0.01):
    """One position at a time; stop first, then EMA close, then RTH close.

    Signals and exits are labelled by candle start time. Close confirmation
    occurs five minutes later. No stop/exit is evaluated inside the entry bar.
    """
    df = signals[signals.Session.between(start_date, end_date) & signals.RTH].reset_index(drop=True)
    trades = []
    i = 0
    while i < len(df) - 1:
        signal = df.iloc[i]
        if not signal.BuySignal or df.iloc[i + 1].Session != signal.Session:
            i += 1
            continue
        entry = float(signal.Close)
        stop = float(signal.Low) - stop_buffer
        j = i + 1
        while j < len(df):
            bar = df.iloc[j]
            if bar.Open <= stop:
                price, reason = float(bar.Open), "SL gap"
            elif bar.Low <= stop:
                price, reason = stop, "SL hit"
            elif bar.Close < bar.EMA9:
                price, reason = float(bar.Close), "EMA9 exit"
            elif j == len(df) - 1 or df.iloc[j + 1].Session != bar.Session:
                price, reason = float(bar.Close), "RTH end"
            else:
                j += 1
                continue
            trades.append({
                "CandleTimeUK": signal.CandleTimeUK,
                "Entry": entry, "Stop": stop,
                "ExitCandleUK": bar.CandleTimeUK, "Exit": price,
                "Reason": reason,
                "Status": "Good" if price > entry else "Bad" if price < entry else "Flat",
                "GainPct": (price / entry - 1) * 100,
            })
            break
        i = j + 1
    return pd.DataFrame(trades, columns=["CandleTimeUK", "Entry", "Stop", "ExitCandleUK", "Exit", "Reason", "Status", "GainPct"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--vwap-buffer-pct", type=float, default=0.5)
    parser.add_argument("--trend-min-move-pct", type=float, default=0.2)
    parser.add_argument("--allow-range-entries", action="store_true", help="Disable the previous-10-candle range breakout filter.")
    args = parser.parse_args()
    signals = generate_buy_signals(pd.read_csv(args.csv), vwap_buffer_pct=args.vwap_buffer_pct, trend_min_move_pct=args.trend_min_move_pct, require_range_break=not args.allow_range_entries)
    trades = evaluate_buys(signals, start_date=args.start_date, end_date=args.end_date)
    good = trades.Status.eq("Good").sum()
    bad = trades.Status.eq("Bad").sum()
    success = 100 * good / len(trades) if len(trades) else 0
    print(f"Trades={len(trades)} Good={good} Bad={bad} Success={success:.1f}%")
    print(trades.to_string(index=False))


if __name__ == "__main__":
    main()
