"""Rudra DDB A/B/C: fifteen-minute EMA9/EMA20 BUY WATCH and ASJR Gann levels.

Runs exclusively through the existing Chakra IBKR app and Discord hook.
No orders, independent broker connection, new scheduler, or legacy alerts.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "RudraScanner" / "ddb_ema_gann_config.json"
STATE = ROOT / "ASJR_Analyst" / "state" / "ddb_ema_gann_alerts.json"
GANN_CACHE = ROOT / "ASJR_Analyst" / "state" / "ddb_gann_150d_cache.json"
ET = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def config():
    c = _load(CONFIG, {})
    groups = c.get("groups", {})
    if not c.get("enabled") or not isinstance(groups, dict):
        raise RuntimeError("DDB alerts not enabled; no legacy fallback")
    seen, items = set(), []
    for group in ("A", "B", "C"):
        for item in groups.get(group, []):
            sym = str(item).strip().upper()
            if not sym.isascii() or not sym.replace(".", "").replace("-", "").isalnum():
                raise ValueError("Invalid DDB symbol")
            if sym and sym not in seen:
                items.append((sym, group))
                seen.add(sym)
    if len(items) != 49:
        raise ValueError("DDB universe must contain 49 unique A/B/C tickers")
    return c, items


def gann_levels(price, daily_low, daily_high):
    """Match ASJR Pine: MAIN odd n^2 / even n^2+1; MID quarter steps.

    The TradingView study filters all levels to the highest-high/lowest-low
    of the most recent 150 DAILY bars (including the current daily bar).
    """
    mains = [float(n * n + (1 if n % 2 == 0 else 0)) for n in range(1, 101)]
    levels = [(x, "MAIN") for x in mains]
    for a, b in zip(mains, mains[1:]):
        levels.extend((a + (b - a) * k / 4.0, "MID") for k in (1, 2, 3))
    levels = sorted((v, typ) for v, typ in levels
                    if daily_low <= v <= daily_high)
    if not levels:
        return []
    below = [p for p in levels if p[0] <= price]
    above = [p for p in levels if p[0] > price]
    selected = below[-2:] + above[:3]
    if len(selected) < 5:
        remaining = [p for p in levels if p not in selected]
        remaining.sort(key=lambda p: abs(p[0] - price))
        selected += remaining[:5 - len(selected)]
    return sorted(selected)


def build_complete_15m_bars(df, *, now):
    """Aggregate exactly three contiguous completed IBKR 5m candles per 15m bar.

    IBKR timestamp denotes the 5-minute bar OPEN. This rejects missing bars,
    unfinished 15-minute buckets, and duplicate timestamps. EMA is computed
    on 15-minute closes, never on the original five-minute closes.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    bars = df.copy().sort_index()
    if bars.index.tz is None:
        raise ValueError("IBKR bar index must be timezone-aware")
    bars.index = bars.index.tz_convert("UTC")
    bars = bars[~bars.index.duplicated(keep="last")]
    now = pd.Timestamp(now).tz_convert("UTC")
    # Exclude any 5m candle that is still forming.
    bars = bars[(bars.index + pd.Timedelta(minutes=5)) <= now]
    if bars.empty:
        return pd.DataFrame()
    for col in ("Open", "High", "Low", "Close"):
        bars[col] = pd.to_numeric(bars[col], errors="coerce")
    bars = bars.dropna(subset=["Open", "High", "Low", "Close"])
    if bars.empty:
        return pd.DataFrame()
    # Wall-clock :00/:15/:30/:45 boundaries align in UTC and America/New_York.
    quarter = bars.index.floor("15min")
    offset = (bars.index - quarter).total_seconds() / 60.0
    bars = bars[offset.isin([0.0, 5.0, 10.0])]
    if bars.empty:
        return pd.DataFrame()
    quarter = bars.index.floor("15min")
    grouped = bars.groupby(quarter, sort=True)
    complete = grouped.filter(
        lambda group: len(group) == 3
        and (group.index - group.index[0]).total_seconds().tolist()
        == [0.0, 300.0, 600.0]
    )
    if complete.empty:
        return pd.DataFrame()
    grouped = complete.groupby(complete.index.floor("15min"), sort=True)
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    if "Volume" in complete.columns:
        complete = complete.copy()
        complete["Volume"] = pd.to_numeric(
            complete["Volume"], errors="coerce").fillna(0).clip(lower=0)
        agg["Volume"] = "sum"
    result = complete.groupby(
        complete.index.floor("15min"), sort=True).agg(agg)
    # Independently enforce the 15m closing timestamp.
    return result[(result.index + pd.Timedelta(minutes=15)) <= now]


