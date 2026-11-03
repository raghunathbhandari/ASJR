"""Rudra ThreeCandl-V3 LEARNING file (15-minute charts only).

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
    if ticker not in ("NQ=F", "GC=F", "MES=F"):
        raise ValueError("Use NQ=F, GC=F, or MES=F")
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
    if ticker not in ("NQ=F", "GC=F", "MES=F"):
        raise ValueError("Use NQ=F, GC=F, or MES=F")

    prefix = {"NQ=F": "NQ", "GC=F": "GC", "MES=F": "MES"}[ticker]
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
        # Yahoo also needs earlier candles to warm up EMA20 and EMA200.
        earlier = (start - timedelta(days=24)).isoformat()
        yahoo = Download_yfinalce(ticker, (earlier, dateTo), "15m")
        requested = yahoo.index.date >= start
        if not requested.any():
            raise ValueError("No Yahoo candles within requested dates")
        first = int(requested.argmax())
        return yahoo.iloc[max(0, first - 1000):]

    # Optional previous-month CSV supplies EMA warmup when requested period
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
    # Keep up to 1000 preceding bars for EMA20/EMA200, but do not count them as signals.
    requested = (data.index.date >= start) & (data.index.date <= end)
    if not requested.any():
        raise ValueError("No complete IBKR 15m bars for requested dates")
    first = int(requested.argmax())
    data = data.iloc[max(0, first - 200):]
    data = data.loc[data.index.date <= end]
    if first < 1000:
        print("EMA200 NOTICE: fewer than 1000 earlier bars; value may differ from TradingView")
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


# 3B. CORE DETECTION — only candle geometry; NO extra filters
def three_candle_core(c1, c2, c3, direction="BUY"):
    """C2 sweeps C1; a later C3 breaks C2's BODY boundary (not wick)."""
    if direction == "BUY":
        return bool(c2.Low < c1.Low and c3.High > max(c2.Open, c2.Close))
    if direction == "SELL":
        return bool(c2.High > c1.High and c3.Low < min(c2.Open, c2.Close))
    raise ValueError("direction must be BUY or SELL")


def scan_core_candidates(data):
    """State machine: C1 -> exactly ONE C2 sweep -> wait for C3.

    - C1 stays fixed while subsequent candles are inside its range.
    - C2 is a single candle sweeping C1 low (BUY) or high (SELL).
    - Any later candle can be C3 if it crosses C2's body boundary.
    - If a waiting candle breaks C2's sweep extreme, reset with it as C1.
    - If a candle both breaks the extreme and confirms, reset first:
      15m OHLC cannot tell which event occurred first.
    - Reset at missing 15m timestamps; never connect across gaps.
    - On confirmation use that C3 as the next C1.
    """
    step = pd.Timedelta(minutes=15)
    c1_i = None
    c2_i = None
    side = None

    for i in range(len(data)):
        if i and data.index[i] - data.index[i - 1] != step:
            c1_i, c2_i, side = None, None, None
        if c1_i is None:
            c1_i = i
            continue

        candle = data.iloc[i]
        c1 = data.iloc[c1_i]

        if c2_i is None:
            sweep_low = candle.Low < c1.Low
            sweep_high = candle.High > c1.High
            if sweep_low and sweep_high:
                c1_i = i            # Ambiguous two-sided sweep
            elif sweep_low or sweep_high:
                c2_i = i
                side = "BUY" if sweep_low else "SELL"
            # Otherwise continue watching original C1.
            continue

        c2 = data.iloc[c2_i]
        invalid = (candle.Low < c2.Low if side == "BUY"
                   else candle.High > c2.High)
        confirmed = three_candle_core(c1, c2, candle, side)
        if invalid and confirmed:
            # Intrabar sequencing unknown: record, never count as confirmed.
            data.attrs.setdefault("ambiguous", []).append({
                "C1_time": data.index[c1_i],
                "C2_time": data.index[c2_i],
                "C3_time": data.index[i],
                "Direction": side,
            })
        if invalid:
            c1_i, c2_i, side = i, None, None
            continue

        if confirmed:
            yield c1_i, c2_i, i, side, i - c2_i
            c1_i, c2_i, side = i, None, None


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


