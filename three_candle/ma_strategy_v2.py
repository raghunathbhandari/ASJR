"""Rudra MA Strategy V2: fixed EMA cross + slope + RSI + ADX research.

Independent of the Three-Candle signal engine. IBKR CSV data is read
through the existing MA V1 loader (including historical EMA warm-up).
All candle times use Europe/London.
"""
import math
import pandas as pd

from ma_strategy_v1 import load_MA_history


def _wilder(series, period=14):
    """Wilder's recursively smoothed average (RMA)."""
    return series.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _indicators(candles):
    frame = candles.copy()
    for period in (9, 21):
        ema = frame.Close.ewm(span=period, adjust=False).mean()
        frame[f"EMA{period}"] = ema
        frame[f"EMA{period}_slope_pts"] = ema.diff(3)

    delta = frame.Close.diff()
    up = delta.clip(lower=0)
    down = (-delta).clip(lower=0)
    avg_up, avg_down = _wilder(up), _wilder(down)
    rs = avg_up / avg_down.replace(0, float("nan"))
    frame["RSI14"] = (100 - 100 / (1 + rs)).where(avg_down != 0, 100.0)
    frame.loc[(avg_down == 0) & (avg_up == 0), "RSI14"] = 50.0

    prev_close = frame.Close.shift(1)
    tr = pd.concat((frame.High - frame.Low,
                    (frame.High - prev_close).abs(),
                    (frame.Low - prev_close).abs()), axis=1).max(axis=1)
    up_move = frame.High.diff()
    down_move = -frame.Low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    atr = _wilder(tr).replace(0, float("nan"))
    plus_di = 100 * _wilder(plus_dm) / atr
    minus_di = 100 * _wilder(minus_dm) / atr
    denominator = (plus_di + minus_di).replace(0, float("nan"))
    dx = 100 * (plus_di - minus_di).abs() / denominator
    frame["ADX14"] = _wilder(dx)
    frame["ADX_rising"] = frame.ADX14 > frame.ADX14.shift(1)
    return frame


def MA_strategy_v2(ticker, dateFrom, dateTo, timeframe="5min", verbose=True):
    """Fixed BUY/SELL conditions, next-candle-open fills.

    BUY: EMA9 crosses above EMA21, both 3-bar slopes > 0,
         RSI14 > 50, ADX14 > 20 and rising.
    SELL: exact reverse of EMA/slope/RSI; ADX condition identical.
    VWAP, higher timeframe, previous-day SR are deliberately NOT included.
    """
    candles = load_MA_history(ticker, dateFrom, dateTo, timeframe)
    frame = _indicators(candles)
    fast, slow = frame.EMA9, frame.EMA21
    cross_up = (fast > slow) & (fast.shift(1) <= slow.shift(1))
    cross_down = (fast < slow) & (fast.shift(1) >= slow.shift(1))
    strong = (frame.ADX14 > 20) & frame.ADX_rising
    buy = (cross_up & (frame.EMA9_slope_pts > 0) &
           (frame.EMA21_slope_pts > 0) & (frame.RSI14 > 50) & strong)
    sell = (cross_down & (frame.EMA9_slope_pts < 0) &
            (frame.EMA21_slope_pts < 0) & (frame.RSI14 < 50) & strong)
    start = pd.Timestamp(dateFrom).date()
    end = pd.Timestamp(dateTo).date()
    dates = (frame.index.date >= start) & (frame.index.date <= end)
    minutes = candles.attrs.get("timeframe_minutes", 5)
    next_time = frame.index.to_series().shift(-1)
    contiguous = (next_time - frame.index.to_series() ==
                  pd.Timedelta(minutes=minutes))
    selected = frame.loc[dates & contiguous & (buy | sell)].copy()
    result = pd.DataFrame(index=selected.index)
    result["Signal_time"] = selected.index
    result["Direction"] = ["BUY" if buy.loc[i] else "SELL" for i in selected.index]
    result["Entry_time"] = next_time.reindex(selected.index)
    result["Entry_open"] = frame.Open.shift(-1).reindex(selected.index)
    result["Signal_Close"] = selected.Close
    for name in ("EMA9", "EMA21", "EMA9_slope_pts", "EMA21_slope_pts",
                 "RSI14", "ADX14", "ADX_rising"):
        result[name] = selected[name]
    result = result.reset_index(drop=True)
    result.insert(0, "Signal", range(1, len(result) + 1))
    result.attrs = {"candles": frame, "strategy": "MA_strategy_v2",
                    "contract": ticker, "requested_start": str(dateFrom),
                    "requested_end": str(dateTo), "timeframe": timeframe}
    if verbose:
        print(f"MA V2 | {ticker} | {dateFrom} to {dateTo} | "
              f"BUY {(result.Direction == 'BUY').sum()} | "
              f"SELL {(result.Direction == 'SELL').sum()}")
        if not result.empty:
            from IPython.display import display
            display(result)
    return result