def _is_rth(ts):
    """New York 09:30-16:00, DST safe; only completed 15m RTH bars."""
    t = ts.tz_convert(ET)
    minute = t.hour * 60 + t.minute
    return 570 <= minute < 960


def _benchmark_bullish(benchmark_df, curr_time, now):
    """Fail closed if Group A semiconductor benchmark is missing or weak."""
    b = build_complete_15m_bars(benchmark_df, now=now)
    if len(b) < 28 or b.index[-1] != curr_time:
        return False
    close = b["Close"]
    fast = close.ewm(span=9, adjust=False).mean()
    slow = close.ewm(span=20, adjust=False).mean()
    return bool(
        close.iloc[-1] > fast.iloc[-1] > slow.iloc[-1]
        and fast.iloc[-1] > fast.iloc[-2]
        and slow.iloc[-1] > slow.iloc[-2]
    )


def signal_on_closed_bars(df, ticker, group, *, now=None,
                          benchmark_df=None, filters=None):
    """V2 selective BUY: actual bullish 15m cross + one confirming candle.

    Unlike V1, a change to 'full candle above already-aligned EMAs'
    is NOT called a crossover. Only complete IBKR 5m => 15m bars.
    Filters are deliberately selective; performance is not yet backtested.
    """
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        raise ValueError("now must have timezone")
    now = now.tz_convert("UTC")
    bars = build_complete_15m_bars(df, now=now)
    if len(bars) < 28 or "Volume" not in bars:
        return None
    cfg = filters or {}
    min_fast_slope = float(cfg.get("ema9_min_slope_pct", 0.05))
    min_slow_slope = float(cfg.get("ema20_min_slope_pct", 0.01))
    min_volume_ratio = float(cfg.get("min_volume_ratio", 1.25))
    max_extension = float(cfg.get("max_ema9_extension_pct", 2.5))

    curr_time = bars.index[-1]
    age = (now - (curr_time + pd.Timedelta(minutes=15))).total_seconds()
    if age < 0 or age > 900:
        return None
    if curr_time.tz_convert(ET).date() != now.tz_convert(ET).date():
        return None
    # The crossover bar and follow-through bar must BOTH be inside RTH.
    if not _is_rth(curr_time) or not _is_rth(bars.index[-2]):
        return None

    opens, closes = bars["Open"], bars["Close"]
    lows = bars["Low"]
    ema9 = closes.ewm(span=9, adjust=False).mean()
    ema20 = closes.ewm(span=20, adjust=False).mean()

    # ACTUAL EMA9-up-through-EMA20 cross in previous completed 15m bar.
    cross = (
        ema9.iloc[-3] <= ema20.iloc[-3]
        and ema9.iloc[-2] > ema20.iloc[-2]
        and ema9.iloc[-1] > ema20.iloc[-1]
    )
    if not cross:
        return None

    slope9 = (ema9.iloc[-1] / ema9.iloc[-2] - 1.0) * 100.0
    slope20 = (ema20.iloc[-1] / ema20.iloc[-2] - 1.0) * 100.0
    if not (slope9 >= min_fast_slope
            and slope20 >= min_slow_slope and slope9 > slope20):
        return None

    # Confirm bullish follow-through, entire candle body ABOVE both MAs.
    if not (float(closes.iloc[-2]) > float(ema9.iloc[-2])
            and float(closes.iloc[-1]) > float(opens.iloc[-1])
            > float(ema9.iloc[-1]) > float(ema20.iloc[-1])):
        return None
    extension = (closes.iloc[-1] / ema9.iloc[-1] - 1.0) * 100.0
    if extension > max_extension:
        return None

    # Only RTH volume is compared, never misleading overnight volume.
    history = bars.iloc[:-1]
    rth_history = history.loc[[_is_rth(t) for t in history.index]]
    if len(rth_history) < 12:
        return None
    past_vol = pd.to_numeric(
        rth_history["Volume"].iloc[-12:], errors="coerce")
    baseline = float(past_vol.median())
    current_vol = float(bars["Volume"].iloc[-1])
    if baseline <= 0 or current_vol <= 0:
        return None
    volume_ratio = current_vol / baseline
    if volume_ratio < min_volume_ratio:
        return None

    # Group A moves together: do not BUY against a bearish SMH regime.
    if group == "A" and not _benchmark_bullish(
            benchmark_df, curr_time, now):
        return None

    stamp = curr_time.tz_convert(UK)
    return {
        "version": "V2",
        "key": f"{ticker}|{curr_time.isoformat()}|DDB_EMA9_20_15M_V2",
        "timeframe": "15min",
        "ticker": ticker, "group": group,
        "bar_uk": stamp.strftime("%Y-%m-%d %H:%M"),
        "bar_utc": curr_time.isoformat(),
        "open": round(float(opens.iloc[-1]), 4),
        "low": round(float(lows.iloc[-1]), 4),
        "close": round(float(closes.iloc[-1]), 4),
        "ema9": round(float(ema9.iloc[-1]), 4),
        "ema20": round(float(ema20.iloc[-1]), 4),
        "ema9_slope_pct": round(float(slope9), 3),
        "ema20_slope_pct": round(float(slope20), 3),
        "volume_ratio": round(float(volume_ratio), 2),
        "ema9_extension_pct": round(float(extension), 3),
        "sector": "SMH BULLISH" if group == "A" else "OWN TREND",
        "trigger": "REAL CROSS + FOLLOW-THROUGH",
    }