# 6. MAIN NOTEBOOK CALL — keep this public method name/signature unchanged
def three_candle_signal_learning(tiker, datefrom, dateTo):
    """Find BUY and SELL core patterns, then PRINT other filters only."""
    if tiker not in ("NQ=F", "GC=F", "MES=F"):
        raise ValueError("Use NQ=F, GC=F, or MES=F")

    data = load_learning_candles(tiker, datefrom, dateTo)
    print(f"Downloaded {len(data)} x 15m candles for {tiker}")
    signals = []
    requested_start = date.fromisoformat(str(datefrom))

    for c1_i, c2_i, c3_i, direction, wait_bars in scan_core_candidates(data):
        times = [data.index[j] for j in (c1_i, c2_i, c3_i)]
        if times[2].date() < requested_start:
            continue   # Warm-up candles are not reported as new candidates.
        c1, c2, c3 = (data.iloc[c1_i], data.iloc[c2_i], data.iloc[c3_i])

        # All checks are print-only; core detection never depends on them.
        # Additional direction-neutral measures mirror BUY and SELL.
        body2 = abs(c2.Close - c2.Open)
        sweep_distance = (c1.Low - c2.Low if direction == "BUY"
                          else c2.High - c1.High)
        tick_size = {"NQ=F": 0.25, "GC=F": 0.10, "MES=F": 0.25}[tiker]
        sweep_ticks = sweep_distance / tick_size
        directional_wick = (min(c2.Open, c2.Close) - c2.Low
                            if direction == "BUY"
                            else c2.High - max(c2.Open, c2.Close))
        c3_close_break = (c3.Close > max(c2.Open, c2.Close)
                          if direction == "BUY"
                          else c3.Close < min(c2.Open, c2.Close))
        c3_directional = (c3.Close > c3.Open and c3.Close > c2.Close
                          if direction == "BUY"
                          else c3.Close < c3.Open and c3.Close < c2.Close)
        checks = {
            "c1_range_pct": candle_range_pct(c1) >= MIN_C1_RANGE_PCT,
            "c2_range_pct": candle_range_pct(c2) >= MIN_C2_RANGE_PCT,
            "c2_lower_wick_longer_than_body": c2_lower_wick_longer_than_body(c2),
            "c2_sweeps_c1_low": c2_sweeps_c1_low(c1, c2),
            "c3_confirms_buy": c3_confirms_buy(c2, c3),
            "c3_volume_higher": c3_volume_higher(c2, c3),
            "directional_wick_gt_body": directional_wick > body2,
            "directional_sweep": sweep_distance > 0,
            "c3_directional_strength": c3_directional,
            "c3_close_beyond_c2_body": c3_close_break,
            "sweep_at_least_1_tick": sweep_ticks >= 1 - 1e-7,
            "sweep_at_least_2_ticks": sweep_ticks >= 2 - 1e-7,
        }
        # Descriptive 'pass' flag, NOT a gate for core candidates.
        passed = all(checks[key] for key in (
            "c1_range_pct", "c2_range_pct", "directional_wick_gt_body",
            "directional_sweep", "c3_directional_strength"
        )) and (not CHECK_VOLUME or checks["c3_volume_higher"])
        number = len(signals) + 1
        if PRINT_FILTER_DETAILS:
            print(f"\nCandidate {number} | {direction} | "
                  f"C3 {times[2]:%Y-%m-%d %H:%M %Z} | "
                  f"CORE=True | Extra filters={passed} | "
                  f"C3 wait={wait_bars} bar(s)")
            for name, ok in checks.items():
                note = (" (optional OFF)" if name == "c3_volume_higher"
                        and not CHECK_VOLUME else "")
                print(f"  {name} = {ok}{note}")

        # BUY/SL columns are retained for notebook compatibility only.
        # They represent the C2 close/open study references, NOT filled orders.
        row = {"Ticker": tiker, "Direction": direction,
               "BUY": float(c2.Close), "SL": float(c2.Open),
               "C3_wait_bars": wait_bars,
               "C2_sweep_ticks": float(sweep_ticks),
               "core_match": True, "all_filters_pass": passed}
        row.update(checks)
        for label, stamp, candle in zip(("C1", "C2", "C3"), times, (c1, c2, c3)):
            row[f"{label}_time"] = stamp
            for field in ("Open", "High", "Low", "Close", "Volume"):
                row[f"{label}_{field}"] = float(candle[field])
        signals.append(row)

    result = pd.DataFrame(signals)
    result.attrs["ambiguous"] = data.attrs.get("ambiguous", [])
    result.attrs["candles"] = data
    result.attrs["requested_start"] = str(datefrom)
    passed_count = int(result["all_filters_pass"].sum()) if not result.empty else 0
    print(f"\nFound {len(result)} core candidates; {passed_count} meet descriptive checks.")
    print(f"Ambiguous confirmation/invalidation candles: {len(result.attrs['ambiguous'])}")
    print("\n========== PASSED CANDIDATES ==========")
    if passed_count == 0:
        print("None")
    else:
        for idx, row in result.loc[result["all_filters_pass"]].iterrows():
            print(f"Candidate {idx+1} | {row['Direction']} | "
                  f"C3 {row['C3_time']:%Y-%m-%d %H:%M %Z} | "
                  f"C2 close reference {row['BUY']:.2f} | "
                  f"C2 open reference {row['SL']:.2f}")
            for name in ("c1_range_pct", "c2_range_pct",
                         "c2_lower_wick_longer_than_body", "c2_sweeps_c1_low",
                         "c3_confirms_buy", "c3_volume_higher"):
                note = (" (optional OFF)" if name == "c3_volume_higher"
                        and not CHECK_VOLUME else "")
                print(f"  {name} = {bool(row[name])}{note}")
    return result


