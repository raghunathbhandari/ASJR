"""Rudra Three-Candle LEARNING file (15-minute charts only).

This is an NQ=F extended-futures teaching scanner: it prints C1/C2/C3\nand draws each matching setup.
It does NOT place trades, calculate P&L, or simulate stops.

Install once in VS Code terminal:
    pip install yfinance pandas matplotlib
"""

from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd
import yfinance as yf


# 1. SETTINGS: change these while learning
CHECK_VOLUME = False       # True: C3 volume must exceed C2 volume
SHOW_CHARTS = True         # Legacy setting; scanner does not draw charts
MIN_C1_RANGE_PCT = 0.20   # C1 must have at least this high-low range (%)
MIN_C2_RANGE_PCT = 0.25   # C2 must have at least this high-low range (%)
PRINT_FILTER_DETAILS = True  # Print PASS/FAIL for each 3-candle window


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
    if ticker not in ("NQ=F", "GC=F"):
        raise ValueError("Use NQ=F or GC=F")
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


# 2B. READ IBKR CSV FIRST; FALL BACK TO YAHOO IF MONTHLY FILES ARE ABSENT
def load_learning_candles(ticker, datefrom, dateTo):
    """Build exact 15m bars from local IBKR 5m CSVs, or download Yahoo 15m."""
    start = date.fromisoformat(str(datefrom))
    end = date.fromisoformat(str(dateTo))
    if end < start:
        raise ValueError("dateTo before datefrom")
    if ticker not in ("NQ=F", "GC=F"):
        raise ValueError("Use NQ=F or GC=F")

    prefix = "NQ" if ticker == "NQ=F" else "GC"
    folder = Path(__file__).resolve().parent / "data"
    files = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        files.append(folder / f"{prefix}Z2026_IBKR_5m_{year}-{month:02d}.csv")
        month += 1
        if month == 13:
            month, year = 1, year + 1

    if not all(path.is_file() for path in files):
        print("IBKR CSV missing; using Yahoo instead:",
              ", ".join(p.name for p in files if not p.is_file()))
        # Yahoo also needs earlier candles to warm up MA20 and MA200.
        earlier = (start - timedelta(days=12)).isoformat()
        yahoo = Download_yfinalce(ticker, (earlier, dateTo), "15m")
        requested = yahoo.index.date >= start
        if not requested.any():
            raise ValueError("No Yahoo candles within requested dates")
        first = int(requested.argmax())
        return yahoo.iloc[max(0, first - 200):]

    # Optional previous-month CSV supplies warmup when requested period
    # starts at the beginning of a month.
    previous = start.replace(day=1) - timedelta(days=1)
    previous_file = folder / f"{prefix}Z2026_IBKR_5m_{previous.year}-{previous.month:02d}.csv"
    if previous_file.is_file() and previous_file not in files:
        files.insert(0, previous_file)

    raw = pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
    needed = ["Datetime_UTC", "Open", "High", "Low", "Close", "Volume"]
    if not set(needed).issubset(raw.columns):
        raise ValueError("IBKR CSV columns incomplete; not mixing data vendors")
    raw["Datetime_UTC"] = pd.to_datetime(raw["Datetime_UTC"], utc=True)
    for col in needed[1:]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    raw = raw.dropna(subset=needed).sort_values("Datetime_UTC")
    raw = raw.drop_duplicates("Datetime_UTC").set_index("Datetime_UTC")

    bad = ((raw.High < raw[["Open", "Close", "Low"]].max(axis=1))
           | (raw.Low > raw[["Open", "Close", "High"]].min(axis=1))
           | ((raw.High - raw.Low) / raw.Close > 0.02))
    if bad.any():
        print(f"WARNING: excluded {int(bad.sum())} suspicious 5m IBKR bars")
        raw = raw.loc[~bad]

    # Each 15m candle MUST contain exactly 3 aligned 5m timestamps.
    candles = []
    for stamp, group in raw.groupby(raw.index.floor("15min")):
        expected = [stamp + pd.Timedelta(minutes=n) for n in (0, 5, 10)]
        if list(group.index) != expected:
            continue
        candles.append((stamp, group.Open.iloc[0], group.High.max(),
                        group.Low.min(), group.Close.iloc[-1], group.Volume.sum()))
    if not candles:
        raise ValueError("IBKR files exist but no complete 15m bars")
    data = pd.DataFrame(candles, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
    data = data.set_index("Time")
    data.index = data.index.tz_convert("Europe/London")
    # Keep 200 preceding bars for MA20/MA200, but do not count them as signals.
    requested = (data.index.date >= start) & (data.index.date <= end)
    if not requested.any():
        raise ValueError("No complete IBKR 15m bars for requested dates")
    first = int(requested.argmax())
    data = data.iloc[max(0, first - 200):]
    data = data.loc[data.index.date <= end]
    if first < 200:
        print("MA200 WARNING: fewer than 200 earlier bars available")
    if data.empty:
        raise ValueError("No complete IBKR 15m bars for requested dates")
    print(f"Using IBKR CSV: {len(data)} complete 15m bars from {len(files)} file(s)")
    return data


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


# 3B. CORE TURNING PATTERN (BUY only)
def three_candle_core(c1, c2, c3):
    """C2 sweeps C1 low, then C3 high breaks C2 BODY top (not C2 high).

    No wick, candle-range, volume, or C3 colour filters are applied.
    """
    return bool(c2.Low < c1.Low and c3.High > max(c2.Open, c2.Close))


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
    """Return all core BUY candidates with each extra filter result."""
    if tiker not in ("NQ=F", "GC=F"):
        raise ValueError("Use NQ=F or GC=F")

    data = load_learning_candles(tiker, datefrom, dateTo)
    print(f"Downloaded {len(data)} x 15m candles for {tiker}")
    signals = []
    step = pd.Timedelta(minutes=15)

    for i in range(2, len(data)):
        times = list(data.index[i - 2:i + 1])
        c1, c2, c3 = [data.iloc[j] for j in (i - 2, i - 1, i)]

        # Only consecutive 15m candles can form a pattern.
        if times[1] - times[0] != step or times[2] - times[1] != step:
            continue

        # Warmup candles are chart-only, not new signal candidates.
        if times[2].date() < date.fromisoformat(str(datefrom)):
            continue

        # STEP 1: core turning-point detection.
        if not three_candle_core(c1, c2, c3):
            continue

        # STEP 2: inspect extra filters, without rejecting core candidates.
        checks = {
            "c1_range_pct": candle_range_pct(c1) >= MIN_C1_RANGE_PCT,
            "c2_range_pct": candle_range_pct(c2) >= MIN_C2_RANGE_PCT,
            "c2_lower_wick_longer_than_body": c2_lower_wick_longer_than_body(c2),
            "c2_sweeps_c1_low": c2_sweeps_c1_low(c1, c2),
            "c3_confirms_buy": c3_confirms_buy(c2, c3),
            "c3_volume_higher": c3_volume_higher(c2, c3),
        }
        passed = all(value for name, value in checks.items()
                     if name != "c3_volume_higher" or CHECK_VOLUME)
        number = len(signals) + 1
        if PRINT_FILTER_DETAILS:
            print(f"\nCandidate {number} | C3 {times[2]:%Y-%m-%d %H:%M %Z} "
                  f"| CORE=True | Extra filters={passed}")
            for name, ok in checks.items():
                note = " (optional OFF)" if name == "c3_volume_higher" and not CHECK_VOLUME else ""
                print(f"  {name} = {ok}{note}")

        row = {"Ticker": tiker, "Direction": "BUY",
               "BUY": float(c2.Close), "SL": float(c2.Open),
               "core_match": True, "all_filters_pass": passed}
        row.update(checks)
        for label, time, candle in zip(("C1", "C2", "C3"), times, (c1, c2, c3)):
            row[f"{label}_time"] = time
            for field in ("Open", "High", "Low", "Close", "Volume"):
                row[f"{label}_{field}"] = float(candle[field])
        signals.append(row)

    result = pd.DataFrame(signals)
    result.attrs["candles"] = data  # Includes preceding MA20 warm-up bars.
    result.attrs["requested_start"] = str(datefrom)
    passed_count = int(result["all_filters_pass"].sum()) if not result.empty else 0
    print(f"\nFound {len(result)} core candidates; {passed_count} pass extra filters.")

    # Print passing setups at the END, after all candidate diagnostics.
    print("\n========== PASSED CANDIDATES ==========")
    if passed_count == 0:
        print("None")
    else:
        for index, row in result[result["all_filters_pass"]].iterrows():
            print(f"Candidate {index + 1} | C3 {row['C3_time']:%Y-%m-%d %H:%M %Z}"
                  f" | BUY {row['BUY']:.2f} | SL {row['SL']:.2f}")
            for name in ("c1_range_pct", "c2_range_pct",
                         "c2_lower_wick_longer_than_body", "c2_sweeps_c1_low",
                         "c3_confirms_buy", "c3_volume_higher"):
                suffix = " (optional OFF)" if name == "c3_volume_higher" and not CHECK_VOLUME else ""
                print(f"  {name} = {bool(row[name])}{suffix}")
    return result


# Build MA20 on the complete dataset; display only requested dates.
def chart_data_and_mas(result):
    """Compute MA20 and MA200 with hidden historical candles before chart start."""
    full_data = result.attrs.get("candles")
    if full_data is None or full_data.empty:
        raise ValueError("Full candles unavailable. Rerun the scanner.")
    ma20 = full_data.Close.rolling(20, min_periods=20).mean()
    ma200 = full_data.Close.rolling(200, min_periods=200).mean()
    start = result.attrs.get("requested_start")
    if start is None:
        return full_data, ma20, ma200
    visible = full_data.loc[full_data.index.date >= date.fromisoformat(start)]
    if visible.empty:
        raise ValueError("No candles in requested date range")
    return visible, ma20.reindex(visible.index), ma200.reindex(visible.index)


# 7. PLOT SIGNALS: plot only when called separately
def plot_signal(result, show_sr=False):
    """Show the FULL downloaded NQ candle chart for EACH matching signal."""
    if result is None or result.empty:
        print("No signals to plot.")
        return

    data, ma20, ma200 = chart_data_and_mas(result)

    for number, row in result.iterrows():
        print(f"\\n=== NQ BUY SIGNAL {number + 1}/{len(result)} ===")
        for label in ("C1", "C2", "C3"):
            print(
                f"{label} | {row[f'{label}_time']:%Y-%m-%d %H:%M %Z} | "
                f"O={row[f'{label}_Open']:.2f} "
                f"H={row[f'{label}_High']:.2f} "
                f"L={row[f'{label}_Low']:.2f} "
                f"C={row[f'{label}_Close']:.2f} "
                f"Vol={row[f'{label}_Volume']:.0f}"
            )
        print(f"BUY reference: {row['BUY']:.2f} | SL reference: {row['SL']:.2f}")
        fig, ax = plt.subplots(figsize=(16, 6), facecolor="#101722")
        ax.set_facecolor("#101722")

        # Draw the full downloaded range, not just 3 isolated candles.
        for i, candle in enumerate(data.itertuples()):
            color = "#23c985" if candle.Close >= candle.Open else "#ff6471"
            ax.vlines(i, candle.Low, candle.High, color=color, linewidth=0.8)
            ax.add_patch(Rectangle(
                (i - 0.3, min(candle.Open, candle.Close)),
                0.6, max(abs(candle.Close - candle.Open), 0.00001),
                facecolor=color, edgecolor=color,
            ))

        # Highlight THIS signal's three candles on the full chart.
        for label in ("C1", "C2", "C3"):
            candle_time = row[f"{label}_time"]
            if candle_time not in data.index:
                continue  # C1/C2 may be just before requested chart start.
            pos = data.index.get_loc(candle_time)
            ax.axvspan(pos - 0.45, pos + 0.45, color="#77bcff", alpha=0.13)
            ax.annotate(label, (pos, data.iloc[pos].High),
                        xytext=(0, 9), textcoords="offset points",
                        ha="center", color="#a4d1ff", weight="bold")

        # Only draw BUY and SL lines from C2 through the chart's right edge.
        c2_position = data.index.get_loc(row["C2_time"]) if row["C2_time"] in data.index else 0
        ax.hlines(row["BUY"], c2_position, len(data) - 0.5,
                  color="#33e99a", linewidth=1.3,
                  label=f"BUY reference {row['BUY']:.2f}")
        ax.hlines(row["SL"], c2_position, len(data) - 0.5,
                  color="#ff6978", linewidth=1.3,
                  label=f"SL reference {row['SL']:.2f}")

        # Add confirmed swing S/R only when requested (passed-signal charts).
        if show_sr:
            for kind, pivot, confirmed_at, price in detect_swing_levels(data, left=2, right=2):
                level_color = "#56c4f5" if kind == "SUPPORT" else "#ff7979"
                # Short segment centred on the actual swing candle.
                x1 = max(0, pivot - 2)
                x2 = min(len(data) - 0.5, pivot + 2.5)
                ax.hlines(price, x1, x2, color=level_color,
                          linewidth=2.0, alpha=0.95)

        every = max(1, len(data) // 15)
        ticks = list(range(0, len(data), every))
        ax.set_xticks(ticks, [data.index[j].strftime("%d %b %H:%M") for j in ticks],
                      rotation=35, ha="right")
        ax.plot(range(len(data)), ma20, color="#f7c65c", linewidth=1.5,
                label="MA20 (15m close)", zorder=4)
        ax.plot(range(len(data)), ma200, color="#b58cff", linewidth=1.6,
                label="MA200 (15m close)", zorder=4)
        ax.set_xlim(-1, len(data))
        ax.set_ylabel("NQ futures price", color="#dbe5f0")
        ax.set_title(f"NQ=F | 15m full chart | Signal {number + 1}/{len(result)} | UK time",
                     color="#f0f5fa")
        ax.tick_params(colors="#dbe5f0")
        for spine in ax.spines.values():
            spine.set_color("#526174")
        ax.grid(color="#526174", alpha=0.35)
        ax.legend(loc="best", facecolor="#1a2534",
                  edgecolor="#526174", labelcolor="white")
        fig.tight_layout()
        plt.show()
        plt.close(fig)


# 8. CHART ONLY FULLY PASSED SIGNALS (one chart per signal)
def plot_signal_passed(result):
    """Draw one full-price-history chart for each candidate passing extra filters."""
    if result is None or result.empty:
        print("No candidates to plot.")
        return
    passed = result.loc[result["all_filters_pass"]].copy()
    passed.attrs["candles"] = result.attrs.get("candles")
    passed.attrs["requested_start"] = result.attrs.get("requested_start")
    if passed.empty:
        print("No candidates passed all enabled extra filters.")
        return
    # Preserve original candidate numbers in printed headings / chart titles.
    plot_signal(passed, show_sr=True)


# 9. CHART ALL CORE CANDIDATES (one chart, direction-coloured C2 dots)
def plot_signal_candidate(result):
    """Show NQ once: green C2 dots for BUY, red C2 dots for SELL."""
    if result is None:
        print("No result supplied.")
        return
    data, ma20, ma200 = chart_data_and_mas(result)

    fig, ax = plt.subplots(figsize=(20, 9), facecolor="#101722")
    ax.set_facecolor("#101722")

    # Full 15m OHLC candles.
    for i, candle in enumerate(data.itertuples()):
        color = "#23c985" if candle.Close >= candle.Open else "#ff6471"
        ax.vlines(i, candle.Low, candle.High, color=color, linewidth=0.8)
        ax.add_patch(Rectangle(
            (i - 0.3, min(candle.Open, candle.Close)),
            0.6, max(abs(candle.Close - candle.Open), 0.00001),
            facecolor=color, edgecolor=color,
        ))

    # Direction-coloured markers identify C2 (the sweep candle), not C3.
    for _, row in result.iterrows():
        if row["C2_time"] not in data.index:
            continue
        pos = data.index.get_loc(row["C2_time"])
        # BUY = green dot below C2; SELL = red dot above C2.
        direction = str(row["Direction"]).upper()
        dot_color = "#23c985" if direction == "BUY" else "#ff6471"
        dot_price = row["C2_Low"] if direction == "BUY" else row["C2_High"]
        ax.scatter(pos, dot_price, color=dot_color, s=65,
                   edgecolors="#ffffff", linewidths=0.6, zorder=6)

    # Short local S/R segments at each confirmed swing (not full-width lines).
    for kind, pivot, confirmed_at, price in detect_swing_levels(data, left=2, right=2):
        level_color = "#56c4f5" if kind == "SUPPORT" else "#ff7979"
        x1 = max(0, pivot - 2)
        x2 = min(len(data) - 0.5, pivot + 2.5)
        ax.hlines(price, x1, x2, color=level_color, linewidth=2.0,
                  alpha=0.95, zorder=5)

    every = max(1, len(data) // 15)
    ticks = list(range(0, len(data), every))
    ax.set_xticks(ticks, [data.index[j].strftime("%d %b %H:%M") for j in ticks],
                  rotation=35, ha="right")
    ax.plot(range(len(data)), ma20, color="#f7c65c", linewidth=1.5,
            label="MA20 (15m close)", zorder=4)
    ax.plot(range(len(data)), ma200, color="#b58cff", linewidth=1.6,
                label="MA200 (15m close)", zorder=4)
    ax.legend(loc="best", facecolor="#1a2534", edgecolor="#526174", labelcolor="white")
    ax.set_xlim(-1, len(data))
    ax.set_ylabel("NQ futures price", color="#dbe5f0")
    ax.set_title(f"NQ=F | 15m | {len(result)} core candidate C2 markers | UK time",
                 color="#f0f5fa")
    ax.tick_params(colors="#dbe5f0")
    for spine in ax.spines.values():
        spine.set_color("#526174")
    ax.grid(color="#526174", alpha=0.35)
    fig.tight_layout()
    plt.show()
    plt.close(fig)


# 10. SWING HIGH / LOW SUPPORT AND RESISTANCE RESEARCH
def detect_swing_levels(data, left=2, right=2):
    """Return confirmed swing highs/lows using neighbouring candles.

    A HIGH must exceed highs of 'left' earlier and 'right' later bars.
    A LOW must be below lows of those bars. A pivot becomes KNOWN only
    after the right-side candles close (no early/future signal).
    """
    levels = []
    for i in range(left, len(data) - right):
        high = float(data.High.iloc[i])
        low = float(data.Low.iloc[i])
        before = data.iloc[i-left:i]
        after = data.iloc[i+1:i+1+right]
        if high > before.High.max() and high > after.High.max():
            levels.append(("RESISTANCE", i, i + right, high))
        if low < before.Low.min() and low < after.Low.min():
            levels.append(("SUPPORT", i, i + right, low))
    return levels


def plot_swing_levels(result, left=2, right=2):
    """One full 15m chart with MA20 and horizontal swing S/R levels.

    Example: learning.plot_swing_levels(result)
    Increase left/right for fewer, more important levels.
    """
    if result is None:
        print("No scan result supplied.")
        return
    data, ma20, ma200 = chart_data_and_mas(result)
    levels = detect_swing_levels(data, left=left, right=right)

    fig, ax = plt.subplots(figsize=(20, 9), facecolor="#101722")
    ax.set_facecolor("#101722")
    for i, candle in enumerate(data.itertuples()):
        color = "#23c985" if candle.Close >= candle.Open else "#ff6471"
        ax.vlines(i, candle.Low, candle.High, color=color, linewidth=0.8)
        ax.add_patch(Rectangle(
            (i - 0.3, min(candle.Open, candle.Close)),
            0.6, max(abs(candle.Close - candle.Open), 0.00001),
            facecolor=color, edgecolor=color,
        ))
    ax.plot(range(len(data)), ma20, color="#f7c65c",
            linewidth=1.5, label="MA20 (15m close)")
    ax.plot(range(len(data)), ma200, color="#b58cff",
            linewidth=1.6, label="MA200 (15m close)")

    support_count = 0
    resistance_count = 0
    for kind, pivot, confirmed_at, price in levels:
        # Plot only AFTER confirmation to avoid visual lookahead.
        color = "#56c4f5" if kind == "SUPPORT" else "#ff7979"
        ax.hlines(price, confirmed_at, len(data)-0.5, color=color,
                  linewidth=1.1, alpha=0.78, linestyle="--")
        ax.scatter(pivot, price, s=34, color=color, zorder=6)
        if kind == "SUPPORT":
            support_count += 1
        else:
            resistance_count += 1

    every = max(1, len(data) // 15)
    ticks = list(range(0, len(data), every))
    ax.set_xticks(ticks, [data.index[j].strftime("%d %b %H:%M") for j in ticks],
                  rotation=35, ha="right")
    ax.set_xlim(-1, len(data))
    ax.set_ylabel("Futures price", color="#dbe5f0")
    ax.set_title(f"15m swing S/R | Support {support_count} | Resistance {resistance_count} | UK time",
                 color="#f0f5fa")
    ax.tick_params(colors="#dbe5f0")
    for spine in ax.spines.values():
        spine.set_color("#526174")
    ax.grid(color="#526174", alpha=0.35)
    ax.legend(loc="best", facecolor="#1a2534", edgecolor="#526174", labelcolor="white")
    fig.tight_layout()
    plt.show()
    plt.close(fig)
    print(f"Swing S/R: {support_count} support and {resistance_count} resistance levels")


# 11. RUN DIRECTLY IN VS CODE (or import from your notebook)
if __name__ == "__main__":
    three_candle_signal_learning("NQ=F", "2026-10-29", "2026-10-30")
