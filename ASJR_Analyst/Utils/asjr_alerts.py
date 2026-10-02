"""Stateful five-minute upper/lower wick alerts for Chakra."""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from Utils.asjr_day import session_date
from Strategies.MeanReversal4Pct import mean_reversal


ET = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")
ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "wick_alert_state.json"
BATCH_FILE = ROOT / "wick_alert_batch.json"
CONFIG_FILE = ROOT / "config" / "wick_setups.json"
CODE_FENCE = chr(96) * 3

STATE_SCHEMA_VERSION = 3


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


def _load_wick_setups(path=CONFIG_FILE):
    """Load enabled wick setups fresh on every pipeline run."""
    config = _read_json(path, {})
    setups = config.get("setups", []) if isinstance(config, dict) else []
    return [
        setup
        for setup in setups
        if isinstance(setup, dict)
        and setup.get("enabled", True)
        and setup.get("id")
    ]


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

    # A detector-rule/schema change intentionally discards the old pending
    # backlog and seeds processing from the newest completed candle.
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != STATE_SCHEMA_VERSION
    ):
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


def _wick_event(ticker, frame, idx, side, setups):
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
    if wick <= 0:
        return None

    range_pct = candle_range / close * 100.0
    wick_share = wick / candle_range
    wick_price_pct = wick / close * 100.0
    body_pct = body / close * 100.0

    matched_setup = None
    matched_prior = None
    prior_level = None
    swept = False
    lookback_bars = 12

    # JSON order is priority order. One candle-side emits at most one setup.
    for setup in setups:
        setup_side = str(setup.get("side", "BOTH")).upper()
        if setup_side not in {"BOTH", side}:
            continue

        try:
            min_wick_pct = float(setup.get("min_wick_pct", 0.0))
            max_body_pct = setup.get("max_body_pct")
            max_body_pct = (
                float(max_body_pct) if max_body_pct is not None else None
            )
            lookback_bars = max(1, int(setup.get("lookback_bars", 12)))
            min_prior_bars = max(0, int(setup.get("min_prior_bars", 0)))
        except (TypeError, ValueError):
            continue

        if wick_price_pct < min_wick_pct:
            continue
        if max_body_pct is not None and body_pct > max_body_pct:
            continue

        prior = frame.iloc[max(0, idx - lookback_bars):idx]
        if len(prior) < min_prior_bars:
            continue

        prior_low = pd.to_numeric(prior["low"], errors="coerce").min()
        prior_high = pd.to_numeric(prior["high"], errors="coerce").max()

        if side == "LOWER":
            level = float(prior_low) if pd.notna(prior_low) else None
            is_sweep = (
                bool(low < prior_low and close > prior_low)
                if pd.notna(prior_low)
                else False
            )
        else:
            level = float(prior_high) if pd.notna(prior_high) else None
            is_sweep = (
                bool(high > prior_high and close < prior_high)
                if pd.notna(prior_high)
                else False
            )

        if setup.get("require_reclaim", False) and not is_sweep:
            continue

        matched_setup = setup
        matched_prior = prior
        prior_level = level
        swept = is_sweep
        break

    if matched_setup is None:
        return None

    next_row = frame.iloc[idx + 1] if idx + 1 < len(frame) else None
    next_confirmed = None
    if next_row is not None:
        next_confirmed = (
            bool(float(next_row["low"]) > low)
            if side == "LOWER"
            else bool(float(next_row["high"]) < high)
        )

    event_type = "LOWER_WICK" if side == "LOWER" else "UPPER_WICK"
    setup_label = str(matched_setup.get("label", matched_setup["id"])).upper()
    event_name = setup_label

    bar_time = row["bar_et"]
    return {
        "type": event_type,
        "setup_id": str(matched_setup["id"]),
        "setup_label": setup_label,
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
        "volume_x": _volume_context(matched_prior, volume),
        "wick": wick,
        "wick_pct": wick_price_pct,
        "wick_share_pct": wick_share * 100.0,
        "body_pct": body_pct,
        "range_pct": range_pct,
        "lookback_bars": lookback_bars,
        "prior_level": prior_level,
        "swept_reclaimed": swept,
        "next_confirmed": next_confirmed,
    }


def build_wick_alerts(
    intraday,
    trade_date=None,
    now=None,
    state_file=STATE_FILE,
    config_file=CONFIG_FILE,
):
    """Scan every completed candle not yet processed and persist pending wicks.

    The per-ticker last_processed marker survives bot restarts. If Chakra is
    stopped, the next run loads IBKR history and catches up every completed bar
    after the saved marker. Pending wick events survive until delivery is
    explicitly acknowledged by mark_alert_sent().
    """
    if intraday is None or intraday.empty:
        return []

    setups = _load_wick_setups(config_file)
    if not setups:
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
                event = _wick_event(ticker, frame, idx, side, setups)
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
    """Format mean-reversal first; otherwise format oldest pending wick batch."""
    mean_message = mean_reversal.prepare_alert(result)
    if mean_message:
        return mean_message

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
            label = event.get("setup_label", "LOWER WICK")
            level_name = f'{event.get("lookback_bars", 12)}-bar low'
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
            label = event.get("setup_label", "UPPER WICK")
            level_name = f'{event.get("lookback_bars", 12)}-bar high'
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
    if mean_reversal.has_prepared_batch():
        return mean_reversal.mark_alert_sent()

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