# Build MA20 on the complete dataset; display only requested dates.
def chart_data_and_mas(result):
    """Compute EMA20 and EMA200 with hidden historical candles before chart start."""
    full_data = result.attrs.get("candles")
    if full_data is None or full_data.empty:
        raise ValueError("Full candles unavailable. Rerun the scanner.")
    ma20 = full_data.Close.ewm(span=20, adjust=False).mean()
    ma200 = full_data.Close.ewm(span=200, adjust=False).mean()
    start = result.attrs.get("requested_start")
    if start is None:
        return full_data, ma20, ma200
    visible = full_data.loc[full_data.index.date >= date.fromisoformat(start)]
    if visible.empty:
        raise ValueError("No candles in requested date range")
    return visible, ma20.reindex(visible.index), ma200.reindex(visible.index)


# 7. PLOT SIGNALS: plot only when called separately
def plot_signal(result, show_sr=False, show_metrics=False):
    """Show the FULL downloaded NQ candle chart for EACH matching signal."""
    if result is None or result.empty:
        print("No signals to plot.")
        return

    data, ma20, ma200 = chart_data_and_mas(result)

    metric_table = build_signal_metrics(result) if show_metrics else pd.DataFrame()
    for number, row in result.iterrows():
        print(f"\n=== {row['Ticker']} {row['Direction']} SIGNAL {number + 1}/{len(result)} ===")
        for label in ("C1", "C2", "C3"):
            print(
                f"{label} | {row[f'{label}_time']:%Y-%m-%d %H:%M %Z} | "
                f"O={row[f'{label}_Open']:.2f} "
                f"H={row[f'{label}_High']:.2f} "
                f"L={row[f'{label}_Low']:.2f} "
                f"C={row[f'{label}_Close']:.2f} "
                f"Vol={row[f'{label}_Volume']:.0f}"
            )
        print(f"C2 close study reference: {row['BUY']:.2f} | C2 open study reference: {row['SL']:.2f}")
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
                  label=f"C2 close reference {row['BUY']:.2f}")
        ax.hlines(row["SL"], c2_position, len(data) - 0.5,
                  color="#ff6978", linewidth=1.3,
                  label=f"C2 open reference {row['SL']:.2f}")

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
                label="EMA20 (15m close)", zorder=4)
        ax.plot(range(len(data)), ma200, color="#b58cff", linewidth=1.6,
                label="EMA200 (15m close)", zorder=4)
        ax.set_xlim(-1, len(data))
        ax.set_ylabel("NQ futures price", color="#dbe5f0")
        ax.set_title(f"{row['Ticker']} | 15m | {row['Direction']} Signal {number + 1}/{len(result)} | UK time",
                     color="#f0f5fa")
        ax.tick_params(colors="#dbe5f0")
        for spine in ax.spines.values():
            spine.set_color("#526174")
        ax.grid(color="#526174", alpha=0.35)
        ax.legend(loc="best", facecolor="#1a2534",
                  edgecolor="#526174", labelcolor="white")
        if show_metrics and not metric_table.empty:
            selected = metric_table.loc[metric_table["Candidate"] == number + 1]
            if not selected.empty:
                observation = selected.iloc[0]
                fields = list(metric_table.columns)[3:]
                lines = []
                for name in fields:
                    value = observation[name]
                    shown = f"{value:.3f}" if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value)
                    lines.append(f"{name}: {shown}")
                fig.set_size_inches(22, 10)
                fig.tight_layout(rect=(0, 0, 0.73, 1))
                fig.text(0.745, 0.96, "RESEARCH METRICS (PRINT ONLY)", color="#f0f5fa",
                         fontsize=12, va="top", weight="bold")
                fig.text(0.745, 0.92, "\n".join(lines), color="#dbe5f0",
                         fontsize=8.8, va="top", family="monospace", linespacing=1.4)
            else:
                fig.tight_layout()
        else:
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
    plot_signal(passed, show_sr=True, show_metrics=True)


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
            label="EMA20 (15m close)", zorder=4)
    ax.plot(range(len(data)), ma200, color="#b58cff", linewidth=1.6,
                label="EMA200 (15m close)", zorder=4)
    ax.legend(loc="best", facecolor="#1a2534", edgecolor="#526174", labelcolor="white")
    ax.set_xlim(-1, len(data))
    ax.set_ylabel("NQ futures price", color="#dbe5f0")
    ax.set_title(f"15m | {len(result)} core candidate C2 markers | UK time",
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
            linewidth=1.5, label="EMA20 (15m close)")
    ax.plot(range(len(data)), ma200, color="#b58cff",
            linewidth=1.6, label="EMA200 (15m close)")

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



