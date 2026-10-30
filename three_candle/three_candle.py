"""Rudra Three-Candle: transparent NQ=F 15-minute signal research.

This module identifies *setups*, not executable fills or profit results.
Every filter is independent so its definition can be reviewed or changed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class Signal:
    time: pd.Timestamp
    direction: str
    candle1_time: pd.Timestamp
    candle2_time: pd.Timestamp
    candle3_time: pd.Timestamp
    candle2_high: float
    candle2_low: float
    candle2_open: float
    candle2_close: float
    candle3_volume: float
    candle2_volume: float


def download_nq(start: str, end: str, interval: str = "15m") -> pd.DataFrame:
    """Download inclusive calendar dates; return UK-localized OHLCV candles.

    Yahoo typically limits 15-minute history to about 60 days. Yahoo futures
    volume can be incomplete; validate it before interpreting volume filters.
    """
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)
    if last < first:
        raise ValueError("end must be on/after start")
    # Query exactly the requested dates. Yahoo's 'end' is exclusive.
    raw = yf.download(
        "NQ=F", start=first.isoformat(),
        end=(last + timedelta(days=1)).isoformat(),
        interval=interval, auto_adjust=False, progress=False,
        prepost=True, threads=False,
    )
    if raw.empty:
        raise ValueError("No Yahoo candles returned. Check dates, symbol, and 15m retention limit.")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    raw = raw.dropna(subset=["Open", "High", "Low", "Close"])
    if raw.index.tz is None:
        raise ValueError("Yahoo returned timezone-naive timestamps: cannot safely label candle times")
    raw.index = raw.index.tz_convert("Europe/London")
    raw = raw.sort_index()
    # Date boundaries are interpreted in UK calendar dates.
    dates = pd.Index(raw.index.date)
    return raw.loc[(dates >= first) & (dates <= last)]


def candle_is_bullish(candle: pd.Series) -> bool:
    """Direction filter: green candle 2."""
    return float(candle.Close) > float(candle.Open)


def candle2_wick_exceeds_body(candle: pd.Series) -> bool:
    """Original broad wick filter: either wick longer than candle 2 body."""
    body = abs(float(candle.Close) - float(candle.Open))
    upper = float(candle.High) - max(float(candle.Open), float(candle.Close))
    lower = min(float(candle.Open), float(candle.Close)) - float(candle.Low)
    return max(upper, lower) > body


def candle3_volume_increases(candle2: pd.Series, candle3: pd.Series) -> bool:
    """Candle 3 volume must strictly exceed candle 2; zero/missing fails."""
    return (pd.notna(candle2.Volume) and pd.notna(candle3.Volume)
            and float(candle2.Volume) > 0
            and float(candle3.Volume) > float(candle2.Volume))


def candle3_breaks_candle2_high(candle2: pd.Series, candle3: pd.Series) -> bool:
    """Optional confirmation: candle 3 traded above candle 2's high."""
    return float(candle3.High) > float(candle2.High)


def check_three_candle(c1: pd.Series, c2: pd.Series, c3: pd.Series,
                       require_breakout: bool = False) -> bool:
    """Single readable decision point; edit/disable each filter here."""
    if not candle_is_bullish(c2):
        return False
    if not candle2_wick_exceeds_body(c2):
        return False
    if not candle3_volume_increases(c2, c3):
        return False
    if require_breakout and not candle3_breaks_candle2_high(c2, c3):
        return False
    return True


def find_signals(data: pd.DataFrame, require_breakout: bool = False):
    """Yield each setup chronologically, using completed candles only."""
    for i in range(2, len(data)):
        c1, c2, c3 = data.iloc[i-2], data.iloc[i-1], data.iloc[i]
        if not check_three_candle(c1, c2, c3, require_breakout):
            continue
        yield Signal(
            time=data.index[i], direction="LONG", candle1_time=data.index[i-2],
            candle2_time=data.index[i-1], candle3_time=data.index[i],
            candle2_high=float(c2.High), candle2_low=float(c2.Low),
            candle2_open=float(c2.Open), candle2_close=float(c2.Close),
            candle3_volume=float(c3.Volume), candle2_volume=float(c2.Volume),
        )


