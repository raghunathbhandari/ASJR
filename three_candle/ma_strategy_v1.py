"""Independent Rudra MA Strategy V1 — no Three-Candle/Gann signal logic.

Place this file beside three_candle_learing.py and import it directly
from the existing three_candle notebook directory.
"""

from datetime import date

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Only share the existing IBKR/Yahoo data reader and timeframe normalizer.
# This module does not call any Three-Candle signal/filter/backtest method.
from three_candle_learing import load_learning_candles, normalise_learning_timeframe


# 13. MA STRATEGY V1 — independent of Three-Candle and Gann
def MA_strategy_v1(ticker, dateFrom, dateTo, timeframe="5min", verbose=True,
                   require_ema200=False):
    """BUY-only EMA alignment study; no Three-Candle or Gann checks.

    Candidate: completed candle CLOSE > EMA9 > EMA21.
    EMA200 is measured for research, but optional as an entry filter.
    The simulated order is placed at the NEXT candle OPEN, never the
    qualifying candle's close (which was not known beforehand).
    Slopes are percent change of each EMA over the previous 3 bars.
    """
    data = load_learning_candles(ticker, dateFrom, dateTo, timeframe)
    frame = data.copy()
    for span in (9, 21, 200):
        key = f"EMA{span}"
        frame[key] = frame.Close.ewm(span=span, adjust=False).mean()
        frame[f"{key}_slope_pct"] = 100 * (
            frame[key] / frame[key].shift(3) - 1)
        frame[f"{key}_slope_pts"] = frame[key] - frame[key].shift(3)
    # Only EMA21 warm-up is required by default. The optional EMA200
    # filter reproduces the stronger three-EMA alignment on request.
    bar_count = pd.Series(range(len(frame)), index=frame.index)
    frame["MA_pass"] = ((frame.Close > frame.EMA9) &
                        (frame.EMA9 > frame.EMA21) & (bar_count >= 20))
    if require_ema200:
        frame["MA_pass"] &= ((frame.EMA21 > frame.EMA200) & (bar_count >= 199))
    start, end = date.fromisoformat(str(dateFrom)), date.fromisoformat(str(dateTo))
    in_dates = (frame.index.date >= start) & (frame.index.date <= end)
    selected = frame.loc[in_dates & frame.MA_pass].copy()
    rows = []
    minutes = data.attrs.get("timeframe_minutes", 5)
    bar_step = pd.Timedelta(minutes=minutes)
    for stamp, candle in selected.iterrows():
        idx = int(frame.index.get_loc(stamp))
        if idx+1 >= len(frame) or frame.index[idx+1]-stamp != bar_step:
            continue
        next_bar = frame.iloc[idx+1]
        rows.append({
            "Signal": len(rows)+1, "Direction": "BUY", "MA_pass": True,
            "Signal_time": stamp, "Entry_time": frame.index[idx+1],
            "Signal_Close": float(candle.Close),
            "Entry_open": float(next_bar.Open),
            "EMA9": float(candle.EMA9),
            "EMA21": float(candle.EMA21),
            "EMA200": float(candle.EMA200),
            "EMA9_slope_pct": float(candle.EMA9_slope_pct),
            "EMA21_slope_pct": float(candle.EMA21_slope_pct),
            "EMA200_slope_pct": float(candle.EMA200_slope_pct),
            "EMA9_slope_pts": float(candle.EMA9_slope_pts),
            "EMA21_slope_pts": float(candle.EMA21_slope_pts),
            "EMA200_slope_pts": float(candle.EMA200_slope_pts),
            "Close_minus_EMA9": float(candle.Close-candle.EMA9),
            "EMA9_minus_EMA21": float(candle.EMA9-candle.EMA21),
            "EMA21_minus_EMA200": float(candle.EMA21-candle.EMA200),
            "Candle_range_points": float(candle.High-candle.Low),
            "Candle_body_points": float(abs(candle.Close-candle.Open)),
            "Volume": float(candle.Volume),
            "Volume_ratio_20": float(candle.Volume / frame.Volume.iloc[
                max(0, idx-19):idx+1].mean())
                if frame.Volume.iloc[max(0, idx-19):idx+1].mean() > 0 else float("nan"),
        })
    result = pd.DataFrame(rows)
    result.attrs = {
        "candles": frame,
        "requested_start": str(dateFrom),
        "timeframe": normalise_learning_timeframe(timeframe),
        "contract": str(ticker).upper(),
        "strategy": "MA_strategy_v1",
        "require_ema200": bool(require_ema200),
    }
    if verbose:
        print(f"MA_strategy_v1 | {ticker} | {dateFrom} to {dateTo} | "
              f"{len(result)} aligned BUY candles")
        print("Rule: Close > EMA9 > EMA21; EMA200 optional; entry next bar OPEN.")
        print("EMA slopes: 3-candle change in points and percent.")
        if not result.empty:
            from IPython.display import display
            display(result)
    return result


