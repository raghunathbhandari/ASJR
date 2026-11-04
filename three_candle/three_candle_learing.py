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

# V3 initial screening thresholds; research defaults, not yet optimized.
# A Candidate is always a confirmed core pattern.
# A Pass Candidate must meet ALL six #3-#8 conditions.
V3_SR_MIN_ROOM_R = 1.0
V3_V_MIN_RECOVERY_PCT = 0.0
V3_RANGE_MIN_R = 1.0
V3_C2_MIN_RVOL20 = 1.20
V3_C3_MIN_VOLUME_RATIO = 1.00
V3_ALLOWED_SESSIONS = {
    "OVERNIGHT", "US_PREMARKET", "US_OPENING_HOUR", "US_RTH", "US_POSTMARKET"
}  # All sessions initially eligible; tighten after a measured backtest.
V3_MIN_WICK_BODY = 0.50
V3_DAILY_MIN_ROOM_R = 1.0



# Law of Motion: experimental thresholds from the 2026-10-30 MES labels.
# Research only; does not change the existing core or six V3 checks.
config_law_of_motion = {
    "A1": {
        "min_approach_points": 25.0,
        "min_reaction_points": 15.0,
        "min_c3_body_break_points": 10.0,
        "max_ema20_distance_pct": -0.20,
    },
    "WEAK": {
        "min_approach_points": 20.0,
        "min_reaction_points": 10.0,
        "min_c3_body_break_points": 7.0,
        "min_ema20_distance_pct": -0.05,
    },
    "require_directional_ema5_slope": True,
    # EMA200 is recorded for analysis but not used as a pass condition.
}


def Filter_law_of_motion(signal, config=None):
    """Return True if a candidate meets the A1 or WEAK Law of Motion rules.

    Accepts a dict or pandas Series containing the six point-in-time metrics.
    Use Filter_law_of_motion_grade() to distinguish A1 from WEAK.
    """
    return Filter_law_of_motion_grade(signal, config) != "REJECT"


