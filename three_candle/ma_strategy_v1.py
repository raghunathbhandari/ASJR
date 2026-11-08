"""Independent Rudra MA Strategy V1 — no Three-Candle/Gann signal logic.

Place this file beside three_candle_learing.py and import it directly
from the existing three_candle notebook directory.
"""

from datetime import date, timedelta
from pathlib import Path
import re

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Only share the existing IBKR/Yahoo data reader and timeframe normalizer.
# This module does not call any Three-Candle signal/filter/backtest method.
from three_candle_learing import load_learning_candles, normalise_learning_timeframe


def load_MA_history(ticker, dateFrom, dateTo, timeframe="5min",
                    min_warmup_bars=600):
    """Read exact-contract IBKR daily/monthly CSVs ONCE, vectorially.

    Prefer CONTRACT_5m_YYYY-MM-DD.csv, then CONTRACT_5m_YYYY-MM.csv.
    No historical retries or per-candle processing loops.
    Preserve the Three-Candle loader untouched.
    """
    requested = str(ticker).upper().strip()
    match = re.fullmatch(r"(MES|NQ|GC)([FGHJKMNQUVXZ])([0-9]{4})", requested)
    if match is None:
        raise ValueError("MA V1 direct IBKR reader needs dated contract, e.g. MESZ2026")
    from_day, to_day = date.fromisoformat(str(dateFrom)), date.fromisoformat(str(dateTo))
    if from_day > to_day:
        raise ValueError("dateFrom must be <= dateTo")
    interval = normalise_learning_timeframe(timeframe)
    minutes = 5 if interval == "5m" else 15
    folder = Path(__file__).resolve().parent / "data"
    files = []
    # Read at most 14 historical calendar days, prioritising daily files.
    history_start = from_day - timedelta(days=14)
    for offset in range((to_day-history_start).days+1):
        day = history_start+timedelta(days=offset)
        daily = folder / f"{requested}_IBKR_5m_{day}.csv"
        monthly = folder / f"{requested}_IBKR_5m_{day.year}-{day.month:02d}.csv"
        path = daily if daily.is_file() else monthly if monthly.is_file() else None
        if path is not None and path not in files:
            files.append(path)
    if not files:
        raise FileNotFoundError(f"No local IBKR CSVs for {requested} near {dateFrom}")

    fields = ["Datetime_UTC", "Open", "High", "Low", "Close", "Volume"]
    raw = pd.concat((pd.read_csv(path, usecols=fields) for path in files),
                    ignore_index=True)
    raw["Datetime_UTC"] = pd.to_datetime(raw["Datetime_UTC"], utc=True,
                                          errors="coerce")
    for field in fields[1:]:
        raw[field] = pd.to_numeric(raw[field], errors="coerce")
    raw = raw.dropna(subset=fields).sort_values("Datetime_UTC")
    raw = raw.drop_duplicates("Datetime_UTC").set_index("Datetime_UTC")
    raw = raw.loc[(raw.index.date >= history_start) &
                  (raw.index.date <= to_day)]
    bad = ((raw.High < raw[["Open", "Close", "Low"]].max(axis=1))
           | (raw.Low > raw[["Open", "Close", "High"]].min(axis=1))
           | ((raw.High-raw.Low)/raw.Close > 0.02))
    raw = raw.loc[~bad]
    if minutes == 15:
        grouped = raw.groupby(raw.index.floor("15min"))
        candles = grouped.agg({"Open": "first", "High": "max",
                               "Low": "min", "Close": "last", "Volume": "sum"})
        count = grouped.size()
        # 3 complete contiguous five-minute timestamps per 15m bar.
        expected = grouped.apply(
            lambda g: len(g) == 3 and
            (g.index[1]-g.index[0] == pd.Timedelta(minutes=5)) and
            (g.index[2]-g.index[1] == pd.Timedelta(minutes=5)))
        candles = candles.loc[(count == 3) & expected]
    else:
        candles = raw.copy()
    candles.index = candles.index.tz_convert("Europe/London")
    start_mask = candles.index.date >= from_day
    if not start_mask.any():
        raise ValueError(f"No IBKR candles for {requested} on {dateFrom}")
    first_idx = int(start_mask.argmax())
    if first_idx < min_warmup_bars:
        raise ValueError(
            f"Only {first_idx} warm-up candles; need {min_warmup_bars}. "
            f"Sync earlier IBKR CSVs for {requested}.")
    candles = candles.iloc[first_idx-min_warmup_bars:].copy()
    candles.attrs["timeframe_minutes"] = minutes
    candles.attrs["ma_warmup_bars"] = min_warmup_bars
    return candles