def _daily_gann_ranges(tickers, *, now=None):
    """Daily Yahoo 150-bar ranges, cached by UK day; never guessed on failure."""
    now = datetime.now(UK) if now is None else now
    cache = _load(GANN_CACHE, {})
    today = now.strftime("%Y-%m-%d")
    if cache.get("day") == today and all(
            ticker in cache.get("ranges", {}) for ticker in tickers):
        return cache.get("ranges", {})
    import yfinance as yf
    ranges = {}
    try:
        source = yf.download(
            tickers=" ".join(tickers), period="1y", interval="1d",
            auto_adjust=False, group_by="ticker", threads=True, progress=False,
        )
        for sym in tickers:
            data = source[sym] if isinstance(source.columns, pd.MultiIndex) else (
                source if len(tickers) == 1 else pd.DataFrame())
            if data is None or len(data) < 150:
                continue
            last150 = data[["High", "Low"]].apply(
                pd.to_numeric, errors="coerce").dropna().tail(150)
            if len(last150) != 150:
                continue
            ranges[sym] = [float(last150["Low"].min()),
                           float(last150["High"].max())]
    except Exception as exc:
        print("RUDRA DDB | GANN daily data unavailable:", type(exc).__name__)
    # Cache partial results only; next cycle retries any missing names.
    if ranges:
        _save(GANN_CACHE, {"day": today, "ranges": ranges, "provider": "Yahoo 1D"})
    return ranges


def _queue(events):
    if not events:
        return
    state = _load(STATE, {"pending": [], "sent": []})
    sent = set(state.get("sent", []))
    pending = {e["key"]: e for e in state.get("pending", [])}
    for item in events:
        if item["key"] not in sent:
            pending[item["key"]] = item
    state["pending"] = list(pending.values())[-100:]
    state["sent"] = list(sent)[-1500:]
    _save(STATE, state)