def Filter_law_of_motion_grade(signal, config=None):
    """Classify as A1, WEAK, or REJECT without altering V1/V3 detection."""
    cfg = config_law_of_motion if config is None else config
    direction = signal["Direction"]
    if direction not in ("BUY", "SELL"):
        return "REJECT"
    vals = (
        "approach_distance_points", "bounce_distance_points",
        "c3_body_break_points", "ema20_distance_pct", "ema5_slope_pct",
    )
    if any(pd.isna(signal.get(key)) for key in vals):
        return "REJECT"
    if cfg["require_directional_ema5_slope"]:
        slope = signal["ema5_slope_pct"]
        if not (slope > 0 if direction == "BUY" else slope < 0):
            return "REJECT"

    def common_pass(thresholds):
        return (
            signal["approach_distance_points"] >= thresholds["min_approach_points"]
            and signal["bounce_distance_points"] >= thresholds["min_reaction_points"]
            and signal["c3_body_break_points"] >= thresholds["min_c3_body_break_points"]
        )

    a1 = cfg["A1"]
    if common_pass(a1) and signal["ema20_distance_pct"] <= a1["max_ema20_distance_pct"]:
        return "A1"

    weak = cfg["WEAK"]
    if common_pass(weak) and signal["ema20_distance_pct"] > weak["min_ema20_distance_pct"]:
        return "WEAK"

    return "REJECT"


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
    # Retain the underlying IBKR 5m bars to resolve aggressive C3 fills.
    # The original 15m candles and their calculations remain unchanged.
    raw.index = raw.index.tz_convert("Europe/London")
    data.attrs["ibkr_5m"] = raw[["Open", "High", "Low", "Close", "Volume"]]
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
    """Detect overlapping C2 setups independently, with multi-bar C3 waiting.

    Each consecutive pair of 15m candles is a potential C1/C2 pair.
    A sweep may open a BUY, SELL, or both independent pending setups.
    Previously opened setups stay active while newer C2s are discovered.
    Each setup is emitted once, at its first unambiguous body break.
    Sweep-extreme invalidation takes priority on the confirming candle
    because OHLC cannot establish intrabar event order.
    Missing 15m candles invalidate pending setups; never bridge a gap.
    """
    step = pd.Timedelta(minutes=15)
    pending = []  # (c1_index, c2_index, direction)
    data.attrs["ambiguous"] = []

    for i in range(1, len(data)):
        if data.index[i] - data.index[i - 1] != step:
            pending = []
            continue

        candle = data.iloc[i]
        still_pending = []

        # Evaluate all earlier C2 candidates without blocking newer C2s.
        for c1_i, c2_i, direction in pending:
            c1 = data.iloc[c1_i]
            c2 = data.iloc[c2_i]
            invalid = (candle.Low < c2.Low if direction == "BUY"
                       else candle.High > c2.High)
            confirmed = three_candle_core(c1, c2, candle, direction)

            if invalid and confirmed:
                data.attrs["ambiguous"].append({
                    "C1_time": data.index[c1_i],
                    "C2_time": data.index[c2_i],
                    "C3_time": data.index[i],
                    "Direction": direction,
                })
            if invalid:
                continue
            if confirmed:
                yield c1_i, c2_i, i, direction, i - c2_i
            else:
                still_pending.append((c1_i, c2_i, direction))

        pending = still_pending

        # Every candle can be a new C2 relative to the preceding C1,
        # including candles that also confirmed another pending setup.
        c1 = data.iloc[i - 1]
        if candle.Low < c1.Low:
            pending.append((i - 1, i, "BUY"))
        if candle.High > c1.High:
            pending.append((i - 1, i, "SELL"))


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
def six_point_research_metrics(history, c2_position, direction):
    """Six comparison measurements through C3 close; no change to signal filters.

    Previous price extreme is calculated from at most 20 bars before C2.
    Approach and bounce are point distances; EMA distances and slope are %.
    """
    c2 = history.iloc[c2_position]
    c3 = history.iloc[-1]
    previous = history.iloc[max(0, c2_position - 20):c2_position]
    if previous.empty:
        approach = float("nan")
    elif direction == "BUY":
        approach = float(previous.High.max() - c2.Low)
    else:
        approach = float(c2.High - previous.Low.min())
    bounce = float(c3.Close - c2.Low if direction == "BUY"
                   else c2.High - c3.Close)
    c2_body_edge = max(c2.Open, c2.Close) if direction == "BUY" else min(c2.Open, c2.Close)
    body_break = float(c3.Close - c2_body_edge if direction == "BUY"
                       else c2_body_edge - c3.Close)
    closes = history.Close
    ema5 = closes.ewm(span=5, adjust=False).mean()
    ema20 = closes.ewm(span=20, adjust=False).mean()
    ema200 = closes.ewm(span=200, adjust=False).mean()

    def pct_from_ema(ema_value):
        return float(100 * (c3.Close - ema_value) / ema_value) if ema_value else float("nan")

    ema5_slope = (float(100 * (ema5.iloc[-1] - ema5.iloc[-2]) / ema5.iloc[-2])
                  if len(ema5) >= 2 and ema5.iloc[-2] else float("nan"))
    return {
        "approach_distance_points": approach,
        "bounce_distance_points": bounce,
        "c3_body_break_points": body_break,
        "ema200_distance_pct": pct_from_ema(ema200.iloc[-1]),
        "ema20_distance_pct": pct_from_ema(ema20.iloc[-1]),
        "ema5_slope_pct": ema5_slope,
    }


