"""Rudra Three-Candle LEARNING file (15-minute charts only).

This is an NQ=F extended-futures teaching scanner: it prints C1/C2/C3\nand draws each matching setup.
It does NOT place trades, calculate P&L, or simulate stops.

Install once in VS Code terminal:
    pip install yfinance pandas matplotlib
"""

from datetime import date, timedelta

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd
import yfinance as yf


# 1. SETTINGS: change these while learning
CHECK_VOLUME = False       # True: C3 volume must exceed C2 volume
SHOW_CHARTS = True         # Legacy setting; scanner does not draw charts
MIN_C1_RANGE_PCT = 0.20   # C1 must have at least this high-low range (%)
MIN_C2_RANGE_PCT = 0.25   # C2 must have at least this high-low range (%)


# 2. DOWNLOAD: Yahoo's native 15-minute OHLCV candles
def Download_yfinalce(ticker, datetime, timeframe="15m"):
    """Download ONE date (YYYY-MM-DD) or (start_date, end_date) tuple.

    Dates are inclusive. Returned timestamps are in UK local time.
    Yahoo normally provides 15m intraday data for only recent ~60 days.
    """
    if isinstance(datetime, (tuple, list)):
        date_from, date_to = datetime
    else:
        date_from = date_to = datetime

    start = date.fromisoformat(str(date_from))
    end = date.fromisoformat(str(date_to))
    if end < start:
        raise ValueError("dateTo must be on or after datefrom")
    if ticker != "NQ=F":
        raise ValueError("This learning file is NQ-only: use NQ=F")
    if timeframe not in ("15m", "15min"):
        raise ValueError("Learning version supports 15m only")

    raw = yf.download(
        ticker,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),  # Yahoo end is exclusive
        interval="15m",
        prepost=True,  # include NQ overnight / extended futures session
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if raw.empty:
        raise ValueError("No Yahoo candles. Try a recent date within ~60 days.")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    candles = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    candles = candles.dropna(subset=["Open", "High", "Low", "Close"])
    if candles.index.tz is None:
        raise ValueError("Yahoo did not supply a candle timezone")
    candles.index = candles.index.tz_convert("Europe/London")
    candles = candles.sort_index()
    return candles[~candles.index.duplicated(keep="last")]


# 3. SMALL FILTERS: each is independent so you can change it
def candle_range_pct(candle):
    return (candle.High - candle.Low) / candle.Close * 100


def c2_lower_wick_longer_than_body(c2):
    body = abs(c2.Close - c2.Open)
    lower_wick = min(c2.Open, c2.Close) - c2.Low
    return lower_wick > body


def c2_sweeps_c1_low(c1, c2):
    return c2.Low < c1.Low


def c3_confirms_buy(c2, c3):
    return c3.Close > c3.Open and c3.Close > c2.Close


def c3_volume_higher(c2, c3):
    return pd.notna(c2.Volume) and pd.notna(c3.Volume) and c2.Volume > 0 and c3.Volume > c2.Volume


def passes_three_candle_filters(c1, c2, c3):
    """Simple BUY sweep model. All filters must be True."""
    return (
        candle_range_pct(c1) >= MIN_C1_RANGE_PCT
        and candle_range_pct(c2) >= MIN_C2_RANGE_PCT
        and c2_lower_wick_longer_than_body(c2)
        and c2_sweeps_c1_low(c1, c2)
        and c3_confirms_buy(c2, c3)
        and (not CHECK_VOLUME or c3_volume_higher(c2, c3))
    )


# 4. PRINT ONE CANDLE: easy to compare C1, C2, C3
def print_single_candle(name, time, candle):
    print(
        f"{name} | {time:%Y-%m-%d %H:%M %Z} | "
        f"O={candle.Open:.2f} H={candle.High:.2f} "
        f"L={candle.Low:.2f} C={candle.Close:.2f} "
        f"Vol={candle.Volume:.0f}"
    )


