"""Rudra Three-Candle: original RTH sweep/reclaim research.

Notebook API remains:
    test = check_signals("INTC", "2026-10-28", "2026-10-28", r=0.10)
    show_chart(test)

Historical C2-close entry is an EX-POST hypothesis: C3 volume was unavailable
at entry. Target touches do not prove executed wins or realised profit.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd

__version__ = "2.3.2-20261030"
MODEL = "RTH_C2_SWEEP_EXPOST"
print(f"[Rudra Three-Candle] LOADED v{__version__} | MODEL={MODEL}")
COLS = ["Open", "High", "Low", "Close", "Volume"]
TIMEFRAMES = {"5min": 5, "15min": 15, "30min": 30, "1h": 60, "4h": 240}


# 01. INPUT SETTINGS AND TIMEFRAMES
# Timeframe aliases and configuration.

def get_timeframe_minutes(value: str) -> int:
    aliases = {"5m": "5min", "15m": "15min", "30m": "30min",
               "60m": "1h", "60min": "1h", "1hr": "1h", "4hr": "4h", "240m": "4h"}
    key = aliases.get(str(value).lower(), str(value).lower())
    if key not in TIMEFRAMES:
        raise ValueError("interval must be 5min, 15min, 30min, 1h, or 4h")
    return TIMEFRAMES[key]



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


# 02. DOWNLOAD AND DATA QUALITY
# Detect gaps and invalid prices; never fabricate OHLCV bars.

def clean_downloaded_candles(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        raise ValueError("No Yahoo bars returned")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    if raw.index.tz is None:
        raise ValueError("Yahoo data lacks timezone")
    data = raw[COLS].copy().sort_index()
    return data.loc[~data.index.duplicated(keep="last")]


def find_missing_regular_hours_candles(data: pd.DataFrame) -> list[pd.Timestamp]:
    """Identify absent 5m timestamps only for observed US RTH dates."""
    eastern = data.index.tz_convert("America/New_York")
    missing = []
    for day in sorted(set(eastern.date)):
        observed = eastern[eastern.date == day]
        if not any((observed.hour >= 9) & (observed.hour <= 15)):
            continue
        expected = pd.date_range(
            pd.Timestamp(day, tz="America/New_York") + pd.Timedelta(hours=9, minutes=30),
            periods=78, freq="5min",
        )
        # Do not flag bars that have not happened yet on an active session.
        expected = expected[expected <= pd.Timestamp.now(tz="America/New_York")]
        missing.extend(expected.difference(observed))
    return missing


def remove_suspicious_nq_candles(data: pd.DataFrame) -> pd.DataFrame:
    """Exclude unverified NQ bars with an extreme 5m range (>2% of prior close)."""
    if data.empty:
        return data
    data = data.sort_index()
    previous = data.Close.shift(1)
    abnormal = ((data.High - data.Low) / previous > 0.02) & (previous > 0)
    # Also ensure OHLC obeys elementary envelope constraints.
    abnormal |= (data.High < data[["Open", "Close", "Low"]].max(axis=1))
    abnormal |= (data.Low > data[["Open", "Close", "High"]].min(axis=1))
    if abnormal.any():
        print("[Rudra Three-Candle] DATA WARNING: quarantining unverified NQ 5m bars:")
        for stamp in data.index[abnormal]:
            print(f"  {stamp.tz_convert('Europe/London'):%Y-%m-%d %H:%M %Z} "
                  f"range={data.loc[stamp,'High']-data.loc[stamp,'Low']:.2f}")
    return data.loc[~abnormal].copy()


def download_candles_from_yahoo(start: str, end: str, symbol: str = "INTC",
                  interval: str = "5m") -> pd.DataFrame:
    """Download Yahoo bars, retry incomplete 5m RTH dates, flag quality problems.

    Yahoo cannot guarantee missing data recovery. Never interpolate OHLCV.
    """
    import yfinance as yf
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last < first:
        raise ValueError("end before start")
    raw = yf.download(
        symbol, start=first.isoformat(),
        end=(last+timedelta(days=1)).isoformat(), interval=interval,
        prepost=True, auto_adjust=False, progress=False, threads=False,
    )
    data = clean_downloaded_candles(raw)
    if interval in ("5m", "5min"):
        missing = find_missing_regular_hours_candles(data)
        if missing:
            print(f"[Rudra Three-Candle] DATA WARNING: {len(missing)} missing RTH 5m bars; retrying dates")
            for day in sorted({t.date() for t in missing}):
                retry = yf.download(
                    symbol, start=(day-timedelta(days=1)).isoformat(),
                    end=(day+timedelta(days=1)).isoformat(),
                    interval="5m", prepost=True, auto_adjust=False,
                    progress=False, threads=False,
                )
                if not retry.empty:
                    extra = clean_downloaded_candles(retry)
                    data = pd.concat([data, extra]).sort_index()
                    data = data.loc[~data.index.duplicated(keep="last")]
        if symbol == "NQ=F":
            data = remove_suspicious_nq_candles(data)
        unresolved = find_missing_regular_hours_candles(data)
        if unresolved:
            print(f"[Rudra Three-Candle] DATA WARNING: {len(unresolved)} RTH 5m bars still missing/invalid:")
            for stamp in unresolved:
                print(f"  {stamp.tz_convert('Europe/London'):%Y-%m-%d %H:%M %Z}")
            print("[Rudra Three-Candle] Incomplete candle groups will be excluded; no synthetic fills.")
    return data


# 03. BUILD MARKET SESSION CANDLES
# Completed RTH or extended-futures bars from 5-minute source data.

def build_regular_market_candles(raw: pd.DataFrame, start: str, end: str,
                    symbol: str = "INTC", interval: str = "15min") -> pd.DataFrame:
    """Completed US RTH bars from 5m, anchored at 09:30 ET for any supported timeframe."""
    if raw.index.tz is None:
        raise ValueError("Input timestamps must be timezone-aware")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last < first:
        raise ValueError("end before start")
    minutes = get_timeframe_minutes(interval)
    group_size = minutes // 5
    data = raw[COLS].apply(pd.to_numeric, errors="coerce").dropna().sort_index()
    if symbol == "NQ=F":
        data = remove_suspicious_nq_candles(data)
    data.index = data.index.tz_convert("America/New_York")
    data = data.loc[(pd.Index(data.index.date) >= first) &
                    (pd.Index(data.index.date) <= last)]
    data = data.between_time("09:30", "15:59")
    sessions = []
    for day_date, day in data.groupby(data.index.date):
        offset = day.index.hour*60 + day.index.minute - 570
        day = day.loc[offset % 5 == 0]
        bucket = (day.index.hour*60 + day.index.minute - 570)//minutes
        grouped = day.groupby(bucket)
        count = grouped.size()
        bars = grouped.agg({"Open":"first", "High":"max", "Low":"min",
                            "Close":"last", "Volume":"sum"}).loc[count[count==group_size].index]
        if bars.empty:
            continue
        session_open = pd.Timestamp(day_date, tz="America/New_York") + pd.Timedelta(hours=9, minutes=30)
        bars.index = pd.DatetimeIndex([
            session_open + pd.Timedelta(minutes=int(b)*minutes) for b in bars.index
        ])
        sessions.append(bars)
    if not sessions:
        raise ValueError(f"No complete RTH {interval} candles")
    result = pd.concat(sessions)
    result.index = result.index.tz_convert("Europe/London")
    result.attrs.update({"symbol":symbol, "model":MODEL, "interval_minutes":minutes})
    return result



def get_trading_session_dates(data: pd.DataFrame):
    """NY 18:00 futures open belongs to the following ET trading date."""
    eastern = data.index.tz_convert("America/New_York")
    if data.attrs.get("session_type") == "nq_extended":
        return (eastern + pd.Timedelta(hours=6)).date
    return eastern.date


def build_extended_nq_4hour_candles(raw: pd.DataFrame, start: str,
                            end: str) -> pd.DataFrame:
    """Full 4h NQ futures candles, 18:00 ET anchored; omit partial 14–17 bar.

    Maintenance 17:00–18:00 ET is excluded. Futures sessions run from
    18:00 ET of the previous calendar day to 17:00 ET of the trade date.
    """
    if raw.index.tz is None:
        raise ValueError("NQ source timestamps must be timezone-aware")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last < first:
        raise ValueError("end before start")
    data = raw[COLS].apply(pd.to_numeric, errors="coerce").dropna().sort_index()
    data = remove_suspicious_nq_candles(data)
    data.index = data.index.tz_convert("America/New_York")
    labels = (data.index + pd.Timedelta(hours=6)).date
    data = data.loc[(pd.Index(labels) >= first) & (pd.Index(labels) <= last)]
    sessions = []
    for trade_date, day in data.groupby((data.index + pd.Timedelta(hours=6)).date):
        session_open = pd.Timestamp(trade_date, tz="America/New_York") - pd.Timedelta(hours=6)
        offsets = pd.Index((day.index - session_open).total_seconds() / 60).astype(int)
        # Only full blocks within 18:00–14:00 ET; skip 14:00–17:00 partial.
        valid = (offsets >= 0) & (offsets < 1200) & (offsets % 5 == 0)
        day = day.loc[valid]
        buckets = offsets[valid] // 240
        grouped = day.groupby(buckets)
        counts = grouped.size()
        complete = counts[counts == 48].index
        bars = grouped.agg({"Open":"first", "High":"max", "Low":"min",
                            "Close":"last", "Volume":"sum"}).loc[complete]
        if bars.empty:
            continue
        bars.index = pd.DatetimeIndex([
            session_open + pd.Timedelta(minutes=int(b)*240) for b in bars.index
        ])
        sessions.append(bars)
    if not sessions:
        raise ValueError("No complete NQ extended-session 4h candles")
    result = pd.concat(sessions)
    result.index = result.index.tz_convert("Europe/London")
    result.attrs.update({"symbol":"NQ=F", "model":"NQ_EXTENDED_C2_SWEEP_EXPOST",
                         "interval_minutes":240, "session_type":"nq_extended"})
    return result


def build_extended_nq_candles(raw: pd.DataFrame, start: str,
                            end: str, interval: str = "15min") -> pd.DataFrame:
    """Full NQ futures bars anchored to 18:00 ET; exclude 17:00-18:00 ET break.

    'start' and 'end' refer to futures *trade dates* (US Eastern).
    For example, Friday 01:45 UK is included in Friday's futures session.
    Incomplete groups, missing 5m timestamps and suspicious bars are excluded.
    """
    if raw.index.tz is None:
        raise ValueError("NQ source timestamps must be timezone-aware")
    minutes = get_timeframe_minutes(interval)
    if minutes == 240:
        return build_extended_nq_4hour_candles(raw, start, end)
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last < first:
        raise ValueError("end before start")
    data = raw[COLS].apply(pd.to_numeric, errors="coerce").dropna().sort_index()
    data = remove_suspicious_nq_candles(data)
    data.index = data.index.tz_convert("America/New_York")
    # Explicit trade-date assignment avoids treating the evening open as
    # a different calendar trading day.
    trade_days = (data.index + pd.Timedelta(hours=6)).date
    data = data.loc[(pd.Index(trade_days) >= first) &
                    (pd.Index(trade_days) <= last)]
    sessions = []
    for trade_date, day in data.groupby((data.index + pd.Timedelta(hours=6)).date):
        session_open = pd.Timestamp(trade_date, tz="America/New_York") - pd.Timedelta(hours=6)
        offsets = pd.Index((day.index - session_open).total_seconds() / 60).astype(int)
        valid = (offsets >= 0) & (offsets < 1380) & (offsets % 5 == 0)
        day = day.loc[valid]
        buckets = offsets[valid] // minutes
        grouped = day.groupby(buckets)
        counts = grouped.size()
        # Reject partial final 4h/1h blocks ending after the daily 17:00 close.
        complete = counts[counts == minutes // 5].index
        complete = [b for b in complete if (int(b)+1)*minutes <= 1380]
        bars = grouped.agg({"Open":"first", "High":"max", "Low":"min",
                            "Close":"last", "Volume":"sum"}).loc[complete]
        if bars.empty:
            continue
        bars.index = pd.DatetimeIndex([
            session_open + pd.Timedelta(minutes=int(b)*minutes)
            for b in bars.index
        ])
        sessions.append(bars)
    if not sessions:
        raise ValueError(f"No complete NQ extended-session {interval} candles")
    result = pd.concat(sessions).sort_index()
    result.index = result.index.tz_convert("Europe/London")
    result.attrs.update({"symbol":"NQ=F",
                         "model":"NQ_EXTENDED_C2_SWEEP_EXPOST",
                         "interval_minutes":minutes, "session_type":"nq_extended"})
    return result


def load_candles_from_csv(path: str, start: str, end: str,
                       interval: str = "15min", session: str = "RTH") -> pd.DataFrame:
    raw = pd.read_csv(path)
    time_col = "Datetime" if "Datetime" in raw else "datetime_source"
    if time_col not in raw:
        raise ValueError("Expected Datetime or datetime_source CSV column")
    raw.index = pd.DatetimeIndex(pd.to_datetime(raw[time_col], utc=True))
    if session.lower() == "extended":
        return build_extended_nq_candles(raw, start, end, interval)
    if get_timeframe_minutes(interval) == 240:
        return build_extended_nq_4hour_candles(raw, start, end)
    return build_regular_market_candles(raw, start, end, Path(path).name.split("_")[0].split(".")[0], interval)


# 04. THREE-CANDLE SETUP RULES
# C1 preceding candle, C2 bullish sweep/reclaim, C3 confirmation.

def is_bullish_three_candle_sweep(c1: pd.Series, c2: pd.Series,
                            c3: pd.Series, check_vol: bool = True,
                            min_c1_range_pct: float = 0.20,
                            min_c2_range_pct: float = 0.25) -> bool:
    """C2 wick sweeps C1; C3 must close green; volume optional."""
    # C2 may be RED or GREEN: require a lower-wick sweep of C1 low.
    # C3 MUST be GREEN and close above C2. Volume remains optional.
    # Provisional absolute-size gate: rejects weak/tiny C1+C2 patterns.
    # C1 >= 0.20% and C2 >= 0.25% of their respective closing prices.
    if min_c1_range_pct < 0 or min_c2_range_pct < 0:
        raise ValueError("minimum candle ranges must be nonnegative")
    c1_range_pct = 100 * float(c1.High - c1.Low) / float(c1.Close)
    c2_range_pct = 100 * float(c2.High - c2.Low) / float(c2.Close)
    if c1_range_pct < min_c1_range_pct or c2_range_pct < min_c2_range_pct:
        return False
    body = abs(float(c2.Close - c2.Open))
    lower_wick = float(min(c2.Open, c2.Close) - c2.Low)
    return (lower_wick > body
            and float(c2.Low) < float(c1.Low)
            and float(c3.Close) > float(c3.Open)
            and float(c3.Close) > float(c2.Close)
            and (not check_vol or (pd.notna(c2.Volume) and pd.notna(c3.Volume)
                 and float(c2.Volume) > 0 and float(c3.Volume) > float(c2.Volume))))


def find_three_candle_setups(data: pd.DataFrame, check_vol: bool = True,
                             min_c1_range_pct: float = 0.20,
                             min_c2_range_pct: float = 0.25):
    """Never join pattern candles across two US trading sessions."""
    for _, day in data.groupby(get_trading_session_dates(data)):
        step = pd.Timedelta(minutes=int(data.attrs.get("interval_minutes", 15)))
        for i in range(2, len(day)):
            if day.index[i] - day.index[i-1] != step or day.index[i-1] - day.index[i-2] != step:
                continue
            c1, c2, c3 = day.iloc[i-2], day.iloc[i-1], day.iloc[i]
            if not is_bullish_three_candle_sweep(c1, c2, c3, check_vol=check_vol,
                    min_c1_range_pct=min_c1_range_pct,
                    min_c2_range_pct=min_c2_range_pct):
                continue
            yield Signal(
                day.index[i], "LONG", day.index[i-2], day.index[i-1], day.index[i],
                float(c2.High), float(c2.Low), float(c2.Open), float(c2.Close),
                float(c3.Volume), float(c2.Volume),
            )


# 05. SUPPORT / RESISTANCE SWING LEVELS
# Confirm a pivot only after swingRight further candles have closed.

def find_confirmed_swing_levels(data: pd.DataFrame, left: int = 3, right: int = 3) -> list[dict]:
    """Causal pivot levels: only confirmed after right bars close."""
    if left < 1 or right < 1:
        raise ValueError("swingLeft and swingRight must be positive")
    levels = []
    step = pd.Timedelta(minutes=int(data.attrs.get("interval_minutes", 15)))
    for trade_day, day in data.groupby(get_trading_session_dates(data)):
        for i in range(left, len(day)-right):
            window = day.iloc[i-left:i+right+1]
            if any(window.index[j]-window.index[j-1] != step
                   for j in range(1, len(window))):
                continue
            others = window.drop(day.index[i])
            for kind, column, compare in (("SUPPORT","Low",min),
                                          ("RESISTANCE","High",max)):
                price = float(day.iloc[i][column])
                extreme = float(compare(others[column]))
                if (kind == "SUPPORT" and price < extreme) or (
                        kind == "RESISTANCE" and price > extreme):
                    levels.append({"kind":kind,"price":price,"pivot_time":day.index[i],
                                   "confirmed_at":day.index[i+right]+step,
                                   "trade_day":trade_day})
    return levels


def find_nearest_swing_for_setup(signal: Signal, levels: list[dict],
                            proximity_pct: float, minutes: int) -> dict:
    """Nearest already-confirmed support to C2 low or resistance to C2 high."""
    if proximity_pct < 0:
        raise ValueError("swingProximity must be nonnegative")
    known_at = signal.candle2_time + pd.Timedelta(minutes=minutes)
    candidates = []
    for level in levels:
        if level["confirmed_at"] > known_at:
            continue
        point = signal.candle2_low if level["kind"] == "SUPPORT" else signal.candle2_high
        distance = abs(point-level["price"])/level["price"]*100
        candidates.append((distance,level))
    if not candidates:
        return {"near":False,"distance_pct":None,"level":None}
    distance,level = min(candidates,key=lambda x:x[0])
    return {"near":distance<=proximity_pct,"distance_pct":distance,"level":level}


# 06. RESEARCH TARGET TOUCH STATISTICS
# Ex-post touches are NOT executable backtest returns.

def count_future_target_touches(signals: list[Signal], data: pd.DataFrame,
                              r_pct: float = 0.10) -> tuple[int, int, int]:
    """Same-session future highs from C3; stop ordering is deliberately ignored."""
    if r_pct <= 0:
        raise ValueError("r must be positive")
    ny_dates = get_trading_session_dates(data)
    hits = [0, 0, 0]
    for signal in signals:
        entry = signal.candle2_close
        step = max(entry-signal.candle2_open, entry*r_pct/100)
        day = (signal.time.tz_convert("America/New_York") + (
            pd.Timedelta(hours=6) if data.attrs.get("session_type") == "nq_extended"
            else pd.Timedelta(0)
        )).date()
        later = data.loc[(ny_dates == day) & (data.index >= signal.candle3_time)]
        if later.empty:
            continue
        high = float(later.High.max())
        for k in (1, 2, 3):
            hits[k-1] += int(high >= entry+k*step)
    return tuple(hits)


def sum_hypothetical_target_returns(signals: list[Signal], data: pd.DataFrame,
                               r_pct: float = 0.10) -> tuple[float, float, float]:
    """Sum target-hit gross price returns per hypothetical equal-sized trade.

    NOT realised profit: stop order, C3 look-ahead, overlap, fees and slippage
    are all ignored. Each kR column is a separate fixed-target scenario.
    """
    if r_pct <= 0:
        raise ValueError("r must be positive")
    dates = get_trading_session_dates(data)
    gains = [0.0, 0.0, 0.0]
    for signal in signals:
        entry = signal.candle2_close
        step = max(entry-signal.candle2_open, entry*r_pct/100)
        day = (signal.time.tz_convert("America/New_York") + (
            pd.Timedelta(hours=6) if data.attrs.get("session_type") == "nq_extended"
            else pd.Timedelta(0)
        )).date()
        later = data.loc[(dates == day) & (data.index >= signal.candle3_time)]
        if later.empty:
            continue
        peak = float(later.High.max())
        for k in (1, 2, 3):
            if peak >= entry+k*step:
                gains[k-1] += 100*k*step/entry
    return tuple(gains)


# 07. MAIN NOTEBOOK METHOD: CHECK SIGNALS
# Edit user-facing parameters here; keep the method name stable.

def check_signals(ticker: str = "INTC", *args: str, r: float = 0.10,
                  start: str | None = None, end: str | None = None,
                  interval: str = "15min", target_r: int = 1,
                  require_breakout: bool = False,
                  source_csv: str | None = None,
                  checkVol: bool = False, session: str = "RTH",
                   swingLeft: int = 3, swingRight: int = 3,
                   swingProximity: float = 0.25,
                   nearSwingOnly: bool = False,
                   minC1RangePct: float = 0.20,
                   minC2RangePct: float = 0.25) -> dict:
    """Supports both (ticker,start,end) and (ticker,interval,start,end).\n\n    Historical scanner; not an execution backtest.

    target_r/require_breakout remain accepted for older cells but do not
    change the archived fixed pattern, which is a separate research model.
    """
    if str(session).lower() not in ("rth", "extended"):
        raise ValueError("session must be RTH or extended")
    session = "extended" if session.lower() == "extended" else "RTH"
    if session == "extended" and ticker != "NQ=F":
        raise ValueError("extended futures session currently supports NQ=F only")
    if not isinstance(checkVol, bool):
        raise TypeError("checkVol must be True or False")
    if len(args) == 2:
        start, end = args
    elif len(args) == 3:
        interval, start, end = args
    elif len(args) != 0:
        raise TypeError("Use check_signals(ticker, start, end) or (ticker, interval, start, end)")
    if start is None or end is None:
        raise TypeError("start and end dates are required")
    minutes = get_timeframe_minutes(interval)
    interval_label = f"{minutes}min" if minutes < 60 else f"{minutes//60}h"
    if minutes == 240 and ticker not in ("NQ=F",):
        raise ValueError("4h extended futures mode currently supports NQ=F only")
    active_model = "NQ_EXTENDED_C2_SWEEP_EXPOST" if session == "extended" or minutes == 240 else MODEL
    print(f"[Rudra Three-Candle] v{__version__} | MODEL={active_model} | TIMEFRAME={interval_label} | checkVol={checkVol} | SESSION={session}")
    if source_csv:
        data = load_candles_from_csv(source_csv, start, end, interval_label, session=session)
    elif session == "extended" or minutes == 240:
        fetch_start = (date.fromisoformat(start) - timedelta(days=1)).isoformat()
        data = build_extended_nq_candles(download_candles_from_yahoo(fetch_start, end, ticker), start, end, interval_label)
    else:
        data = build_regular_market_candles(download_candles_from_yahoo(start, end, ticker),
                               start, end, ticker, interval_label)
    levels = find_confirmed_swing_levels(data, swingLeft, swingRight)
    signals = list(find_three_candle_setups(
        data, check_vol=checkVol, min_c1_range_pct=minC1RangePct,
        min_c2_range_pct=minC2RangePct))
    matches = {sig.candle2_time: find_nearest_swing_for_setup(
        sig, levels, swingProximity, minutes) for sig in signals}
    raw_count = len(signals)
    if nearSwingOnly:
        signals = [sig for sig in signals if matches[sig.candle2_time]["near"]]
    near_count = sum(matches[sig.candle2_time]["near"] for sig in signals)
    hits = count_future_target_touches(signals, data, r)
    gains = sum_hypothetical_target_returns(signals, data, r)
    total = len(signals)
    print(f"\n{ticker} | {start} to {end} | {len(data)} {'EXTENDED' if data.attrs.get('session_type') == 'nq_extended' else 'RTH'} {interval_label} candles")
    print(f"=== RUDRA THREE-CANDLE SUMMARY (ex-post price touches; checkVol={checkVol}) ===")
    print(f"Swing levels confirmed: {len(levels)} | pivot {swingLeft}/{swingRight} | proximity {swingProximity:.2f}%")
    print(f"Signals near swings: {near_count}/{total} | nearSwingOnly={nearSwingOnly}"
          + (f" | unfiltered signals={raw_count}" if nearSwingOnly else ""))
    print(f"{'Metric':<24} {'Count':>8} {'Rate':>9} {'Gain %':>12}")
    print(f"{'Qualifying signals':<24} {total:>8} {'100%' if total else 'N/A':>9} {'—':>12}")
    for k, count in enumerate(hits, 1):
        rate = f"{count/total*100:.1f}%" if total else "N/A"
        print(f"{str(k)+'R price touches':<24} {count:>8} {rate:>9} {gains[k-1]:>11.2f}%")
    print("Gain % = sum of hypothetical gross target-hit returns at each R; NOT realized P&L.")
    print("Executed win rate: NOT DETERMINED (C3 look-ahead / intrabar order).")
    print("\n=== SIGNAL DETAILS (CANDLE 2 ONLY) ===")
    if not signals:
        print("No qualifying signals.")
    for number, s in enumerate(signals, 1):
        c2 = data.loc[s.candle2_time]
        print(f"\n#{number} LONG | C2 {s.candle2_time:%Y-%m-%d %H:%M %Z} | "
              f"C3 close/confirmation {(s.candle3_time + pd.Timedelta(minutes=minutes)):%H:%M %Z}")
        print(pd.DataFrame([c2], index=[s.candle2_time], columns=COLS).to_string())
        vol_ratio = (f"{s.candle3_volume/s.candle2_volume:.2f}x"
                     if s.candle2_volume > 0 else "N/A")
        print(f"C2 close hypothesis {s.candle2_close:.4f} | SL {s.candle2_open:.4f} | "
              f"C3/C2 volume {vol_ratio} (filter {'ON' if checkVol else 'OFF'})")
        match = matches[s.candle2_time]
        if match["level"]:
            level = match["level"]
            print(f"Swing {'NEAR' if match['near'] else 'FAR'} | "
                  f"{level['kind']} {level['price']:.2f} | "
                  f"wick distance {match['distance_pct']:.3f}% | "
                  f"pivot {level['pivot_time']:%Y-%m-%d %H:%M %Z}")
        else:
            print("Swing N/A | no previously confirmed level")
    return {"data":data, "signals":signals, "results":[],
            "touches":hits, "potential_gains_pct":gains, "model":active_model, "r_pct":r, "interval":interval_label, "checkVol":checkVol, "session":session, "swing_levels":levels,
            "swing_matches":matches, "swingProximity":swingProximity,
            "nearSwingOnly":nearSwingOnly}


# 08. CHART: ALL SWING PRICE LINES
# Signals are hidden for now as requested.

def show_chart(test: dict, signal_number: int | None = None) -> None:
    """Draw all confirmed swing support/resistance price lines, with candles.

    No signal, entry, stop or target overlays at this stage. Price lines begin
    at each swing's confirmation time (not at its historical pivot) so the
    plotted level is never displayed before it could have been known.
    signal_number is retained for notebook call compatibility but unused.
    """
    data = test["data"]
    levels = test.get("swing_levels", [])
    if not levels:
        levels = find_confirmed_swing_levels(data)
    fig, (ax, volume) = plt.subplots(
        2, 1, figsize=(15, 7), sharex=True,
        gridspec_kw={"height_ratios":[4,1]},
    )
    for x, (_, bar) in enumerate(data.iterrows()):
        color = "#168650" if bar.Close >= bar.Open else "#c64242"
        ax.vlines(x, bar.Low, bar.High, color=color, linewidth=1)
        ax.add_patch(Rectangle(
            (x-.3, min(bar.Open,bar.Close)), .6,
            max(abs(bar.Close-bar.Open), .005),
            facecolor=color, edgecolor=color))
        volume.bar(x, bar.Volume, color=color, width=.7)

    # Every confirmed pivot is drawn separately; no nearest-six restriction.
    for level in levels:
        price = float(level["price"])
        known_at = level["confirmed_at"]
        first = int(data.index.searchsorted(known_at, side="left"))
        if first >= len(data):
            continue
        color = "#008b8b" if level["kind"] == "SUPPORT" else "#dd8626"
        ax.hlines(price, first, len(data)-.3, color=color,
                  linestyles="dashed", linewidth=.9, alpha=.7)
        ax.plot(first, price, marker=".", color=color, markersize=3)
    ax.set_xlim(-.5, len(data)+3)
    ax.set_title(f"{data.attrs.get('symbol','INTC')} | "
                 f"{test.get('interval','15min')} | "
                 f"{'EXTENDED' if data.attrs.get('session_type') == 'nq_extended' else 'RTH'} "
                 f"| ALL CONFIRMED SWING LEVELS | "
                 f"Support {sum(lv['kind']=='SUPPORT' for lv in levels)} / "
                 f"Resistance {sum(lv['kind']=='RESISTANCE' for lv in levels)}")
    ax.set_ylabel("Price")
    volume.set_ylabel("Volume")
    ticks = list(range(0, len(data), max(1, len(data)//11)))
    volume.set_xticks(ticks, [data.index[i].strftime("%d %b %H:%M") for i in ticks],
                      rotation=35, ha="right")
    from matplotlib.lines import Line2D
    ax.legend(handles=[
        Line2D([0],[0],color="#008b8b",ls="--",label="Confirmed support"),
        Line2D([0],[0],color="#dd8626",ls="--",label="Confirmed resistance"),
    ],loc="best",fontsize=9)
    fig.tight_layout()
    plt.show()
    plt.close(fig)


# 09. COMPATIBILITY AND METHOD-CALL GUIDE

def review_historical_csv(path: str, start: str, end: str) -> list[Signal]:
    """Compatibility helper for archived reproduction."""
    ticker = Path(path).name.split("_")[0].split(".")[0]
    return check_signals(ticker, start, end, source_csv=path)["signals"]


def show_method_flow() -> None:
    """Print the readable processing sequence for notebook review."""
    print(f"""RUDRA THREE-CANDLE v{__version__} — METHOD CALL FLOW