def three_candle_signal_learning(tiker, datefrom, dateTo, enableDig=False):
    """Find BUY/SELL patterns; enableDig controls printing only (default off)."""
    if tiker not in ("NQ=F", "GC=F", "MES=F"):
        raise ValueError("Use NQ=F, GC=F, or MES=F")

    data = load_learning_candles(tiker, datefrom, dateTo)
    if enableDig:
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
        # The core scanner is the ONLY source of Candidate detection.
        # These six V3 checks determine Pass Candidate status.
        history = data.iloc[:c3_i + 1]
        observations = v3_research_checks(history, times[1], direction, tiker)
        v3_checks = v3_pass_checks(observations)
        passed = all(v3_checks.values())
        number = len(signals) + 1
        if enableDig:
            print(f"\nCandidate {number} | {direction} | "
                  f"C3 {times[2]:%Y-%m-%d %H:%M %Z} | "
                  f"CORE=True | Pass Candidate={passed} | "
                  f"C3 wait={wait_bars} bar(s)")
            for name, ok in v3_checks.items():
                print(f"  {name} = {ok}")
            # Legacy diagnostic values remain in result, but are not printed.

        # BUY/SL columns are retained for notebook compatibility only.
        # They represent the C2 close/open study references, NOT filled orders.
        row = {"Ticker": tiker, "Direction": direction,
               "BUY": float(c2.Close), "SL": float(c2.Open),
               "C3_wait_bars": wait_bars,
               "C2_sweep_ticks": float(sweep_ticks),
               "core_match": True, "all_filters_pass": passed,
               "pass_candidate": passed, "candidate_status": (
                   "PASS" if passed else "CORE_ONLY"),
               "V3withBodySize_pass": v3_with_body_size_pass(direction, c3),
               "V3withBodySize_Wick4to10_pass":
                   v3_with_body_size_wick4to10_pass(direction, c2, c3),
               "V3withBodySize_C3_body_pct": abs(c3.Close - c3.Open) * 100 / c3.Close}
        row.update(checks)
        row.update(v3_checks)
        row.update(six_point_research_metrics(history, c2_i, direction))
        row["law_of_motion_grade"] = Filter_law_of_motion_grade(row)
        row["Filter_law_of_motion"] = Filter_law_of_motion(row)
        row["Signal"] = number
        for label, stamp, candle in zip(("C1", "C2", "C3"), times, (c1, c2, c3)):
            row[f"{label}_time"] = stamp
            for field in ("Open", "High", "Low", "Close", "Volume"):
                row[f"{label}_{field}"] = float(candle[field])
        signals.append(row)

    result = pd.DataFrame(signals)
    result.attrs["ambiguous"] = data.attrs.get("ambiguous", [])
    result.attrs["candles"] = data
    result.attrs["ibkr_5m"] = data.attrs.get("ibkr_5m")
    result.attrs["requested_start"] = str(datefrom)
    if enableDig:
        passed_count = int(result["all_filters_pass"].sum()) if not result.empty else 0
        body_count = int(result["V3withBodySize_pass"].sum()) if not result.empty else 0
        wick_count = int(result["V3withBodySize_Wick4to10_pass"].sum()) if not result.empty else 0
        print(f"\nFound {len(result)} core Candidates; {passed_count} Pass Candidates (all 6 V3 filters).")
        print(f"V3withBodySize SELL C3 body 0.05%-<0.10%: {body_count} research candidates.")
        print(f"V3withBodySize_Wick4to10 quality candidates: {wick_count}")
        print(f"Ambiguous confirmation/invalidation candles: {len(result.attrs['ambiguous'])}")
        columns = [
            "Signal", "Direction", "C3_time", "candidate_status",
            "Filter_law_of_motion", "law_of_motion_grade",
            "filter_3_location", "filter_4_v_shape", "filter_5_volume",
            "filter_6_time", "filter_7_wick", "filter_8_daily_range",
            "approach_distance_points", "bounce_distance_points",
            "c3_body_break_points", "ema200_distance_pct",
            "ema20_distance_pct", "ema5_slope_pct",
        ]
        print("\n========== SIGNAL COMPARISON (one row per signal) ==========")
        if not result.empty:
            print(f"Law of Motion: {int(result['Filter_law_of_motion'].sum())}/{len(result)} True "
                  f"({int((result['law_of_motion_grade'] == 'A1').sum())} A1, "
                  f"{int((result['law_of_motion_grade'] == 'WEAK').sum())} WEAK)")
        if result.empty:
            print("No signals to compare.")
        else:
            from IPython.display import display
            display(result[columns])
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
def plot_signal_passed(result, stop_points=6.0, before=12, after=6):
    """Plot Law of Motion passes with actual simulated trailing-stop exits.

    Only candle bars plus ENTRY and EXIT markers. Each setup is evaluated
    separately; overlapping positions are permitted in these diagnostic
    plots, unlike the sequential portfolio backtest summary.
    """
    if result is None or result.empty:
        print("No candidates to plot.")
        return
    if "Filter_law_of_motion" not in result.columns:
        raise ValueError("Law of Motion field missing; rerun scanner")
    candles = result.attrs.get("candles")
    if candles is None or candles.empty:
        raise ValueError("Missing OHLC history in result.attrs['candles']")

    passed = result.loc[result["Filter_law_of_motion"].fillna(False)].copy()
    passed = passed.drop_duplicates(subset=["Direction", "C2_time", "C3_time"])
    passed = passed.sort_values("C3_time")
    if passed.empty:
        print("No Law of Motion passed signals.")
        return

    print(f"Plotting {len(passed)} Law of Motion signals.")
    for _, row in passed.iterrows():
        single = pd.DataFrame([row.to_dict()])
        single.attrs["candles"] = candles
        trades = summarise_signal_result(single, stop_points=stop_points, verbose=False)
        trade = trades.iloc[0] if not trades.empty else None

        # Print the individual trade result immediately before its chart.
        number = row.get("Signal", "?")
        grade = row.get("law_of_motion_grade", "PASS")
        print(f"\n========== SIGNAL {number} | {row['Direction']} | {grade} ==========")
        if trade is None:
            print("No simulated fill: the entry trigger or future candle is unavailable.")
        else:
            status = str(trade["Status"])
            points = float(trade["Points"])
            return_pct = float(trade["Return_pct"])
            risk_r = points / stop_points
            exit_text = (f"{float(trade['Exit']):.2f}" if status == "CLOSED"
                         else "OPEN")
            exit_time = (str(trade["Exit_time"]) if status == "CLOSED"
                         else "Not exited")
            print(f"Entry (C3) : {trade['Entry_time']} @ {float(trade['Entry']):.2f}")
            print(f"Initial SL : {float(trade['Entry']) - (stop_points if row['Direction'] == 'BUY' else -stop_points):.2f}")
            print(f"Exit       : {exit_time} @ {exit_text}")
            print(f"Status     : {status} | {trade['Exit_reason']}")
            print(f"P/L        : {points:+.2f} points | {return_pct:+.4f}% | {risk_r:+.2f}R")
            print(f"Final SL   : {float(trade['Final_SL']):.2f} | "
                  f"Highest step: {int(trade['Max_R_step'])}R")
            if status == "OPEN":
                print("P/L shown is unrealised mark-to-market, not booked profit.")
            if bool(trade.get("C3_intrabar_ambiguous", False)):
                print("CAUTION: entry/stop sequence inside C3 unknown; conservative SL assumed.")

        c2_idx = int(candles.index.get_loc(row["C2_time"]))
        c3_idx = int(candles.index.get_loc(row["C3_time"]))
        entry_idx = (int(candles.index.get_loc(trade["Entry_time"]))
                     if trade is not None else None)
        exit_idx = (int(candles.index.get_loc(trade["Exit_time"]))
                    if trade is not None and trade["Status"] == "CLOSED" else None)

        start_idx = max(0, c2_idx - before)
        # Show the actual trailing-stop exit, or all remaining bars if OPEN.
        last_trade_idx = (exit_idx if exit_idx is not None else
                          len(candles)-1 if trade is not None else c3_idx)
        end_idx = min(len(candles)-1, max(c3_idx, last_trade_idx)+after)
        visible = candles.iloc[start_idx:end_idx+1]
        fig, ax = plt.subplots(figsize=(14, 6), facecolor="#101722")
        ax.set_facecolor("#101722")

        for i, candle in enumerate(visible.itertuples()):
            color = "#23c985" if candle.Close >= candle.Open else "#ff6471"
            ax.vlines(i, candle.Low, candle.High, color=color, linewidth=1)
            ax.add_patch(Rectangle(
                (i-0.3, min(candle.Open, candle.Close)), 0.6,
                max(abs(candle.Close-candle.Open), 0.01),
                facecolor=color, edgecolor=color))

        if trade is not None:
            x_entry = entry_idx-start_idx
            entry_price = float(trade["Entry"])
            # Three clean price reference lines. Initial SL is distinct
            # from the advancing trailing stop used by the simulator.
            sign = 1 if row["Direction"] == "BUY" else -1
            initial_sl = entry_price - sign * stop_points
            x_line_end = (exit_idx - start_idx if exit_idx is not None
                          else len(visible) - 1)
            x_line_end = max(x_entry + 0.5, x_line_end)
            ax.hlines(entry_price, x_entry, x_line_end,
                      colors="#35e89b", linewidth=1.6,
                      label=f"ENTRY {entry_price:.2f}", zorder=5)
            ax.hlines(initial_sl, x_entry, x_line_end,
                      colors="#ff6471", linewidth=1.6,
                      label=f"INITIAL SL {initial_sl:.2f}", zorder=5)
            if exit_idx is not None:
                ax.hlines(float(trade["Exit"]), x_entry, x_line_end,
                          colors="#bd91ff", linewidth=1.6,
                          label=f"TRAIL EXIT {float(trade['Exit']):.2f}", zorder=5)
            ax.scatter(x_entry, entry_price, marker="^", s=140,
                       color="#35e89b", zorder=7)
            ax.annotate(f"ENTRY {entry_price:.2f}",
                        (x_entry, entry_price), xytext=(10, 15),
                        textcoords="offset points", color="#35e89b",
                        fontsize=10, weight="bold")
            if exit_idx is not None:
                x_exit = exit_idx-start_idx
                exit_price = float(trade["Exit"])
                ax.scatter(x_exit, exit_price, marker="v", s=140,
                           color="#bd91ff", zorder=7)
                ax.annotate(
                    f"TRAIL EXIT {exit_price:.2f} | {trade['Points']:+.2f} pt",
                    (x_exit, exit_price), xytext=(10, -25),
                    textcoords="offset points", color="#bd91ff",
                    fontsize=10, weight="bold")
            else:
                ax.annotate("OPEN — trailing stop not hit",
                            (x_entry, entry_price), xytext=(10, -25),
                            textcoords="offset points", color="#dbe5f0",
                            fontsize=9)

        step = max(1, len(visible)//12)
        ticks = list(range(0, len(visible), step))
        ax.set_xticks(ticks, [visible.index[i].strftime("%d %b %H:%M")
                             for i in ticks], rotation=35, ha="right")
        number = row.get("Signal", "?")
        grade = row.get("law_of_motion_grade", "PASS")
        ax.set_title(f"{row['Ticker']} | Signal {number} | "
                     f"{row['Direction']} {grade} | UK time",
                     color="#f0f5fa")
        if trade is not None:
            status = str(trade["Status"])
            pnl = float(trade["Points"])
            pct = float(trade["Return_pct"])
            roi_r = pnl / stop_points
            summary_line = (
                f"{status} | P/L {pnl:+.2f} pts | {pct:+.4f}% | {roi_r:+.2f}R"
                if status == "CLOSED" else
                f"OPEN (unrealised) | {pnl:+.2f} pts | {pct:+.4f}% | {roi_r:+.2f}R"
            )
            fig.text(0.5, 0.94, summary_line, ha="center", va="top",
                     color="#dbe5f0", fontsize=10, weight="bold")
        ax.set_ylabel("Futures price", color="#dbe5f0")
        ax.tick_params(colors="#dbe5f0")
        ax.grid(color="#526174", alpha=0.25)
        if trade is not None:
            ax.legend(loc="best", facecolor="#1a2534",
                      edgecolor="#526174", labelcolor="white")
        for spine in ax.spines.values():
            spine.set_color("#526174")
        fig.tight_layout(rect=(0, 0, 1, 0.92))
        plt.show()
        plt.close(fig)


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
    values["v3_risk_pct"] = 100 * risk / entry if entry and pd.notna(risk) else float("nan")
    values["v3_c3_directional_strength"] = bool(
        c3.Close > c3.Open and c3.Close > c2.Close if direction == "BUY"
        else c3.Close < c3.Open and c3.Close < c2.Close)
    return values


def v3_pass_checks(values):
    """V3 #3-#8 pass flags. Missing values fail rather than auto-pass.

    These thresholds are provisional; core candidate detection never changes.
    """
    import math

    def enough(value, minimum):
        try:
            return math.isfinite(float(value)) and float(value) >= minimum
        except (ValueError, TypeError):
            return False

    # #3: confirmed opposing support/resistance at least 1R away.
    location_ok = enough(values["sr_room_R"], V3_SR_MIN_ROOM_R)

    # #4: directional recovery + 10/20 historical price range sufficient.
    # 20-bar range expressed as percent; C3-price risk is also percent.
    needed_range_pct = values["v3_risk_pct"] * V3_RANGE_MIN_R
    shape_ok = (bool(values["v_shape_observed"])
                and enough(values["recovery_c2_c3_pct"], V3_V_MIN_RECOVERY_PCT)
                and enough(values["range_20_pct"], needed_range_pct))

    # #5: volume needs evidence at C2 or increasing confirmation at C3.
    volume_ok = (enough(values["c2_rvol_20"], V3_C2_MIN_RVOL20)
                 or enough(values["c3_c2_volume_ratio_v3"],
                           V3_C3_MIN_VOLUME_RATIO))

    # #6: time is configurable; all known sessions initially eligible.
    time_ok = values["session_bucket"] in V3_ALLOWED_SESSIONS

    # #7: long wick OR strong directional close/reclaim. No wick is allowed.
    wick_ok = (enough(values["c2_rejection_wick_to_body"], V3_MIN_WICK_BODY)
               or bool(values["v3_c3_directional_strength"]))

    # #8: documented previous-session high/low should leave >=1R room.
    daily_ok = enough(values["room_to_previous_day_level_R"],
                      V3_DAILY_MIN_ROOM_R)
    return {
        "filter_3_location": bool(location_ok),
        "filter_4_v_shape": bool(shape_ok),
        "filter_5_volume": bool(volume_ok),
        "filter_6_time": bool(time_ok),
        "filter_7_wick": bool(wick_ok),
        "filter_8_daily_range": bool(daily_ok),
    }


def v3_with_body_size_wick4to10_pass(direction, c2, c3):
    """Experimental variant: SELL + C3 body [0.05%,0.10%) + C2 wick/body [4,10).

    Use unrounded OHLC for both thresholds. Zero-body C2 is excluded.
    Existing V3 core, six-filter status and BodySize stay unchanged.
    """
    if not v3_with_body_size_pass(direction, c3):
        return False
    body2 = abs(c2.Close - c2.Open)
    if body2 <= 0:
        return False
    upper_wick = c2.High - max(c2.Open, c2.Close)
    return bool(4.0 <= upper_wick / body2 < 10.0)


def v3_with_body_size_pass(direction, c3):
    """V3withBodySize: core candidate + SELL + C3 body [0.05%, 0.10%).

    Separate experimental variant; does not change original V3 six filters.
    Uses unrounded 15m C3 OHLC values at confirmation time.
    """
    if c3.Close <= 0:
        return False
    body_pct = abs(c3.Close - c3.Open) * 100 / c3.Close
    return bool(direction == "SELL" and 0.05 <= body_pct < 0.10)


# 11. RESEARCH METRICS: observational values (NO signal filters)
def build_signal_metrics(result):
    """One row per core candidate, computed using bars available through C3.

    Research fields do not affect core_match. V3 pass status is computed
    separately from six #3-#8 checks at the C3 decision time.
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
                        "V3withBodySize_pass": bool(row["V3withBodySize_pass"]),
                        "V3withBodySize_Wick4to10_pass":
                            bool(row["V3withBodySize_Wick4to10_pass"]),
                        "all_filters_pass": bool(row["all_filters_pass"]),
                        **{name: row[name] for name in (
                            "filter_3_location", "filter_4_v_shape",
                            "filter_5_volume", "filter_6_time",
                            "filter_7_wick", "filter_8_daily_range")},
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


def summarise_signal_result(result, stop_points=6.0, verbose=True):
    """Law of Motion: aggressive C3 entry, 6-point R, stepped SL, no TP.

    For the C3 entry bar use the original IBKR 5m sub-bars (if present).
    A low/high *before* the breakout cannot stop a position not yet entered.
    If entry and SL occur inside the same 5m bar, their order is unknown:
    classify AMBIGUOUS, not a realised loss. Missing 5m + simultaneous
    15m entry/SL is also AMBIGUOUS. No future data is used for entry.
    Subsequent 15m candles retain the conservative trailing-stop logic:
    each completed +1R improves SL by 1R starting on the next candle.
    Trades exit only on stop or remain OPEN at end of available data.
    No fees/slippage; non-overlapping trades; open/ambiguous excluded from
    confirmed realised P&L, success and drawdown.
    """
    import math

    if not isinstance(result, pd.DataFrame):
        raise ValueError("result must be a Pandas DataFrame")
    if stop_points <= 0:
        raise ValueError("stop_points must be positive")
    required = {"Filter_law_of_motion", "Direction", "C3_time", "C2_Open", "C2_Close"}
    if not required.issubset(result.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(result.columns))}")
    candles = result.attrs.get("candles")
    if candles is None or candles.empty:
        raise ValueError("Missing OHLC history: supply original scanner result")
    ibkr_5m = result.attrs.get("ibkr_5m")
    if ibkr_5m is None:
        ibkr_5m = candles.attrs.get("ibkr_5m")

    passed = result.loc[result["Filter_law_of_motion"].fillna(False)].sort_values("C3_time")
    trades = []
    last_exit_idx = -1
    busy_until_end = False
    skipped = 0
    for _, signal in passed.iterrows():
        direction = signal["Direction"]
        stamp = pd.Timestamp(signal["C3_time"])
        if direction not in ("BUY", "SELL") or stamp not in candles.index:
            skipped += 1
            continue

        entry_idx = int(candles.index.get_loc(stamp))
        if entry_idx <= last_exit_idx or busy_until_end:
            skipped += 1
            continue

        sign = 1 if direction == "BUY" else -1
        boundary = (max(float(signal["C2_Open"]), float(signal["C2_Close"]))
                    if sign == 1 else
                    min(float(signal["C2_Open"]), float(signal["C2_Close"])))
        c3 = candles.iloc[entry_idx]
        crossed = (float(c3.High) > boundary if sign == 1
                   else float(c3.Low) < boundary)
        if not crossed:
            skipped += 1
            continue

        entry = None
        ambiguous = False
        c3_stop_hit = False
        c3_exit_price = None
        initial_5m = False
        c3_subbars = None

        if isinstance(ibkr_5m, pd.DataFrame) and not ibkr_5m.empty:
            start = stamp
            end = stamp + pd.Timedelta(minutes=15)
            sub = ibkr_5m.loc[(ibkr_5m.index >= start) & (ibkr_5m.index < end)]
            expected = [start + pd.Timedelta(minutes=n) for n in (0, 5, 10)]
            if list(sub.index) == expected:
                initial_5m = True
                c3_subbars = sub

        if initial_5m:
            # Observe all 5m bars in C3, entering ONLY at the first breakout.
            for subbar in c3_subbars.itertuples():
                op, hi, lo = float(subbar.Open), float(subbar.High), float(subbar.Low)
                if entry is None:
                    hit_entry = hi > boundary if sign == 1 else lo < boundary
                    if not hit_entry:
                        continue
                    entry = max(op, boundary) if sign == 1 else min(op, boundary)
                    stop = entry - sign * stop_points
                    # If stop and entry lie in this SAME 5m candle, sequence
                    # cannot be reconstructed from OHLC. Do not invent a loss.
                    if (lo <= stop if sign == 1 else hi >= stop):
                        ambiguous = True
                        break
                else:
                    # Entry occurred in a PREVIOUS 5m bar, so a subsequent
                    # stop hit is chronologically valid.
                    if (lo <= stop if sign == 1 else hi >= stop):
                        c3_stop_hit = True
                        c3_exit_price = (min(op, stop) if sign == 1
                                         else max(op, stop))
                        break
        else:
            # No verified 5m timeline. Whole-C3 entry/SL is unsequenced.
            op = float(c3.Open)
            entry = max(op, boundary) if sign == 1 else min(op, boundary)
            stop = entry - sign * stop_points
            if (float(c3.Low) <= stop if sign == 1 else float(c3.High) >= stop):
                ambiguous = True

        if entry is None:
            # Defensive case: 15m indicated breakout, but 5m data disagreed.
            skipped += 1
            continue

        stop = entry - sign * stop_points
        highest_r = 0
        exit_idx = None
        exit_price = None
        reason = "OPEN_AT_DATA_END"

        if ambiguous:
            status = "AMBIGUOUS"
            reason = "C3_ENTRY_SL_SEQUENCE_UNKNOWN"
        elif c3_stop_hit:
            status = "CLOSED"
            exit_idx, exit_price = entry_idx, c3_exit_price
            reason = "C3_STOP_5M_CONFIRMED"
        else:
            # First trail update is only from the bar AFTER C3.
            # No C3 full-bar high/low can trigger a premature stop/step.
            for bar_idx in range(entry_idx + 1, len(candles)):
                bar = candles.iloc[bar_idx]
                opening = float(bar.Open)
                low, high = float(bar.Low), float(bar.High)
                hit_stop = low <= stop if sign == 1 else high >= stop
                if hit_stop:
                    exit_idx = bar_idx
                    exit_price = (min(opening, stop) if sign == 1
                                  else max(opening, stop))
                    reason = "TRAIL_STOP"
                    break
                favourable = (high - entry) if sign == 1 else (entry - low)
                new_r = max(0, int(math.floor((favourable + 1e-8) / stop_points)))
                if new_r > highest_r:
                    highest_r = new_r
                    new_stop = entry + sign * (highest_r - 1) * stop_points
                    stop = max(stop, new_stop) if sign == 1 else min(stop, new_stop)
            status = "CLOSED" if exit_idx is not None else "OPEN"

        if status == "CLOSED":
            last_exit_idx = exit_idx
            marked_price = float(exit_price)
        elif status == "OPEN":
            busy_until_end = True
            marked_price = float(candles.iloc[-1].Close)
        else:
            # Exact subsequent position is unknown: do not allow hypothetical
            # overlapping entries to be counted as confirmed.
            busy_until_end = True
            marked_price = float("nan")

        points = sign * (marked_price - entry) if pd.notna(marked_price) else float("nan")
        trades.append({
            "Signal": signal.get("Signal"),
            "Grade": signal.get("law_of_motion_grade", "PASS"),
            "Direction": direction,
            "Entry_time": stamp,
            "Exit_time": (candles.index[exit_idx] if status == "CLOSED" else pd.NaT),
            "Entry": entry,
            "Exit": exit_price if status == "CLOSED" else float("nan"),
            "Status": status,
            "Exit_reason": reason,
            "C3_intrabar_ambiguous": ambiguous,
            "Final_SL": stop,
            "Max_R_step": highest_r,
            "Points": points,
            "Return_pct": 100 * points / entry if pd.notna(points) else float("nan"),
        })

    trade_df = pd.DataFrame(trades)
    closed = (trade_df.loc[trade_df["Status"] == "CLOSED"].copy()
              if not trade_df.empty else pd.DataFrame())
    opened = (trade_df.loc[trade_df["Status"] == "OPEN"].copy()
              if not trade_df.empty else pd.DataFrame())
    ambiguous_df = (trade_df.loc[trade_df["Status"] == "AMBIGUOUS"].copy()
                    if not trade_df.empty else pd.DataFrame())
    n_closed = len(closed)
    wins = int((closed.Points > 0).sum()) if n_closed else 0
    losses = int((closed.Points < 0).sum()) if n_closed else 0
    be = n_closed - wins - losses
    win_rate = 100 * wins / n_closed if n_closed else 0.0
    net_points = float(closed.Points.sum()) if n_closed else 0.0
    net_pct = float(closed.Return_pct.sum()) if n_closed else 0.0
    if n_closed:
        equity = pd.concat([pd.Series([0.0]), closed.Points.cumsum().reset_index(drop=True)],
                           ignore_index=True)
        equity_pct = pd.concat([pd.Series([0.0]), closed.Return_pct.cumsum().reset_index(drop=True)],
                               ignore_index=True)
        dd_points = float((equity.cummax() - equity).max())
        dd_pct = float((equity_pct.cummax() - equity_pct).max())
    else:
        dd_points, dd_pct = 0.0, 0.0

    if verbose:
        print("\n========== LAW OF MOTION — 1R STEPPED TRAILING ==========")
        print(f"Total signals         : {len(result)}")
        print(f"Passed signals        : {len(passed)}")
        print(f"Executed / Open       : {len(trade_df)} / {len(opened)}")
        print(f"Closed / Ambiguous    : {n_closed} / {len(ambiguous_df)}")
        print(f"Wins / Losses / BE    : {wins} / {losses} / {be}")
        print(f"Success rate          : {win_rate:.2f}% (confirmed closed only)")
        print(f"Realised return       : {net_pct:+.3f}%")
        print(f"Realised points       : {net_points:+.2f} points")
        print(f"Max drawdown          : {dd_pct:.3f}% / {dd_points:.2f} points (closed only)")
        print(f"Rules                 : C3 aggressive body-break entry, 1R={stop_points:g}pt, "
              "step trail +1R every +1R, no TP")
        print("C3 sequence checked using IBKR 5m where available; ambiguity excluded.")
        if len(opened):
            print(f"OPEN unrealised       : {opened.Points.sum():+.2f} points (not booked)")
        if skipped:
            print(f"Skipped passed        : {skipped}")
        if not trade_df.empty:
            from IPython.display import display
            display(trade_df)
    return trade_df


# 12. RUN DIRECTLY IN VS CODE (or import from your notebook)
if __name__ == "__main__":
    three_candle_signal_learning("NQ=F", "2026-10-29", "2026-10-30")