def summarise_MA_strategy_v1(result, stop_points=6.0, verbose=True):
    """Non-overlapping long trades; 1R=6pt, 1R stepped trail, no TP.

    Stops are active immediately; trailing increases only after a bar
    CLOSES, for application on the NEXT bar. If the same bar touches
    stop and a higher R, stop is processed first (conservative).
    """
    import math
    if stop_points <= 0:
        raise ValueError("stop_points must be positive")
    candles = result.attrs.get("candles")
    if candles is None or candles.empty:
        raise ValueError("MA_strategy_v1 result with candles required")
    if result.attrs.get("strategy") != "MA_strategy_v1":
        raise ValueError("Pass a MA_strategy_v1 result, not Three-Candle signals")
    rows, blocked_until = [], -1
    for _, signal in result.sort_values("Entry_time").iterrows():
        stamp = signal.Entry_time
        if stamp not in candles.index:
            continue
        entry_idx = int(candles.index.get_loc(stamp))
        if entry_idx <= blocked_until:
            continue
        entry = float(candles.Open.iloc[entry_idx])
        stop = entry-stop_points
        max_step, exit_idx, exit_price = 0, None, None
        for j in range(entry_idx, len(candles)):
            bar = candles.iloc[j]
            if float(bar.Low) <= stop:
                exit_idx = j
                exit_price = min(float(bar.Open), stop)  # gap-aware
                break
            # At the close, record favourable R; apply its new stop next bar.
            favourable = float(bar.High)-entry
            next_step = max(0, int(math.floor((favourable+1e-9)/stop_points)))
            if next_step > max_step:
                max_step = next_step
                stop = max(stop, entry+(max_step-1)*stop_points)
        closed = exit_idx is not None
        if closed:
            blocked_until = exit_idx
            last_price = exit_price
        else:
            blocked_until = len(candles)
            last_price = float(candles.Close.iloc[-1])
        points = last_price-entry
        rows.append({
            "Signal": signal.Signal, "Direction": "BUY",
            "Signal_time": signal.Signal_time,
            "Entry_time": stamp, "Entry": entry,
            "Initial_SL": entry-stop_points, "Final_SL": stop,
            "Exit_time": candles.index[exit_idx] if closed else pd.NaT,
            "Exit": exit_price if closed else float("nan"),
            "Status": "CLOSED" if closed else "OPEN",
            "Max_R_step": max_step,
            "Points": points, "Return_pct": 100*points/entry,
            "R": points/stop_points,
        })
    trades = pd.DataFrame(rows)
    closed = trades.loc[trades.Status == "CLOSED"] if not trades.empty else trades
    wins = int((closed.Points > 0).sum()) if not closed.empty else 0
    losses = int((closed.Points < 0).sum()) if not closed.empty else 0
    be = len(closed)-wins-losses
    equity = pd.concat([pd.Series([0.0]), closed.Points.cumsum().reset_index(drop=True)],
                       ignore_index=True) if not closed.empty else pd.Series([0.0])
    drawdown = float((equity.cummax()-equity).max())
    if verbose:
        print("\n========== MA STRATEGY V1 — 1R STEPPED TRAILING ==========")
        print(f"Candidates            : {len(result)}")
        print(f"Executed / Closed     : {len(trades)} / {len(closed)}")
        print(f"Wins / Losses / BE    : {wins} / {losses} / {be}")
        print(f"Success rate          : {100*wins/len(closed) if len(closed) else 0:.2f}%")
        print(f"Realised points       : {closed.Points.sum() if not closed.empty else 0.0:+.2f}")
        print(f"Realised return       : {closed.Return_pct.sum() if not closed.empty else 0.0:+.3f}%")
        print(f"Max drawdown          : {drawdown:.2f} points")
        print(f"Rules                 : BUY, close above aligned EMAs; next open entry; "
              f"1R={stop_points:g} points; 1R step trail; no TP")
        print("OPEN positions excluded from realised statistics; fees/slippage excluded.")
        if not trades.empty:
            from IPython.display import display
            display(trades)
    trades.attrs = result.attrs.copy()
    return trades