# V3 POINTS 3-8: SIX INDEPENDENT RESEARCH METHODS.
# They return measurements only; no threshold changes the core candidates.
# All inputs end at the C3 bar. No future bar is used.


def location_filter(history, direction, entry, risk_points):
    """#3: Confirmed swing S/R and room toward the opposing level."""
    # A 2-right-bar pivot becomes known only at pivot + 2.
    levels = detect_swing_levels(history, left=2, right=2)
    supports = [price for kind, pivot, known, price in levels
                if kind == "SUPPORT" and known < len(history) and price <= entry]
    resistances = [price for kind, pivot, known, price in levels
                   if kind == "RESISTANCE" and known < len(history) and price >= entry]
    support = max(supports) if supports else float("nan")
    resistance = min(resistances) if resistances else float("nan")
    opposing = resistance if direction == "BUY" else support
    distance = ((opposing - entry) if direction == "BUY"
                else (entry - opposing))
    return {
        "sr_support": support,
        "sr_resistance": resistance,
        "sr_room_points": distance,
        "sr_room_R": distance / risk_points if risk_points > 0 else float("nan"),
    }


def market_shape_filter(history, c2_position, direction):
    """#4: 10/20 bar ranges and slope into C2; an early V hypothesis."""
    def span(n):
        part = history.iloc[max(0, len(history) - n):]
        if len(part) < n:
            return float("nan")
        return 100 * (part.High.max() - part.Low.min()) / part.Close.iloc[-1]

    # Compare C2 with the close 10 bars before it: approach only, not future.
    before = history.iloc[:c2_position + 1]
    approach = before.iloc[-11:] if len(before) >= 11 else pd.DataFrame()
    approach_pct = (100 * (approach.Close.iloc[-1] / approach.Close.iloc[0] - 1)
                    if len(approach) == 11 else float("nan"))
    c3 = history.iloc[-1]
    c2 = history.iloc[c2_position]
    recovery_pct = (100 * (c3.Close - c2.Close) / c2.Close
                    if direction == "BUY" else
                    100 * (c2.Close - c3.Close) / c2.Close)
    v_shape = bool(pd.notna(approach_pct) and
                   (approach_pct < 0 if direction == "BUY" else approach_pct > 0)
                   and recovery_pct > 0)
    return {
        "range_10_pct": span(10), "range_20_pct": span(20),
        "approach_10_pct": approach_pct,
        "recovery_c2_c3_pct": recovery_pct,
        "v_shape_observed": v_shape,
    }