# 13. MA STRATEGY V1 — independent of Three-Candle and Gann
def _MA_strategy_v1_impl(ticker, dateFrom, dateTo, timeframe="5min", verbose=True,
                         require_ema200=False, config=None, show_maslop=False):
    """BUY-only EMA alignment study; no Three-Candle or Gann checks.

    Candidate: completed candle CLOSE > EMA9 > EMA21.
    EMA200 is measured for research, but optional as an entry filter.
    The simulated order is placed at the NEXT candle OPEN, never the
    qualifying candle's close (which was not known beforehand).
    Slopes are percent change of each EMA over the previous 3 bars.
    """
    config = {} if config is None else dict(config)
    accepted = {"ma1_slop", "ma2_slop", "exit_style", "fix_target"}
    unknown = set(config) - accepted
    if unknown:
        raise ValueError(f"Unknown MA config option(s): {sorted(unknown)}")
    ma1_slop = config.get("ma1_slop")
    ma2_slop = config.get("ma2_slop")
    exit_style = str(config.get("exit_style", "trail_1R")).lower()
    if exit_style not in {"trail_1r", "ma9_exit", "fix_target"}:
        raise ValueError("exit_style must be trail_1R, ma9_exit, or fix_target")
    config["exit_style"] = exit_style
    config["fix_target"] = float(config.get("fix_target", 1.2))
    if not (config["fix_target"] > 0):
        raise ValueError("fix_target must be a positive R multiple")
    for name, threshold in (("ma1_slop", ma1_slop), ("ma2_slop", ma2_slop)):
        if threshold is not None:
            try:
                config[name] = float(threshold)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be a number or None") from exc

    data = load_MA_history(ticker, dateFrom, dateTo, timeframe)
    frame = data.copy()
    for span in (9, 21, 200):
        key = f"EMA{span}"
        frame[key] = frame.Close.ewm(span=span, adjust=False).mean()
        frame[f"{key}_slope_pct"] = 100 * (
            frame[key] / frame[key].shift(3) - 1)
        frame[f"{key}_slope_pts"] = frame[key] - frame[key].shift(3)
    # All three EMA lines have at least 600 preceding bars at the first
    # requested candle, even though EMA200 is not an entry requirement.
    bar_count = pd.Series(range(len(frame)), index=frame.index)
    frame["MA_pass"] = ((frame.Close > frame.EMA9) &
                        (frame.EMA9 > frame.EMA21) & (bar_count >= 20))
    if require_ema200:
        frame["MA_pass"] &= ((frame.EMA21 > frame.EMA200) & (bar_count >= 199))
    # Optional slope thresholds are in POINTS over the previous 3 bars.
    # ma1 = EMA9; ma2 = EMA21. No threshold means no slope filter.
    frame["MA_base_pass"] = frame["MA_pass"].copy()
    if ma1_slop is not None:
        frame["MA_pass"] &= frame.EMA9_slope_pts >= config["ma1_slop"]
    if ma2_slop is not None:
        frame["MA_pass"] &= frame.EMA21_slope_pts >= config["ma2_slop"]
    start, end = date.fromisoformat(str(dateFrom)), date.fromisoformat(str(dateTo))
    in_dates = (frame.index.date >= start) & (frame.index.date <= end)
    # Vectorised candidates and next-open entries: no iterrows() loop.
    minutes = data.attrs.get("timeframe_minutes", 5)
    next_time = frame.index.to_series().shift(-1)
    contiguous = (next_time-frame.index.to_series() ==
                  pd.Timedelta(minutes=minutes))
    selected = frame.loc[in_dates & frame.MA_pass & contiguous].copy()
    next_open = frame.Open.shift(-1).reindex(selected.index)
    mean_vol20 = frame.Volume.rolling(20, min_periods=1).mean()
    result = pd.DataFrame(index=selected.index)
    result["Signal"] = range(1, len(selected)+1)
    result["Direction"] = "BUY"
    result["MA_pass"] = True
    result["Signal_time"] = selected.index
    result["Entry_time"] = next_time.reindex(selected.index)
    result["Signal_Close"] = selected.Close
    result["Entry_open"] = next_open
    for name in ("EMA9", "EMA21", "EMA200",
                 "EMA9_slope_pct", "EMA21_slope_pct", "EMA200_slope_pct",
                 "EMA9_slope_pts", "EMA21_slope_pts", "EMA200_slope_pts"):
        result[name] = selected[name]
    result["Close_minus_EMA9"] = selected.Close-selected.EMA9
    result["EMA9_minus_EMA21"] = selected.EMA9-selected.EMA21
    result["EMA21_minus_EMA200"] = selected.EMA21-selected.EMA200
    result["Candle_range_points"] = selected.High-selected.Low
    result["Candle_body_points"] = (selected.Close-selected.Open).abs()
    result["Volume"] = selected.Volume
    result["Volume_ratio_20"] = (selected.Volume /
                                  mean_vol20.reindex(selected.index).replace(0, float("nan")))
    result = result.reset_index(drop=True)
    result.attrs = {
        "candles": frame,
        "requested_start": str(dateFrom),
        "timeframe": normalise_learning_timeframe(timeframe),
        "contract": str(ticker).upper(),
        "strategy": "MA_strategy_v1",
        "require_ema200": bool(require_ema200),
        "ma_warmup_bars": data.attrs.get("ma_warmup_bars", 0),
        "MA_config": config,
        "MA_base_candidates": int((frame.loc[(frame.index.date >= start) &
                                               (frame.index.date <= end),
                                               "MA_base_pass"]).sum()),
    }
    if verbose:
        print(f"MA_strategy_v1 | {ticker} | {dateFrom} to {dateTo} | "
              f"{len(result)} aligned BUY candles")
        print("Rule: Close > EMA9 > EMA21; EMA200 optional; entry next bar OPEN.")
        print(f"EMA warm-up bars before chart: {data.attrs.get('ma_warmup_bars', 0)}")
        print("EMA slopes: 3-candle change in points and percent.")
        print(f"Slope filters (points/3 bars): EMA9 >= {ma1_slop}, "
              f"EMA21 >= {ma2_slop}")
        print(f"Base aligned candidates: {result.attrs['MA_base_candidates']} | "
              f"After slope filter: {len(result)}")
        if not result.empty and not show_maslop:
            from IPython.display import display
            display(result)
    if show_maslop:
        from IPython.display import display
        # Display ALL requested candles, regardless of MA signal pass/fail.
        slope_table = (
            frame.loc[in_dates, ["EMA9_slope_pts", "EMA21_slope_pts"]]
            .rename(columns={"EMA9_slope_pts": "ma1_slop",
                             "EMA21_slope_pts": "ma2_slop"})
            .sort_index()
            .rename_axis("Candle")
            .reset_index()
        )
        display(slope_table)
    return result


