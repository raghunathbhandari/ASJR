"""Stateful five-minute upper/lower wick alerts for Chakra."""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from Utils.asjr_day import session_date


ET = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")
ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "wick_alert_state.json"
BATCH_FILE = ROOT / "wick_alert_batch.json"
CODE_FENCE = chr(96) * 3

STATE_SCHEMA_VERSION = 4
WICK_MIN_PRICE_PCT = 2.00
WICK_MAX_BODY_PCT = 1.00


def _read_json(path, default):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value
    except (OSError, ValueError, TypeError):
        return default


def _write_json_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temp, path)


def _event_key(event):
    return (
        f'{event["ticker"]}|{event["bar_time_et"]}|'
        f'{event["type"]}|{event["event"]}'
    )


def _new_state(day, seed_latest=False):
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "session_date": day,
        "last_processed": {},
        "pending": [],
        "seed_latest": bool(seed_latest),
    }


def _load_state(path, day):
    state = _read_json(path, None)

    # One-time schema migration for 2026.10.01.4:
    # discard the old pending batch and replay the current session from
    # the first available completed candle using the locked wick rule.
    if isinstance(state, dict) and state.get("schema_version") != STATE_SCHEMA_VERSION:
        return _new_state(day, seed_latest=False)

    # If state is genuinely missing/corrupt, start fresh from the latest
    # completed candle to avoid accidental historical replay.
    if not isinstance(state, dict):
        return _new_state(day, seed_latest=True)

    # Normal new trading day: preserve no-miss behavior by allowing the
    # session to be processed from its first available completed candle.
    if state.get("session_date") != day:
        return _new_state(day, seed_latest=False)

    state.setdefault("last_processed", {})
    state.setdefault("pending", [])
    state.setdefault("seed_latest", False)
    return state


def _volume_context(prior, volume):
    baseline = pd.to_numeric(prior["volume"], errors="coerce").dropna()
    baseline = baseline[baseline > 0]
    volume_x = volume / baseline.median() if len(baseline) >= 5 else None
    return round(volume_x, 2) if pd.notna(volume_x) else None


def _wick_event(ticker, frame, idx, side):
    row = frame.iloc[idx]
    open_price = float(row["open"])
    high = float(row["high"])
    low = float(row["low"])
    close = float(row["close"])
    volume = float(row["volume"])

    candle_range = high - low
    if candle_range <= 0 or close <= 0:
        return None

    body = abs(close - open_price)
    wick = (
        min(open_price, close) - low
        if side == "LOWER"
        else high - max(open_price, close)
    )
    range_pct = candle_range / close * 100.0
    wick_share = wick / candle_range
    wick_price_pct = wick / close * 100.0
    body_pct = body / close * 100.0

    prior = frame.iloc[max(0, idx - 12):idx]

    # Locked liquidity-sweep filter:
    #   wick itself must be >= 2% of price
    #   real body must be <= 1% of price
    if wick_price_pct < WICK_MIN_PRICE_PCT:
        return None
    if body_pct > WICK_MAX_BODY_PCT:
        return None

    prior_low = pd.to_numeric(prior["low"], errors="coerce").min()
    prior_high = pd.to_numeric(prior["high"], errors="coerce").max()

    if side == "LOWER":
        prior_level = float(prior_low) if pd.notna(prior_low) else None
        swept = (
            bool(low < prior_low and close > prior_low)
            if pd.notna(prior_low)
            else False
        )
        event_type = "LOWER_WICK"
        event_name = "LONG LOWER WICK"
    else:
        prior_level = float(prior_high) if pd.notna(prior_high) else None
        swept = (
            bool(high > prior_high and close < prior_high)
            if pd.notna(prior_high)
            else False
        )
        event_type = "UPPER_WICK"
        event_name = "LONG UPPER WICK"

    next_row = frame.iloc[idx + 1] if idx + 1 < len(frame) else None
    next_confirmed = None
    if next_row is not None:
        next_confirmed = (
            bool(float(next_row["low"]) > low)
            if side == "LOWER"
            else bool(float(next_row["high"]) < high)
        )

    bar_time = row["bar_et"]
    return {
        "type": event_type,
        "ticker": str(ticker),
        "bar_time_et": bar_time.strftime("%Y-%m-%d %H:%M ET"),
        "event": event_name,
        "session": (
            "RTH"
            if (9, 30) <= (bar_time.hour, bar_time.minute) < (16, 0)
            else "EXTENDED"
        ),
        "open": open_price,
        "high": high,
        "low": low,
        "price": close,
        "volume": volume,
        "volume_x": _volume_context(prior, volume),
        "wick": wick,
        "wick_pct": wick_price_pct,
        "wick_share_pct": wick_share * 100.0,
        "body_pct": body_pct,
        "range_pct": range_pct,
        "prior_level": prior_level,
        "swept_reclaimed": swept,
        "next_confirmed": next_confirmed,
    }