def volume_filter(history, c2_position):
    """#5: C2 volume against preceding 20 bars; C3/C2 participation."""
    c2 = history.iloc[c2_position]
    c3 = history.iloc[-1]
    previous = history.Volume.iloc[max(0, c2_position - 20):c2_position]
    avg = previous.mean() if len(previous) >= 20 else float("nan")
    return {
        "c2_rvol_20": c2.Volume / avg if pd.notna(avg) and avg > 0 else float("nan"),
        "c3_c2_volume_ratio_v3": (c3.Volume / c2.Volume
                                 if c2.Volume > 0 else float("nan")),
        "c3_volume_increases": bool(c3.Volume > c2.Volume),
    }


def time_filter(c3_time):
    """#6: Time-of-day in New York session; outputs stay UK-time elsewhere."""
    et = c3_time.tz_convert("America/New_York")
    mins = et.hour * 60 + et.minute
    if 9 * 60 + 30 <= mins < 10 * 60 + 30:
        label = "US_OPENING_HOUR"
    elif 10 * 60 + 30 <= mins < 16 * 60:
        label = "US_RTH"
    elif 4 * 60 <= mins < 9 * 60 + 30:
        label = "US_PREMARKET"
    elif 16 * 60 <= mins < 18 * 60:
        label = "US_POSTMARKET"
    else:
        label = "OVERNIGHT"
    return {"session_bucket": label, "c3_hour_uk": c3_time.hour}


def wick_filter(c2, direction):
    """#7: C2 directional rejection wick; do not require a wick."""
    body = abs(c2.Close - c2.Open)
    wick = (min(c2.Open, c2.Close) - c2.Low if direction == "BUY"
            else c2.High - max(c2.Open, c2.Close))
    total = c2.High - c2.Low
    return {
        "c2_rejection_wick_points": wick,
        "c2_rejection_wick_to_body": wick / body if body else float("nan"),
        "c2_rejection_wick_fraction": wick / total if total else float("nan"),
        "c2_no_rejection_wick": bool(wick == 0),
    }