def _plot_MA_v1(result, trades=None, multiChart=False, show_entries=False):
    """Same compact white/blue TradingView candle style; no grid."""
    from base64 import b64encode
    from io import BytesIO
    from IPython.display import HTML, display

    candles = result.attrs.get("candles")
    if candles is None or candles.empty:
        raise ValueError("MA_strategy_v1 result with candles required")
    start = date.fromisoformat(result.attrs["requested_start"])
    visible_data = candles.loc[candles.index.date >= start]
    if visible_data.empty:
        print("No candles to plot.")
        return
    days = list(dict.fromkeys(visible_data.index.date))
    for day in days:
        daily = visible_data.loc[visible_data.index.date == day]
        if multiChart:
            sections = [(i, min(i+100, len(daily)))
                        for i in range(0, len(daily), 100)]
        else:
            sections = [(0, len(daily))]
        for first, last in sections:
            visible = daily.iloc[first:last]
            width = 14 if multiChart else max(14, 14*len(visible)/100)
            fig, ax = plt.subplots(figsize=(width, 6), facecolor="#101722")
            ax.set_facecolor("#101722")
            for i, c in enumerate(visible.itertuples()):
                colour = "#d4d4d8" if c.Close >= c.Open else "#3b82f6"
                ax.vlines(i, c.Low, c.High, color=colour, linewidth=1)
                ax.add_patch(Rectangle((i-.33, min(c.Open, c.Close)),
                                       .66, max(.01, abs(c.Close-c.Open)),
                                       facecolor=colour, edgecolor=colour))
            for span, colour, lw in ((9, "#33c8ff", 1.4),
                                     (21, "#ff9f0a", 1.8),
                                     (200, "#b58cff", 1.4)):
                ax.plot(range(len(visible)), visible[f"EMA{span}"],
                        color=colour, linewidth=lw, label=f"EMA{span}")
            if show_entries:
                plotted = trades if trades is not None else pd.DataFrame()
                if not plotted.empty:
                    for _, t in plotted.iterrows():
                        if t.Entry_time not in visible.index:
                            continue
                        x = int(visible.index.get_loc(t.Entry_time))
                        ax.scatter(x, float(visible.Low.iloc[x])-2,
                                   s=55, color="#35e89b", edgecolors="white",
                                   linewidths=.5, zorder=8)
                        ax.axhline(float(t.Entry), color="#35e89b",
                                   linewidth=1, alpha=.9)
                        ax.axhline(float(t.Initial_SL), color="#ff6471",
                                   linewidth=1, linestyle="--")
                        if t.Status == "CLOSED":
                            colour = "#bd91ff" if t.Points > 0 else "#ff6471"
                            ax.axhline(float(t.Exit), color=colour,
                                       linewidth=1, linestyle="-.")
                            if t.Exit_time in visible.index:
                                x2 = int(visible.index.get_loc(t.Exit_time))
                                ax.scatter(x2, float(visible.Low.iloc[x2])-2,
                                           s=55, color=colour, edgecolors="white",
                                           linewidths=.5, zorder=8)
            else:
                matched = (result[result.Signal_time.isin(visible.index)]
                           if not result.empty else result)
                for _, c in matched.iterrows():
                    x = int(visible.index.get_loc(c.Signal_time))
                    ax.scatter(x, float(visible.Low.iloc[x])-2, s=35,
                               color="#35e89b", edgecolors="white",
                               linewidths=.4, zorder=8)
            ax.set_ylim(float(visible.Low.min())-12, float(visible.High.max())+12)
            ax.set_xlim(-1, len(visible))
            ticks = list(range(0, len(visible), max(1, len(visible)//12)))
            ax.set_xticks(ticks, [visible.index[i].strftime("%d %b %H:%M")
                                 for i in ticks], rotation=35, ha="right")
            ax.set_title(f"{result.attrs.get('contract','Futures')} | "
                         f"MA Strategy V1 | {day} | UK time",
                         color="#f0f5fa")
            ax.set_ylabel("Futures price", color="#dbe5f0")
            ax.tick_params(colors="#dbe5f0")
            ax.grid(False)
            ax.legend(loc="best", facecolor="#1a2534",
                      edgecolor="#526174", labelcolor="white")
            for spine in ax.spines.values():
                spine.set_color("#526174")
            fig.tight_layout()
            if multiChart:
                plt.show()
                plt.close(fig)
            else:
                output = BytesIO()
                fig.savefig(output, format="png", dpi=100,
                            facecolor=fig.get_facecolor())
                encoded = b64encode(output.getvalue()).decode("ascii")
                plt.close(fig)
                display(HTML(
                    f'<div style="width:100%;overflow-x:auto;overflow-y:hidden;">'
                    f'<img src="data:image/png;base64,{encoded}" '
                    f'style="width:{int(width*100)}px;max-width:none;height:auto;" />'
                    f'</div>'
                ))


def plot_signal_candidate_MAs(result, multiChart=False):
    """Plot every MA-aligned BUY candidate with EMA9/20/200."""
    return _plot_MA_v1(result, multiChart=multiChart)


def plot_signal_passed_MAs(result, stop_points=6.0, multiChart=False):
    """Plot executed MA trades, including entry, 6pt SL and trail exit."""
    trades = summarise_MA_strategy_v1(result, stop_points, verbose=False)
    return _plot_MA_v1(result, trades=trades, multiChart=multiChart,
                       show_entries=True)


# User-friendly aliases for the requested MA method naming.
three_candle_with_MAs = MA_strategy_v1
summarise_signal_result_MAs = summarise_MA_strategy_v1