check_signals(...)
  1. get_timeframe_minutes(...) — validate timeframe
  2. download_candles_from_yahoo(...) OR load_candles_from_csv(...)
     - clean_downloaded_candles(...)
     - find_missing_regular_hours_candles(...)
     - remove_suspicious_nq_candles(...)
  3. build_regular_market_candles(...) OR build_extended_nq_candles(...)
     - build_extended_nq_4hour_candles(...) for NQ 4h
  4. find_confirmed_swing_levels(...) — causal support/resistance pivots
  5. find_three_candle_setups(...) — C1/C2/C3 sweep
     - is_bullish_three_candle_sweep(...)
  6. find_nearest_swing_for_setup(...) — optional proximity flag
  7. count_future_target_touches(...) — ex-post only
  8. sum_hypothetical_target_returns(...) — ex-post only
  9. print summary and return test dictionary

show_chart(test)
  - draw ALL confirmed swing support/resistance price lines
  - display candlesticks + volume; NO signals for now
""")


# Backwards-compatible internal aliases (older notebooks may import these).
timeframe_minutes = get_timeframe_minutes
_normalize_yahoo = clean_downloaded_candles
_rth_missing_5m = find_missing_regular_hours_candles
_quarantine_nq_outliers = remove_suspicious_nq_candles
download_data = download_candles_from_yahoo
resample_rth_5m = build_regular_market_candles
futures_session_dates = get_trading_session_dates
resample_nq_extended_4h = build_extended_nq_4hour_candles
resample_nq_extended_5m = build_extended_nq_candles
load_historical_5m = load_candles_from_csv
historical_three_candle = is_bullish_three_candle_sweep
find_historical_signals = find_three_candle_setups
find_confirmed_swings = find_confirmed_swing_levels
nearest_confirmed_swing = find_nearest_swing_for_setup
historical_target_touches = count_future_target_touches
historical_potential_gains = sum_hypothetical_target_returns
historical_report = review_historical_csv


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--symbol", default="INTC")
    parser.add_argument("--r-pct", type=float, default=.10)
    parser.add_argument("--historical-csv", default=None)
    parser.add_argument("--no-charts", action="store_true")
    args = parser.parse_args()
    result = check_signals(args.symbol, args.start, args.end,
                           r=args.r_pct, source_csv=args.historical_csv)
    if not args.no_charts:
        show_chart(result)