def summarise_MA_strategy_v2(result, stop_points=6.0, verbose=True):
    """Backtest non-overlapping next-open trades with 1R stepped trailing.

    Stop first inside a candle; the new trailing stop activates on the
    following candle. Gaps are executed at the open when worse than stop.
    Last-candle open trades are marked OPEN and excluded from realised P/L.
    """
    if stop_points <= 0:
        raise ValueError("stop_points must be positive")
    frame = result.attrs["candles"]
    rows = []
    blocked_until = -1
    for signal in result.sort_values("Entry_time").itertuples(index=False):
        stamp = signal.Entry_time
        if stamp not in frame.index:
            continue
        idx = frame.index.get_loc(stamp)
        if idx <= blocked_until:
            continue
        side = 1 if signal.Direction == "BUY" else -1
        entry = float(frame.Open.iloc[idx])
        stop = entry - side * stop_points
        step = 0
        exit_index = None
        exit_price = float("nan")
        for j in range(idx, len(frame)):
            bar = frame.iloc[j]
            touched = bar.Low <= stop if side == 1 else bar.High >= stop
            if touched:
                exit_index = j
                opening = float(bar.Open)
                exit_price = min(opening, stop) if side == 1 else max(opening, stop)
                break
            favourable = ((bar.High - entry) if side == 1
                          else (entry - bar.Low))
            new_step = max(0, int(math.floor((favourable + 1e-9) / stop_points)))
            if new_step > step:
                step = new_step
                candidate_stop = entry + side * (step - 1) * stop_points
                stop = (max(stop, candidate_stop) if side == 1
                        else min(stop, candidate_stop))
        closed = exit_index is not None
        blocked_until = exit_index if closed else len(frame)
        mark = exit_price if closed else float(frame.Close.iloc[-1])
        points = side * (mark - entry)
        rows.append({
            "Signal_time": signal.Signal_time, "Direction": signal.Direction,
            "EMA9_slope_pts": signal.EMA9_slope_pts,
            "EMA21_slope_pts": signal.EMA21_slope_pts,
            "RSI14": signal.RSI14, "ADX14": signal.ADX14,
            "Entry_time": stamp, "Entry": entry, "Initial_SL": entry-side*stop_points,
            "Exit_time": frame.index[exit_index] if closed else pd.NaT,
            "Exit": exit_price, "Final_SL": stop, "Max_R_step": step,
            "Status": "CLOSED" if closed else "OPEN",
            "Points": points, "Return_pct": 100 * points / entry,
            "R": points / stop_points,
        })
    trades = pd.DataFrame(rows)
    done = trades.loc[trades.Status == "CLOSED"] if not trades.empty else trades
    wins = int((done.Points > 0).sum()) if not done.empty else 0
    losses = int((done.Points < 0).sum()) if not done.empty else 0
    breakeven = len(done) - wins - losses
    equity = pd.concat((pd.Series([0.0]), done.Points.cumsum().reset_index(drop=True)),
                       ignore_index=True) if not done.empty else pd.Series([0.0])
    dd = float((equity.cummax() - equity).max())
    if verbose:
        print("========== MA STRATEGY V2 | CROSS + RSI14 + ADX14 ==========")
        print(f"Signals               : {len(result)}")
        print(f"Executed / Closed     : {len(trades)} / {len(done)}")
        print(f"Wins / Losses / BE    : {wins} / {losses} / {breakeven}")
        print(f"Success rate          : {100*wins/len(done) if len(done) else 0:.2f}%")
        print(f"Realised points       : {done.Points.sum() if len(done) else 0:+.2f}")
        print(f"Realised return       : {done.Return_pct.sum() if len(done) else 0:+.3f}%")
        print(f"Max drawdown          : {dd:.2f} points")
        print("1R=6pt default; stepped trailing, no TP; fees/slippage excluded.")
        if not trades.empty:
            from IPython.display import display
            display(trades)
    trades.attrs = result.attrs.copy()
    return trades