def run_cycle(app, *, now=None):
    if app is None:
        raise RuntimeError("Requires existing Chakra IBKR app")
    cfg, items = config()
    from ASJR_Analyst.Utils import asjr_ibkr as ibkr
    names = [sym for sym, _ in items]
    # Group A needs sector agreement. Extra symbol is context, not a DDB alert.
    benchmark_symbol = str(
        cfg.get("signal_filters", {}).get("group_a_benchmark", "SMH")).upper()
    requested = names + ([benchmark_symbol] if benchmark_symbol not in names else [])
    started = time.monotonic()
    print("RUDRA DDB 15M | START | A/B/C=22/17/10 |",
          pd.Timestamp.now(tz="UTC").isoformat(), flush=True)
    batches = ibkr.get_ibkr_5m_batch(
        app, requested, duration="3 D", wait_time=16, batch_size=5)
    # Use the actual post-fetch time. A 49-symbol fetch may take minutes;
    # never compare completed candles against the start-of-round clock.
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    received = sum(batches.get(sym) is not None and not batches[sym].empty
                   for sym in names)
    detected = []
    for sym, group in items:
        event = signal_on_closed_bars(
            batches.get(sym), sym, group, now=now,
            benchmark_df=batches.get(benchmark_symbol) if group == "A" else None,
            filters=cfg.get("signal_filters", {}))
        if event:
            detected.append(event)
    if detected:
        ranges = _daily_gann_ranges(names, now=now.tz_convert(UK).to_pydatetime())
        for item in detected:
            lowhigh = ranges.get(item["ticker"])
            item["gann"] = (
                gann_levels(item["close"], *lowhigh) if lowhigh else [])
        _queue(detected)
    seconds = time.monotonic() - started
    benchmark_ok = (batches.get(benchmark_symbol) is not None
                    and not batches[benchmark_symbol].empty)
    print("RUDRA DDB V2 15M | requested=%d | received=%d | "
          "benchmark_%s=%s | matches=%d | duration=%.1fs" %
          (len(names), received, benchmark_symbol, benchmark_ok,
           len(detected), seconds), flush=True)
    return {
        "alert_mode": "ddb_ema_gann_15m_v2", "ddb_alerts": detected,
        "ddb_requested": len(names), "ddb_received": received,
        "ddb_elapsed_seconds": round(seconds, 2),
        "alert_data": [], "rudra_reversal_alerts": [],
        "rudra_premarket_events": [], "alerts_dispatched": False,
        "snapshot": {"trade_date": now.tz_convert(ET).strftime("%Y-%m-%d")},
        "git": {"status": "DDB_ONLY_NO_DATALAKE_SUBMISSION"},
    }


_PREPARED = []


def prepare_alert(result=None):
    """Format one Discord-sized batch; state is ACKed only after send."""
    global _PREPARED
    _PREPARED = []
    state = _load(STATE, {"pending": [], "sent": []})
    pending = state.get("pending", [])
    if not pending:
        return ""
    now = pd.Timestamp.now(tz="UTC")
    lines = []
    for event in pending:
        stamp = pd.Timestamp(event["bar_utc"])
        if (event.get("version") != "V2"
                or event.get("timeframe") != "15min"
                or (now - stamp).total_seconds() > 1800):
            continue
        section = [
            f'{event["ticker"]} | {event["bar_uk"]} UK '
            '(15min, TRUE EMA9/20 CROSS + CONFIRM)',
            f'EMA9 slope +{event["ema9_slope_pct"]:.3f}% | '
            f'EMA20 slope +{event["ema20_slope_pct"]:.3f}% | '
            f'Vol {event["volume_ratio"]:.2f}x | {event["sector"]}',
            'GANN LEVEL:',
        ]
        if event.get("gann"):
            section.extend(("🔴 MAIN " if typ == "MAIN" else "🟢 MID  ") +
                           f'{value:.2f}' for value, typ in event["gann"])
        else:
            section.append("GANN UNAVAILABLE (150 daily bars needed)")
        section.append("----")
        candidate = "\n".join(lines + section) + "\n"
        if len(candidate) > 1750:
            break
        lines.extend(section)
        _PREPARED.append(event["key"])
    if not _PREPARED:
        return ""
    return "\n".join(lines)


def mark_alert_sent():
    """Invoked only after the EXISTING Discord sender reports success."""
    global _PREPARED
    if not _PREPARED:
        return False
    state = _load(STATE, {"pending": [], "sent": []})
    keys = set(_PREPARED)
    state["sent"] = list(dict.fromkeys(state.get("sent", []) + list(keys)))[-1500:]
    state["pending"] = [e for e in state.get("pending", [])
                        if e["key"] not in keys
                        and (pd.Timestamp.now(tz="UTC") -
                             pd.Timestamp(e["bar_utc"])).total_seconds() <= 1800]
    _save(STATE, state)
    _PREPARED = []
    return True