# 5. CHART: exactly 3 candles, with C1/C2/C3 and price references
def show_three_candle_chart(ticker, times, candles):
    fig, ax = plt.subplots(figsize=(7, 4), facecolor="#101722")
    ax.set_facecolor("#101722")
    ax.tick_params(colors="#dbe5f0")
    ax.xaxis.label.set_color("#dbe5f0")
    ax.yaxis.label.set_color("#dbe5f0")
    ax.title.set_color("#f0f5fa")
    for spine in ax.spines.values():
        spine.set_color("#526174")
    for i, (name, candle) in enumerate(zip(("C1", "C2", "C3"), candles)):
        up = candle.Close >= candle.Open
        color = "#23c985" if up else "#ff6471"
        ax.vlines(i, candle.Low, candle.High, color=color, linewidth=1.6)
        bottom = min(candle.Open, candle.Close)
        height = max(abs(candle.Close - candle.Open), 0.00001)
        ax.add_patch(Rectangle((i - 0.25, bottom), 0.5, height,
                               facecolor=color, edgecolor=color))
        ax.annotate(name, (i, candle.High), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=10)

    # These are hypothetical study references, NOT confirmed fills.
    buy_price = float(candles[1].Close)  # C2-close research hypothesis
    sl_price = float(candles[1].Open)    # C2-open reference (may be invalid)
    ax.axhline(buy_price, color="#33e99a", linewidth=1.2,
               label=f"BUY reference (C2 close) {buy_price:.2f}")
    ax.axhline(sl_price, color="#ff6978", linewidth=1.2,
               label=f"SL reference (C2 open) {sl_price:.2f}")

    ax.set_xticks(range(3), [t.strftime("%H:%M") for t in times])
    ax.set_xlim(-0.55, 2.55)
    ax.set_title(f"{ticker} | 15m | {times[2]:%Y-%m-%d} | UK time")
    ax.set_ylabel("Price")
    ax.grid(color="#526174", alpha=0.35)
    ax.legend(fontsize=8, loc="best", facecolor="#1a2534", edgecolor="#526174", labelcolor="white")
    fig.tight_layout()
    plt.show()
    plt.close(fig)