def MA_strategy_v1(*args, config=None, **kwargs):
    """Run MA V1. Both old calls and config-first calls are supported.

    Example:
        MA_strategy_v1({"ma1_slop": 2.0, "ma2_slop": 1.0},
                       "MESZ2026", "2026-11-06", "2026-11-06",
                       timeframe="5min")
    """
    if args and isinstance(args[0], dict):
        if config is not None:
            raise ValueError("Provide config once, either first or by keyword")
        config, args = args[0], args[1:]
    return _MA_strategy_v1_impl(*args, config=config, **kwargs)


def summarise_MA_strategy_v1(result, stop_points=6.0, verbose=True, config=None):
    """Non-overlapping long trades with configurable exit style.

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
    settings = dict(result.attrs.get("MA_config", {}))
    if config is not None:
        settings.update(config)
    exit_style = str(settings.get("exit_style", "trail_1R")).lower()
    if exit_style not in {"trail_1r", "ma9_exit", "fix_target"}:
        raise ValueError("exit_style must be trail_1R, ma9_exit, or fix_target")
    target_r = float(settings.get("fix_target", 1.2))
    if target_r <= 0:
        raise ValueError("fix_target must be positive")
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
        exit_reason = "OPEN"
        target_price = entry + target_r * stop_points
        for j in range(entry_idx, len(candles)):
            bar = candles.iloc[j]
            # The protective 1R stop is checked before profit targets.
            if float(bar.Low) <= stop:
                exit_idx = j
                exit_price = min(float(bar.Open), stop)
                exit_reason = "STOP"
                break
            if exit_style == "fix_target" and float(bar.High) >= target_price:
                exit_idx = j
                exit_price = max(float(bar.Open), target_price)
                exit_reason = "FIX_TARGET"
                break
            if exit_style == "ma9_exit":
                # Close-below-EMA9 is known only when this bar completes.
                # Execute at the following candle OPEN, if available.
                if float(bar.Close) < float(bar.EMA9) and j+1 < len(candles):
                    exit_idx = j+1
                    next_open = float(candles.Open.iloc[j+1])
                    # Initial protective stop stays active through next open.
                    exit_price = min(next_open, stop) if next_open <= stop else next_open
                    exit_reason = "MA9_EXIT" if next_open > stop else "STOP"
                    break
            elif exit_style == "trail_1r":
                # Update stepped trail after the bar; effective next candle.
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
            "EMA9_slope_pts": float(signal.EMA9_slope_pts),
            "EMA21_slope_pts": float(signal.EMA21_slope_pts),
            "Points": points, "Return_pct": 100*points/entry,
            "Entry_time": stamp, "Entry": entry,
            "Initial_SL": entry-stop_points, "Final_SL": stop,
            "Exit_time": candles.index[exit_idx] if closed else pd.NaT,
            "Exit": exit_price if closed else float("nan"),
            "Status": "CLOSED" if closed else "OPEN",
            "Max_R_step": max_step, "Exit_reason": exit_reason,
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
    # Keep P/L and drawdown calculated in execution order, then sort the report.
    if not trades.empty:
        trades = trades.sort_values("EMA9_slope_pts", ascending=False).reset_index(drop=True)
    if verbose:
        print(f"\n========== MA STRATEGY V1 — {exit_style.upper()} ==========")
        print(f"Candidates            : {len(result)}")
        print(f"Executed / Closed     : {len(trades)} / {len(closed)}")
        print(f"Wins / Losses / BE    : {wins} / {losses} / {be}")
        print(f"Success rate          : {100*wins/len(closed) if len(closed) else 0:.2f}%")
        print(f"Realised points       : {closed.Points.sum() if not closed.empty else 0.0:+.2f}")
        print(f"Realised return       : {closed.Return_pct.sum() if not closed.empty else 0.0:+.3f}%")
        print(f"Max drawdown          : {drawdown:.2f} points")
        print(f"Rules                 : BUY, close above aligned EMAs; next open entry; "
              f"1R={stop_points:g} points; exit={exit_style}" +
              (f"; target={target_r:g}R" if exit_style == "fix_target" else ""))
        print("OPEN positions excluded from realised statistics; fees/slippage excluded.")
        if not trades.empty:
            from IPython.display import display
            display(trades)
    trades.attrs = result.attrs.copy()
    trades.attrs["exit_style"] = exit_style
    trades.attrs["fix_target"] = target_r
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
                    entry_label, exit_label = False, False
                    for _, t in plotted.iterrows():
                        if t.Entry_time in visible.index:
                            x = int(visible.index.get_loc(t.Entry_time))
                            ax.scatter(x, float(t.Entry), marker="^", s=88,
                                       color="#35e89b", edgecolors="white",
                                       linewidths=.7, zorder=9,
                                       label="BUY entry" if not entry_label else None)
                            entry_label = True
                            ax.annotate(
                                f"9:{float(t.EMA9_slope_pts):+.2f}  "
                                f"21:{float(t.EMA21_slope_pts):+.2f}",
                                xy=(x, float(t.Entry)),
                                xytext=(0, -21), textcoords="offset points",
                                fontsize=7, ha="center", va="top",
                                color="#35e89b", zorder=10,
                                bbox=dict(facecolor="#101722", alpha=.80,
                                          edgecolor="none", pad=1))
                        if t.Status == "CLOSED" and t.Exit_time in visible.index:
                            x2 = int(visible.index.get_loc(t.Exit_time))
                            colour = "#b58cff" if t.Points >= 0 else "#ff6471"
                            ax.scatter(x2, float(t.Exit), marker="v", s=88,
                                       color=colour, edgecolors="white",
                                       linewidths=.7, zorder=9,
                                       label="EXIT" if not exit_label else None)
                            exit_label = True
                            ax.annotate(
                                f"{float(t.Points):+.2f} pt",
                                xy=(x2, float(t.Exit)),
                                xytext=(0, 12), textcoords="offset points",
                                fontsize=8, ha="center", va="bottom",
                                fontweight="bold", color=colour, zorder=10,
                                bbox=dict(facecolor="#101722", alpha=.80,
                                          edgecolor="none", pad=1))
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


def plot_signal_passed_MAs(result, stop_points=6.0, multiChart=False, config=None):
    """Plot executed MA trades with clear entry and exit markers, no trade lines."""
    trades = summarise_MA_strategy_v1(result, stop_points, verbose=False, config=config)
    return _plot_MA_v1(result, trades=trades, multiChart=multiChart,
                       show_entries=True)


# User-friendly aliases for the requested MA method naming.
three_candle_with_MAs = MA_strategy_v1
summarise_signal_result_MAs = summarise_MA_strategy_v1


