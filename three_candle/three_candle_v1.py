"""Rudra Three-Candle V1: causal C2-body-break entry on MES 5-minute bars.

This is deliberately independent of the V4 learning engine and MA strategies.
C3 volume/close are *not* filters for an intrabar C3 entry: their final
values cannot be known when the C2-body stop order first triggers.
"""
from pathlib import Path
import pandas as pd


def load_v1_mes(ticker, date_from, date_to):
    """Read downloaded IBKR daily/monthly CSVs; no network downloads."""
    root = Path(__file__).resolve().parent / "data"
    dates = pd.date_range(date_from, date_to, freq="D")
    files = []
    for day in dates:
        daily = root / f"{ticker}_IBKR_5m_{day:%Y-%m-%d}.csv"
        monthly = root / f"{ticker}_IBKR_5m_{day:%Y-%m}.csv"
        file = daily if daily.exists() else monthly if monthly.exists() else None
        if file is not None and file not in files:
            files.append(file)
    if not files:
        raise FileNotFoundError(f"Missing IBKR data for {ticker}: {date_from}..{date_to}")
    fields = ["Datetime_UTC", "Open", "High", "Low", "Close", "Volume"]
    raw = pd.concat([pd.read_csv(path, usecols=fields) for path in files],
                    ignore_index=True)
    raw["Datetime_UTC"] = pd.to_datetime(raw["Datetime_UTC"], format="mixed",
                                          errors="coerce", utc=True)
    for field in fields[1:]:
        raw[field] = pd.to_numeric(raw[field], errors="coerce")
    raw = raw.dropna(subset=fields).drop_duplicates("Datetime_UTC")
    raw = raw.sort_values("Datetime_UTC").set_index("Datetime_UTC")
    raw.index = raw.index.tz_convert("Europe/London")
    first, last = pd.Timestamp(date_from).date(), pd.Timestamp(date_to).date()
    return raw.loc[(raw.index.date >= first) & (raw.index.date <= last)].copy()


def three_candle_v1(ticker, date_from, date_to, stop_tick=0.25,
                    verbose=True):
    """Find C2 wick+sweep setups and execute a stop-buy within C3.

    C2 green; lower wick > C2 body; C2 low < C1 low; C2 close > C1 low.
    Place BUY stop at C2 close immediately after C2 has completed.
    On C3, fill at max(C3 open, C2 close) if C3 high touches the trigger.
    No future C3 close or volume leakage into entry qualification.
    Initial SL = C2 open; 1R=max(C2 body, 0.1% C2 close).
    Stop-first, then +1R milestone trail effective on the following candle.
    Signal-to-signal positions may not overlap.
    """
    bars = load_v1_mes(ticker, date_from, date_to)
    rows = []
    blocked_until = -1
    for i in range(2, len(bars)):
        a, b, c = bars.iloc[i-2], bars.iloc[i-1], bars.iloc[i]
        if ((bars.index[i]-bars.index[i-1] != pd.Timedelta(minutes=5)) or
            (bars.index[i-1]-bars.index[i-2] != pd.Timedelta(minutes=5))):
            continue
        body = float(b.Close-b.Open)
        if not (body > 0 and float(b.Open-b.Low) > body
                and b.Low < a.Low and b.Close > a.Low):
            continue
        trigger = float(b.Close)
        risk_unit = max(body, 0.001 * trigger)
        stop = float(b.Open)
        if i <= blocked_until or float(c.High) < trigger:
            continue
        entry = max(float(c.Open), trigger)
        if entry <= stop:
            continue
        first_stop = stop
        max_step = 0
        exit_price = float("nan")
        exit_idx = None
        # A stop touched on the entry candle may precede the breakout.
        # Pessimistically assume fill then stop; flag the ambiguity.
        ambiguous = bool(c.Open < trigger and c.Low <= stop)
        for j in range(i, len(bars)):
            bar = bars.iloc[j]
            if float(bar.Low) <= stop:
                exit_idx = j
                exit_price = min(float(bar.Open), stop) if j > i else stop
                break
            # Lock the reached milestone AFTER this candle, never within it.
            step = max(0, int((float(bar.High) - entry + 1e-9) // risk_unit))
            if step > max_step:
                max_step = step
                proposed = entry + step * risk_unit
                proposed = int((proposed + 1e-9) / stop_tick) * stop_tick
                stop = max(stop, proposed)
        closed = exit_idx is not None
        blocked_until = exit_idx if closed else len(bars)
        mark = exit_price if closed else float(bars.Close.iloc[-1])
        points = mark-entry
        rows.append({
            "C2_time": bars.index[i-1],
            "C3_time": bars.index[i],
            "Entry_time": bars.index[i],
            "Entry": entry,
            "Initial_SL": first_stop,
            "Risk_points": entry-first_stop,
            "R_points": risk_unit,
            "C3_volume_higher_research_only": bool(c.Volume > b.Volume),
            "C3_close_higher_research_only": bool(c.Close > b.Close),
            "Ambiguous_entry_stop": ambiguous,
            "Exit_time": bars.index[exit_idx] if closed else pd.NaT,
            "Exit": exit_price if closed else float("nan"),
            "Final_SL": stop,
            "Max_R_step": max_step,
            "Status": "CLOSED" if closed else "OPEN",
            "Points": points,
            "Return_pct": 100 * points / entry,
        })
    trades = pd.DataFrame(rows)
    done = trades.loc[trades.Status == "CLOSED"] if not trades.empty else trades
    equity = pd.concat([pd.Series([0.0]), done.Points.cumsum().reset_index(drop=True)],
                       ignore_index=True) if not done.empty else pd.Series([0.0])
    drawdown = float((equity.cummax()-equity).max())
    if verbose:
        win = int((done.Points > 0).sum()) if not done.empty else 0
        loss = int((done.Points < 0).sum()) if not done.empty else 0
        print(f"RUDRA V1 C2-BODY BREAK | {ticker} | {date_from}..{date_to}")
        print(f"Closed {len(done)} | W/L/BE {win}/{loss}/{len(done)-win-loss} "
              f"| Success {100*win/len(done) if len(done) else 0:.2f}%")
        print(f"Realised {done.Points.sum() if len(done) else 0:+.2f} points "
              f"| Max drawdown {drawdown:.2f} points")
        print(f"Ambiguous entry/stop bars: "
              f"{int(trades.Ambiguous_entry_stop.sum()) if len(trades) else 0}")
        print("No C3 lookahead. MES tick-rounded trail. Fees/slippage excluded.")
        if not trades.empty:
            from IPython.display import display
            display(trades)
    return trades