def daily_range_filter(history, direction, entry, risk_points):
    """#8: Current developing futures session and previous completed session."""
    # Futures session rolls at 18:00 ET, including when UK DST differs.
    et = history.index.tz_convert("America/New_York")
    ids = pd.Series((et + pd.Timedelta(hours=6)).date, index=history.index)
    today = ids.iloc[-1]
    current = history.loc[ids == today]
    prior_ids = ids[ids < today]
    prior = (history.loc[ids == prior_ids.iloc[-1]]
             if not prior_ids.empty else pd.DataFrame())
    current_high, current_low = current.High.max(), current.Low.min()
    width = current_high - current_low
    prior_high = prior.High.max() if not prior.empty else float("nan")
    prior_low = prior.Low.min() if not prior.empty else float("nan")
    # "Room" to these levels is recorded only if they oppose direction.
    target = (prior_high if direction == "BUY" else prior_low)
    room = (target - entry if direction == "BUY" else entry - target)
    if pd.notna(room) and room <= 0:
        room = float("nan")  # prior-day level already passed: not overhead
    return {
        "day_high_so_far": current_high,
        "day_low_so_far": current_low,
        "day_range_pct": 100 * width / entry if entry else float("nan"),
        "day_range_position_pct": 100 * (entry - current_low) / width
                                  if width else float("nan"),
        "previous_session_high": prior_high,
        "previous_session_low": prior_low,
        "room_to_previous_day_level_R": (
            room / risk_points if risk_points > 0 else float("nan")),
    }


def v3_research_checks(history, c2_time, direction, ticker):
    """Run #3-#8 once per core signal. No entry filters, ranking, or lookahead."""
    if c2_time not in history.index:
        raise ValueError("C2 missing from historical 15m bars")
    c2_pos = int(history.index.get_loc(c2_time))
    c2, c3 = history.iloc[c2_pos], history.iloc[-1]
    # Assumed study reference for room only; actual fills may be different.
    entry = float(c3.Close)
    risk = (entry * 0.002 if ticker == "NQ=F" else
            3.0 if ticker == "MES=F" else float("nan"))
    values = {}
    values.update(location_filter(history, direction, entry, risk))
    values.update(market_shape_filter(history, c2_pos, direction))
    values.update(volume_filter(history, c2_pos))
    values.update(time_filter(history.index[-1]))
    values.update(wick_filter(c2, direction))
    values.update(daily_range_filter(history, direction, entry, risk))
    return values