def build_wick_alerts(
    intraday,
    trade_date=None,
    now=None,
    state_file=STATE_FILE,
):
    """Scan every completed candle not yet processed and persist pending wicks.

    The per-ticker last_processed marker survives bot restarts. If Chakra is
    stopped, the next run loads IBKR history and catches up every completed bar
    after the saved marker. Pending wick events survive until delivery is
    explicitly acknowledged by mark_alert_sent().
    """
    if intraday is None or intraday.empty:
        return []

    now_et = pd.Timestamp(now if now is not None else datetime.now(ET))
    now_et = (
        now_et.tz_localize(ET)
        if now_et.tzinfo is None
        else now_et.tz_convert(ET)
    )
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

    for ticker, original in intraday.groupby("ticker"):
        frame = original.sort_values("datetime").copy()
        dates = pd.to_datetime(frame["datetime"], utc=True).dt.tz_convert(ET)
        frame["bar_et"] = dates
        frame = frame[
            (dates.map(session_date).astype(str) == day)
            & (dates + pd.Timedelta(minutes=5) <= now_et)
        ].copy()

        if frame.empty:
            continue

        if state.get("seed_latest"):
            state["last_processed"][str(ticker)] = (
                frame.iloc[-1]["bar_et"].isoformat()
            )
            continue

        marker_text = state["last_processed"].get(str(ticker))
        marker = pd.Timestamp(marker_text) if marker_text else None
        if marker is not None:
            marker = (
                marker.tz_localize(ET)
                if marker.tzinfo is None
                else marker.tz_convert(ET)
            )

        for idx in range(len(frame)):
            bar_time = frame.iloc[idx]["bar_et"]
            if marker is not None and bar_time <= marker:
                continue

            for side in ("LOWER", "UPPER"):
                event = _wick_event(ticker, frame, idx, side)
                if event is not None:
                    pending_by_key.setdefault(_event_key(event), event)

        latest_bar = frame.iloc[-1]["bar_et"]
        state["last_processed"][str(ticker)] = latest_bar.isoformat()

    state["seed_latest"] = False
    state["pending"] = sorted(
        pending_by_key.values(),
        key=lambda e: (e["bar_time_et"], e["ticker"], e["type"]),
    )
    _write_json_atomic(state_file, state)
    return list(state["pending"])


# Backward compatibility only; this performs wick detection, not EMA logic.
def build_ema20_alerts(intraday, trade_date=None, now=None):
    return build_wick_alerts(intraday, trade_date=trade_date, now=now)


def prepare_alert(
    result,
    state_file=STATE_FILE,
    batch_file=BATCH_FILE,
):
    """Format the oldest pending wick batch; do not acknowledge it yet."""
    events = result.get("alert_data", []) if result else []
    events = [
        event
        for event in events
        if event.get("type") in {"LOWER_WICK", "UPPER_WICK"}
    ]
    if not events:
        return ""

    header = "ASJR 5M WICK ALERTS | candle times UK\n"
    blocks = []
    prepared_keys = []

    for event in events:
        bar_time_uk = (
            datetime.strptime(event["bar_time_et"], "%Y-%m-%d %H:%M ET")
            .replace(tzinfo=ET)
            .astimezone(UK)
            .strftime("%Y-%m-%d %H:%M %Z")
        )
        volume = (
            f'{event["volume_x"]:.1f}x prior 12-bar median'
            if event.get("volume_x") is not None
            else "comparison unavailable"
        )
        prior_level = (
            f'{event["prior_level"]:.2f}'
            if event.get("prior_level") is not None
            else "n/a"
        )
        sweep = "YES" if event.get("swept_reclaimed") else "NO"

        if event["type"] == "LOWER_WICK":
            label = "LONG LOWER WICK"
            level_name = "12-bar low"
            next_state = (
                "waiting next candle"
                if event.get("next_confirmed") is None
                else (
                    "held low / higher low"
                    if event.get("next_confirmed")
                    else "low not confirmed"
                )
            )
        else:
            label = "LONG UPPER WICK"
            level_name = "12-bar high"
            next_state = (
                "waiting next candle"
                if event.get("next_confirmed") is None
                else (
                    "held high / lower high"
                    if event.get("next_confirmed")
                    else "high not confirmed"
                )
            )

        block = (
            f'\n{event["ticker"]} {label} [{event["session"]}] {bar_time_uk}\n'
            f'O {event["open"]:.2f} H {event["high"]:.2f} '
            f'L {event["low"]:.2f} C {event["price"]:.2f}\n'
            f'Wick {event["wick"]:.2f} '
            f'({event["wick_pct"]:.2f}% price) | '
            f'Body {event.get("body_pct", 0.0):.2f}% | '
            f'{level_name} {prior_level} swept/reclaimed: {sweep}\n'
            f'Vol {event["volume"]:,.0f} ({volume}) | Next: {next_state}\n'
        )

        candidate = CODE_FENCE + "\n" + header + "".join(blocks) + block + CODE_FENCE
        if len(candidate) > 1900:
            break

        blocks.append(block)
        prepared_keys.append(_event_key(event))

    if not blocks:
        return ""

    _write_json_atomic(batch_file, {"event_keys": prepared_keys})
    return CODE_FENCE + "\n" + header + "".join(blocks) + CODE_FENCE


def mark_alert_sent(
    state_file=STATE_FILE,
    batch_file=BATCH_FILE,
):
    """Acknowledge only the batch confirmed sent to Discord."""
    batch = _read_json(batch_file, {})
    keys = set(batch.get("event_keys", [])) if isinstance(batch, dict) else set()
    if not keys:
        return 0

    state = _read_json(state_file, {})
    if not isinstance(state, dict):
        return 0

    before = list(state.get("pending", []))
    after = [
        event
        for event in before
        if _event_key(event) not in keys
    ]
    state["pending"] = after
    _write_json_atomic(state_file, state)

    try:
        Path(batch_file).unlink()
    except OSError:
        pass

    return len(before) - len(after)
