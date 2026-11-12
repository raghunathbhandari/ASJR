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
    result = grouped.agg({"Open": "first", "High": "max",
                          "Low": "min", "Close": "last"})
    # Independently enforce the 15m closing timestamp.
    return result[(result.index + pd.Timedelta(minutes=15)) <= now]


def signal_on_closed_bars(df, ticker, group, *, now=None):
    """Check full 15m candle body above 15m EMA9 > EMA20 on a new transition."""
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        raise ValueError("now must have timezone")
    now = now.tz_convert("UTC")
    bars = build_complete_15m_bars(df, now=now)
    if len(bars) < 26:
        return None
    opens = bars["Open"]
    closes = bars["Close"]
    lows = bars["Low"]
    ema9 = closes.ewm(span=9, adjust=False).mean()
    ema20 = closes.ewm(span=20, adjust=False).mean()
    curr_time = bars.index[-1]
    age = (now - (curr_time + pd.Timedelta(minutes=15))).total_seconds()
    if age < 0 or age > 900:
        return None
    if curr_time.tz_convert(ET).date() != now.tz_convert(ET).date():
        return None
    curr = (min(float(opens.iloc[-1]), float(closes.iloc[-1])) >
            float(ema9.iloc[-1]) > float(ema20.iloc[-1]))
    prev = (min(float(opens.iloc[-2]), float(closes.iloc[-2])) >
            float(ema9.iloc[-2]) > float(ema20.iloc[-2]))
    if not curr or prev:
        return None
    stamp = curr_time.tz_convert(UK)
    return {
        "key": f"{ticker}|{curr_time.isoformat()}|DDB_EMA9_20_15M",
        "timeframe": "15min",
        "ticker": ticker, "group": group,
        "bar_uk": stamp.strftime("%Y-%m-%d %H:%M"),
        "bar_utc": curr_time.isoformat(),
        "open": round(float(opens.iloc[-1]), 4),
        "low": round(float(lows.iloc[-1]), 4),
        "close": round(float(closes.iloc[-1]), 4),
        "ema9": round(float(ema9.iloc[-1]), 4),
        "ema20": round(float(ema20.iloc[-1]), 4),
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
    started = time.monotonic()
    print("RUDRA DDB 15M | START | A/B/C=22/17/10 |",
          pd.Timestamp.now(tz="UTC").isoformat(), flush=True)
    batches = ibkr.get_ibkr_5m_batch(
        app, names, duration="3 D", wait_time=16, batch_size=5)
    # Use the actual post-fetch time. A 49-symbol fetch may take minutes;
    # never compare completed candles against the start-of-round clock.
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    received = sum(batches.get(sym) is not None and not batches[sym].empty
                   for sym in names)
    detected = []
    for sym, group in items:
        event = signal_on_closed_bars(batches.get(sym), sym, group, now=now)
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
    print("RUDRA DDB 15M | requested=%d | received=%d | matches=%d | "
          "duration=%.1fs" % (len(names), received, len(detected), seconds),
          flush=True)
    return {
        "alert_mode": "ddb_ema_gann_5m", "ddb_alerts": detected,
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
        if event.get("timeframe") != "15min" or (now - stamp).total_seconds() > 1800:
            continue
        section = [
            f'{event["ticker"]} | {event["bar_uk"]} UK (15min, EMA Crossed)',
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