# 11. RESEARCH METRICS: observational values (NO signal filters)
def build_signal_metrics(result):
    """One row per core candidate, computed using bars available through C3.

    Research fields do not affect core_match or all_filters_pass.
    Indicator warm-up uses the earlier candles already saved in result.
    """
    if result is None or result.empty:
        return pd.DataFrame()
    data = result.attrs["candles"]
    close, high, low, volume = data.Close, data.High, data.Low, data.Volume

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    change = close.diff()
    gains = change.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    losses = (-change).clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    rsi = 100 * gains / (gains + losses).replace(0, float("nan"))
    prev = close.shift()
    tr = pd.concat([high-low, (high-prev).abs(), (low-prev).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/14, adjust=False).mean()
    mean20 = close.rolling(20, min_periods=20).mean()
    std20 = close.rolling(20, min_periods=20).std(ddof=0)
    prior_low20 = low.shift().rolling(20, min_periods=20).min()
    prior_high20 = high.shift().rolling(20, min_periods=20).max()

    # Futures trading session changes at 18:00 New York time.
    eastern = data.index.tz_convert("America/New_York")
    session = pd.Series((eastern + pd.Timedelta(hours=6)).date, index=data.index)
    typical_price = (high + low + close) / 3
    cumulative_vol = volume.groupby(session).cumsum()
    vwap = (typical_price * volume).groupby(session).cumsum() / cumulative_vol.where(cumulative_vol > 0)

    def pct(part, whole):
        return 100 * part / whole if whole else float("nan")

    records = []
    for number, row in result.iterrows():
        t = row["C3_time"]
        if t not in data.index:
            continue
        i = data.index.get_loc(t)
        c1, c2, c3 = [data.loc[row[f"C{n}_time"]] for n in (1, 2, 3)]
        body2 = abs(c2.Close - c2.Open)
        body3 = abs(c3.Close - c3.Open)
        upper2 = c2.High - max(c2.Open, c2.Close)
        lower2 = min(c2.Open, c2.Close) - c2.Low
        upper3 = c3.High - max(c3.Open, c3.Close)
        lower3 = min(c3.Open, c3.Close) - c3.Low
        metrics = {
            "C1_range_pct": pct(c1.High-c1.Low, c1.Close),
            "C2_range_pct": pct(c2.High-c2.Low, c2.Close),
            "C3_range_pct": pct(c3.High-c3.Low, c3.Close),
            "C2_body_pct": pct(body2, c2.Close),
            "C3_body_pct": pct(body3, c3.Close),
            "C2_lower_wick_pct": pct(lower2, c2.Close),
            "C2_upper_wick_pct": pct(upper2, c2.Close),
            "C3_upper_wick_pct": pct(upper3, c3.Close),
            "C3_lower_wick_pct": pct(lower3, c3.Close),
            "C2_lower_wick_body": lower2/body2 if body2 else float("nan"),
            "C3_total_wick_body": (upper3+lower3)/body3 if body3 else float("nan"),
            "C3_C2_volume_ratio": c3.Volume/c2.Volume if c2.Volume else float("nan"),
            "C3_volume": c3.Volume,
            "EMA20_distance_pct": pct(c3.Close-ema20.iloc[i], ema20.iloc[i]),
            "EMA200_distance_pct": pct(c3.Close-ema200.iloc[i], ema200.iloc[i]),
            "EMA20_slope_3bar_pct": pct(ema20.iloc[i]-ema20.iloc[i-3], ema20.iloc[i-3]) if i >= 3 else float("nan"),
            "RSI14": rsi.iloc[i],
            "ATR14_pct": pct(atr.iloc[i], c3.Close),
            "BB20_width_pct": pct(4*std20.iloc[i], mean20.iloc[i]),
            "VWAP_distance_pct": pct(c3.Close-vwap.iloc[i], vwap.iloc[i]),
            "Prior20_low_sweep_pct": pct(prior_low20.iloc[i]-c3.Low, c3.Close) if c3.Low < prior_low20.iloc[i] else 0.0,
            "Prior20_high_distance_pct": pct(c3.Close-prior_high20.iloc[i], prior_high20.iloc[i]),
            "C3_confirms_buy": bool(c3.Close > c3.Open and c3.Close > c2.Close),
            "C3_directional_strength": bool(
                c3.Close > c3.Open and c3.Close > c2.Close
                if row["Direction"] == "BUY"
                else c3.Close < c3.Open and c3.Close < c2.Close),
        }
        # C3-time slice ensures indicators/levels do not see future candles.
        history = data.iloc[:i + 1]
        extra = v3_research_checks(history, row["C2_time"],
                                   row["Direction"], row["Ticker"])
        records.append({"Candidate": number+1, "C3_time": t,
                        "all_filters_pass": bool(row["all_filters_pass"]),
                        **metrics, **extra})
    return pd.DataFrame(records)


def print_signal_metrics(result):
    """Print observational metrics for each core candidate, including failed ones."""
    metrics = build_signal_metrics(result)
    if metrics.empty:
        print("No candidate metrics available.")
        return metrics
    for _, row in metrics.iterrows():
        print(f"\n=== Candidate {int(row['Candidate'])} | {row['C3_time']} | "
              f"Passed={row['all_filters_pass']} ===")
        for key in list(metrics.columns)[3:]:
            value = row[key]
            display = f"{value:.4f}" if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value)
            print(f"  {key} = {display}")
    return metrics


# 12. RUN DIRECTLY IN VS CODE (or import from your notebook)
if __name__ == "__main__":
    three_candle_signal_learning("NQ=F", "2026-10-29", "2026-10-30")