def print_signal(signal: Signal, data: pd.DataFrame) -> None:
    """Print all three input candles and candidate levels for human review."""
    print(f"\nSIGNAL {signal.direction} | candle 3 closed {signal.time:%Y-%m-%d %H:%M %Z}")
    print(data.loc[[signal.candle1_time, signal.candle2_time, signal.candle3_time]].to_string())
    print(f"Candidate breakout > {signal.candle2_high:.2f} | "
          f"C2 open reference SL {signal.candle2_open:.2f} | "
          f"C3/C2 volume {signal.candle3_volume / signal.candle2_volume:.2f}x")
    print("Research setup only: no entry/fill is assumed at candle 2 close.")


def plot_signal(signal: Signal, data: pd.DataFrame, before: int = 12,
                after: int = 8):
    """Plot nearby candles, highlight C1/C2/C3, return matplotlib figure."""
    idx = data.index.get_loc(signal.candle3_time)
    left, right = max(0, idx-before), min(len(data), idx+after+1)
    view = data.iloc[left:right]
    fig, (ax, vol) = plt.subplots(2, 1, figsize=(13, 6), sharex=True,
                                   gridspec_kw={"height_ratios": [4, 1]})
    for x, (_, row) in enumerate(view.iterrows()):
        up = row.Close >= row.Open
        color = "#168650" if up else "#c64242"
        ax.vlines(x, row.Low, row.High, color=color, linewidth=1.2)
        ax.add_patch(Rectangle((x-0.32, min(row.Open, row.Close)), 0.64,
                               max(abs(row.Close-row.Open), 0.01),
                               facecolor=color, edgecolor=color))
        vol.bar(x, row.Volume, color=color, width=0.7)
    for label, timestamp, color in [
        ("C1", signal.candle1_time, "#4c78a8"),
        ("C2", signal.candle2_time, "#e1a536"),
        ("C3", signal.candle3_time, "#7b58a5"),
    ]:
        x = view.index.get_loc(timestamp)
        ax.axvspan(x-0.48, x+0.48, color=color, alpha=0.15)
        ax.annotate(label, (x, float(view.iloc[x].High)), xytext=(0, 8),
                    textcoords="offset points", ha="center", color=color,
                    weight="bold")
    ax.axhline(signal.candle2_high, color="blue", linestyle="--", alpha=0.6,
               label=f"C2 high {signal.candle2_high:.2f}")
    ax.axhline(signal.candle2_open, color="orange", linestyle=":", alpha=0.7,
               label=f"C2 open {signal.candle2_open:.2f}")
    ax.legend(loc="best")
    ax.set_title(f"NQ=F 15m | Setup confirmed at {signal.time:%Y-%m-%d %H:%M %Z}")
    ax.set_ylabel("Price")
    vol.set_ylabel("Volume")
    ticks = list(range(0, len(view), max(1, len(view)//8)))
    vol.set_xticks(ticks, [view.index[i].strftime("%d %b %H:%M") for i in ticks],
                   rotation=35, ha="right")
    fig.tight_layout()
    return fig


def run(start: str, end: str, show_charts: bool = True,
        require_breakout: bool = False, limit: int | None = None):
    """Download, find, print and optionally plot signals one-by-one."""
    data = download_nq(start, end)
    print(f"NQ=F | {len(data)} 15m candles | {start} to {end} (UK dates)")
    count = 0
    for signal in find_signals(data, require_breakout=require_breakout):
        count += 1
        print_signal(signal, data)
        if show_charts:
            fig = plot_signal(signal, data)
            plt.show()
            plt.close(fig)
        if limit is not None and count >= limit:
            break
    print(f"\nTotal setups shown: {count}")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD, UK calendar")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--no-charts", action="store_true")
    parser.add_argument("--require-breakout", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(args.start, args.end, show_charts=not args.no_charts,
        require_breakout=args.require_breakout, limit=args.limit)
