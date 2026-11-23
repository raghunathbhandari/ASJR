"""Rudra DDB A/B/C: fifteen-minute EMA9/EMA20 BUY WATCH alerts.

Runs exclusively through the existing Chakra IBKR app and Discord hook.
No orders, independent broker connection, new scheduler, or legacy alerts.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "RudraScanner" / "ddb_ema_gann_config.json"
STATE = ROOT / "ASJR_Analyst" / "state" / "ddb_ema_gann_alerts.json"
DDB_ALERT_MODE = "ddb_ema_gann_15m_v2"  # Stable dispatch identifier
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


def _session_name(ts):
    """Identify the US stock session from a timestamp in New York local time."""
    t = ts.tz_convert(ET)
    minute = t.hour * 60 + t.minute
    if 570 <= minute < 960:
        return "RTH"
    if 240 <= minute < 570:
        return "PREMARKET"
    if 960 <= minute < 1200:
        return "AFTERHOURS"
    return "OVERNIGHT"


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
    if len(bars) < 28:
        return None
    cfg = filters or {}
    min_fast_slope = float(cfg.get("ema9_min_slope_pct", 0.05))
    min_slow_slope = float(cfg.get("ema20_min_slope_pct", 0.01))
    max_extension = float(cfg.get("max_ema9_extension_pct", 2.5))

    curr_time = bars.index[-1]
    age = (now - (curr_time + pd.Timedelta(minutes=15))).total_seconds()
    if age < 0 or age > 900:
        return None
    # Cross and confirmation must be contiguous 15m bars, including across
    # midnight. Never infer a crossover across a missing/closed-market gap.
    if ((bars.index[-1] - bars.index[-2]) != pd.Timedelta(minutes=15)
            or (bars.index[-2] - bars.index[-3]) != pd.Timedelta(minutes=15)):
        return None
    session = _session_name(curr_time)

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

    # Group A: retain the strict SMH filter during regular hours.
    # In extended sessions, SMART may not publish an SMH candle at the
    # stock's timestamp. If SMH is available, require it to be bullish;
    # otherwise disclose the unconfirmed sector rather than hide all signals.
    sector = "OWN TREND"
    if group == "A":
        if benchmark_df is None or benchmark_df.empty:
            benchmark_ready = False
        else:
            sbars = build_complete_15m_bars(benchmark_df, now=now)
            benchmark_ready = len(sbars) >= 28 and sbars.index[-1] == curr_time
        if benchmark_ready:
            if not _benchmark_bullish(benchmark_df, curr_time, now):
                return None
            sector = "SMH BULLISH"
        elif session == "RTH":
            return None
        else:
            sector = "SMH UNAVAILABLE (EXTENDED)"

    stamp = curr_time.tz_convert(UK)
    return {
        "version": "V2",
        "key": f"{ticker}|{curr_time.isoformat()}|DDB_EMA9_20_15M_V2",
        "timeframe": "15min",
        "ticker": ticker, "group": group,
        "session": session,
        "bar_uk": stamp.strftime("%Y-%m-%d %H:%M"),
        "bar_utc": curr_time.isoformat(),
        "open": round(float(opens.iloc[-1]), 4),
        "low": round(float(lows.iloc[-1]), 4),
        "close": round(float(closes.iloc[-1]), 4),
        "ema9": round(float(ema9.iloc[-1]), 4),
        "ema20": round(float(ema20.iloc[-1]), 4),
        "ema9_slope_pct": round(float(slope9), 3),
        "ema20_slope_pct": round(float(slope20), 3),
        "ema9_extension_pct": round(float(extension), 3),
        "sector": sector,
        "trigger": "REAL CROSS + FOLLOW-THROUGH",
    }


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
    print("RUDRA DDB 15M | START | ALL SESSIONS | A/B/C=22/17/10 |",
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
        _queue(detected)
    seconds = time.monotonic() - started
    benchmark_ok = (batches.get(benchmark_symbol) is not None
                    and not batches[benchmark_symbol].empty)
    print("RUDRA DDB V2 15M | requested=%d | received=%d | "
          "benchmark_%s=%s | matches=%d | duration=%.1fs" %
          (len(names), received, benchmark_symbol, benchmark_ok,
           len(detected), seconds), flush=True)
    return {
        "alert_mode": DDB_ALERT_MODE, "ddb_alerts": detected,
        "ddb_requested": len(names), "ddb_received": received,
        "ddb_elapsed_seconds": round(seconds, 2),
        "alert_data": [], "rudra_reversal_alerts": [],
        "rudra_premarket_events": [], "alerts_dispatched": False,
        "snapshot": {"trade_date": now.tz_convert(ET).strftime("%Y-%m-%d")},
        "git": {"status": "DDB_ONLY_NO_DATALAKE_SUBMISSION"},
    }


def format_buy_watch_section(event):
    """15m EMA BUY WATCH only; neither volume nor Gann is a signal requirement."""
    ticker = event["ticker"]
    group = event["group"]
    close = float(event["close"])
    ema9 = float(event["ema9"])
    ema20 = float(event["ema20"])
    slope9 = float(event["ema9_slope_pct"])
    slope20 = float(event["ema20_slope_pct"])
    sector = event.get("sector", "NOT CHECKED")
    return [
        f'🟢 {ticker} | GROUP {group} | BUY WATCH (V2)',
        f'{event["bar_uk"]} UK | 15min | {event.get("session", "UNKNOWN")} | EMA9/20 CROSS CONFIRMED',
        f'ENTRY REF (15m close): {close:.2f} | NOT AN EXECUTED ORDER',
        f'EMA9: {ema9:.2f} | slope {slope9:+.3f}% / 15m',
        f'EMA20: {ema20:.2f} | slope {slope20:+.3f}% / 15m',
        f'Sector: {sector}',
        '----',
    ]


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
        section = format_buy_watch_section(event)
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
