"""4% mean-reversal alert strategy.

Reference: previous completed DAILY close.
Trigger: first newly completed 5-minute candle in the US trading session whose
close is <= -4.0% versus that reference close.
Alert levels: 1% stop loss and 4% take profit from the detected candle close.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from Utils.asjr_day import session_date

ET = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")

ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT / "mean_reversal_alert_state.json"
BATCH_FILE = ROOT / "mean_reversal_alert_batch.json"

STATE_SCHEMA_VERSION = 1
DROP_TRIGGER_PCT = -4.0
STOP_PCT = 1.0
TARGET_PCT = 4.0

STRATEGY_TICKERS = ("MU", "CAT", "TSLA", "AMAT", "INTC", "LRCX")


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write_json_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temp, path)


def _new_state(day, seed_latest=False):
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "session_date": day,
        "last_processed": {},
        "triggered": {},
        "pending": [],
        "seed_latest": bool(seed_latest),
    }


def _load_state(path, day):
    state = _read_json(path, None)
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != STATE_SCHEMA_VERSION
    ):
        # First deployment: do not backfill old intraday signals.
        return _new_state(day, seed_latest=True)

    if state.get("session_date") != day:
        # New trading day: process all completed bars so a restart cannot miss
        # an early-session threshold cross.
        return _new_state(day, seed_latest=False)

    state.setdefault("last_processed", {})
    state.setdefault("triggered", {})
    state.setdefault("pending", [])
    state.setdefault("seed_latest", False)
    return state


def _event_key(event):
    return f'{event["ticker"]}|{event["bar_time_et"]}|MEAN_REVERSAL_4PCT'


def _previous_completed_close(daily, ticker, day):
    if daily is None or daily.empty:
        return None

    frame = daily[daily["ticker"].astype(str).str.upper() == ticker].copy()
    if frame.empty:
        return None

    frame["date_norm"] = pd.to_datetime(frame["date"]).dt.date
    prior = frame[frame["date_norm"] < pd.Timestamp(day).date()].sort_values("date_norm")
    if prior.empty:
        return None

    value = pd.to_numeric(prior.iloc[-1]["close"], errors="coerce")
    return float(value) if pd.notna(value) and float(value) > 0 else None


def build_mean_reversal_alerts(
    daily,
    intraday,
    trade_date=None,
    now=None,
    state_file=STATE_FILE,
):
    """Build/persist first -4% threshold-cross alert per ticker per trading day."""
    if intraday is None or intraday.empty or daily is None or daily.empty:
        return []

    now_et = pd.Timestamp(now if now is not None else datetime.now(ET))
    now_et = now_et.tz_localize(ET) if now_et.tzinfo is None else now_et.tz_convert(ET)

    day = (
        str(trade_date)[:10]
        if trade_date is not None
        else session_date(now_et).isoformat()
    )
    state = _load_state(state_file, day)

    pending_by_key = {
        _event_key(event): event
        for event in state.get("pending", [])
        if isinstance(event, dict)
    }

    for ticker in STRATEGY_TICKERS:
        if ticker in state.get("triggered", {}):
            continue

        ref_close = _previous_completed_close(daily, ticker, day)
        if ref_close is None:
            continue

        original = intraday[intraday["ticker"].astype(str).str.upper() == ticker].copy()
        if original.empty:
            continue

        dates = pd.to_datetime(original["datetime"], utc=True).dt.tz_convert(ET)
        original["bar_et"] = dates
        frame = original[
            (dates.map(session_date).astype(str) == day)
            & (dates + pd.Timedelta(minutes=5) <= now_et)
        ].sort_values("bar_et").copy()

        if frame.empty:
            continue

        if state.get("seed_latest"):
            # Begin live monitoring from the newest completed candle.
            state["last_processed"][ticker] = frame.iloc[-1]["bar_et"].isoformat()
            continue

        marker_text = state["last_processed"].get(ticker)
        marker = pd.Timestamp(marker_text) if marker_text else None
        if marker is not None:
            marker = marker.tz_localize(ET) if marker.tzinfo is None else marker.tz_convert(ET)

        prior_move = 0.0
        if marker is not None:
            older = frame[frame["bar_et"] <= marker]
            if not older.empty:
                prior_move = (float(older.iloc[-1]["close"]) / ref_close - 1.0) * 100.0

        new_rows = frame if marker is None else frame[frame["bar_et"] > marker]

        for _, row in new_rows.iterrows():
            close = float(row["close"])
            move_pct = (close / ref_close - 1.0) * 100.0

            # First completed 5-minute close crossing from above -4% to -4% or lower.
            if prior_move > DROP_TRIGGER_PCT and move_pct <= DROP_TRIGGER_PCT:
                event = {
                    "type": "MEAN_REVERSAL_4PCT",
                    "ticker": ticker,
                    "bar_time_et": row["bar_et"].strftime("%Y-%m-%d %H:%M ET"),
                    "reference_close": ref_close,
                    "detected_price": close,
                    "move_pct": move_pct,
                    "sl": close * (1.0 - STOP_PCT / 100.0),
                    "tp": close * (1.0 + TARGET_PCT / 100.0),
                }
                pending_by_key.setdefault(_event_key(event), event)
                state["triggered"][ticker] = event["bar_time_et"]
                break

            prior_move = move_pct

        state["last_processed"][ticker] = frame.iloc[-1]["bar_et"].isoformat()

    state["seed_latest"] = False
    state["pending"] = sorted(
        pending_by_key.values(),
        key=lambda e: (e["bar_time_et"], e["ticker"]),
    )
    _write_json_atomic(state_file, state)
    return list(state["pending"])


def prepare_alert(result, state_file=STATE_FILE, batch_file=BATCH_FILE):
    events = result.get("mean_reversal_alerts", []) if result else []
    events = [e for e in events if e.get("type") == "MEAN_REVERSAL_4PCT"]
    if not events:
        return ""

    blocks = []
    keys = []
    for event in events:
        uk_time = (
            datetime.strptime(event["bar_time_et"], "%Y-%m-%d %H:%M ET")
            .replace(tzinfo=ET)
            .astimezone(UK)
            .strftime("%Y-%m-%d %H:%M %Z")
        )
        block = (
            "4% Mean Reversal:\n"
            f'Ticker: {event["ticker"]}\n'
            f'Detected Candle: {uk_time}\n'
            f'SL: {event["sl"]:.2f}\n'
            f'TP: {event["tp"]:.2f}\n'
        )
        candidate = "\n".join(blocks + [block])
        if len(candidate) > 1900:
            break
        blocks.append(block)
        keys.append(_event_key(event))

    if not blocks:
        return ""

    _write_json_atomic(batch_file, {"event_keys": keys})
    return "\n".join(blocks)


def has_prepared_batch(batch_file=BATCH_FILE):
    batch = _read_json(batch_file, {})
    return bool(isinstance(batch, dict) and batch.get("event_keys"))


def mark_alert_sent(state_file=STATE_FILE, batch_file=BATCH_FILE):
    batch = _read_json(batch_file, {})
    keys = set(batch.get("event_keys", [])) if isinstance(batch, dict) else set()
    if not keys:
        return 0

    state = _read_json(state_file, {})
    if not isinstance(state, dict):
        return 0

    before = list(state.get("pending", []))
    after = [event for event in before if _event_key(event) not in keys]
    state["pending"] = after
    _write_json_atomic(state_file, state)

    try:
        Path(batch_file).unlink()
    except OSError:
        pass

    return len(before) - len(after)