# 5B. EASY NOTEBOOK CHART: pass only your downloaded DataFrame
def plot_chart(df):
    """Draw all candles in df and highlight the most recent qualifying C1/C2/C3.

    Example: learning.plot_chart(df)
    This is a visualization, not a backtest or trading recommendation.
    """
    if df.empty:
        print("Nothing to plot: DataFrame is empty.")
        return

    # Find the most recent 3-candle BUY setup in this DataFrame.
    last_match = None
    step = pd.Timedelta(minutes=15)
    for i in range(2, len(df)):
        times = df.index[i - 2:i + 1]
        if times[1] - times[0] != step or times[2] - times[1] != step:
            continue
        if passes_three_candle_filters(df.iloc[i - 2], df.iloc[i - 1], df.iloc[i]):
            last_match = i

    fig, ax = plt.subplots(figsize=(14, 5), facecolor="#101722")
    ax.set_facecolor("#101722")
    ax.tick_params(colors="#dbe5f0")
    ax.xaxis.label.set_color("#dbe5f0")
    ax.yaxis.label.set_color("#dbe5f0")
    ax.title.set_color("#f0f5fa")
    for spine in ax.spines.values():
        spine.set_color("#526174")
    for i, candle in enumerate(df.itertuples()):
        color = "#23c985" if candle.Close >= candle.Open else "#ff6471"
        ax.vlines(i, candle.Low, candle.High, color=color, linewidth=0.8)
        body_bottom = min(candle.Open, candle.Close)
        body_height = max(abs(candle.Close - candle.Open), 0.00001)
        ax.add_patch(Rectangle((i - 0.3, body_bottom), 0.6, body_height,
                               color=color, alpha=0.8))

    if last_match is not None:
        # Label C1/C2/C3 for the latest matching setup.
        for offset, label in zip((-2, -1, 0), ("C1", "C2", "C3")):
            pos = last_match + offset
            ax.annotate(label, (pos, df.iloc[pos].High),
                        xytext=(0, 10), textcoords="offset points",
                        ha="center", color="#77bcff", weight="bold")
        c2 = df.iloc[last_match - 1]
        ax.axhline(c2.Close, color="#33e99a", linestyle="--",
                   label=f"BUY reference (C2 close) {c2.Close:.2f}")
        ax.axhline(c2.Open, color="#ff6978", linestyle="--",
                   label=f"SL reference (C2 open) {c2.Open:.2f}")
        ax.legend(loc="best", facecolor="#1a2534", edgecolor="#526174", labelcolor="white")
    else:
        print("No qualifying BUY setup in this DataFrame; showing all candles.")

    # Reduce tick labels when many candles are displayed.
    every = max(1, len(df) // 12)
    positions = list(range(0, len(df), every))
    ax.set_xticks(positions, [df.index[j].strftime("%d %b %H:%M") for j in positions],
                  rotation=35, ha="right")
    ax.set_xlim(-1, len(df))
    ax.set_ylabel("NQ futures price")
    ax.set_title("NQ=F | 15-minute candles | UK time")
    ax.grid(color="#526174", alpha=0.35)
    fig.tight_layout()
    plt.show()
    plt.close(fig)


# 6. MAIN LOOP: scan candles and RETURN signals (no charts)
def three_candle_signal_learning(tiker, datefrom, dateTo):
    """Return one DataFrame row per BUY setup. No charts or backtesting."""
    if tiker != "NQ=F":
        raise ValueError("NQ-only learning version: ticker must be NQ=F")

    data = Download_yfinalce(tiker, (datefrom, dateTo), "15m")
    print(f"Downloaded {len(data)} x 15m candles for {tiker}")
    signals = []
    step = pd.Timedelta(minutes=15)

    for i in range(2, len(data)):
        times = list(data.index[i - 2:i + 1])
        c1, c2, c3 = [data.iloc[j] for j in (i - 2, i - 1, i)]

        # Skip missing bars and session gaps.
        if times[1] - times[0] != step or times[2] - times[1] != step:
            continue
        if not passes_three_candle_filters(c1, c2, c3):
            continue

        # Keep each candle's OHLCV so plotting needs only 'result'.
        row = {"Ticker": tiker, "Direction": "BUY",
               "BUY": float(c2.Close), "SL": float(c2.Open)}
        for label, time, candle in zip(("C1", "C2", "C3"), times, (c1, c2, c3)):
            row[f"{label}_time"] = time
            for field in ("Open", "High", "Low", "Close", "Volume"):
                row[f"{label}_{field}"] = float(candle[field])
        signals.append(row)

    result = pd.DataFrame(signals)
    print(f"Found {len(result)} BUY setups (study references only).")
    return result


# 7. PLOT SIGNALS: plot only when called separately
def plot_signal(result):
    """Display a separate C1/C2/C3 chart for every row of a scan result."""
    if result is None or result.empty:
        print("No signals to plot.")
        return

    for number, row in result.iterrows():
        times = [row[f"C{n}_time"] for n in (1, 2, 3)]
        candles = [
            pd.Series({field: row[f"C{n}_{field}"]
                       for field in ("Open", "High", "Low", "Close", "Volume")})
            for n in (1, 2, 3)
        ]
        print(f"Setup {number + 1}/{len(result)} | BUY {row['BUY']:.2f} | SL {row['SL']:.2f}")
        show_three_candle_chart(row["Ticker"], times, candles)


# 8. RUN DIRECTLY IN VS CODE (or import from your notebook)
if __name__ == "__main__":
    three_candle_signal_learning("NQ=F", "2026-10-29", "2026-10-30")
