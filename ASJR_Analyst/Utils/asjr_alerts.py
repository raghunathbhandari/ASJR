"""Stateful five-minute upper/lower wick alerts for Chakra."""

import json
import math
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

STATE_SCHEMA_VERSION = 6


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

    if not all(math.isfinite(v) for v in (open_price, high, low, close, volume)):
        return None
    if low > min(open_price, close) or high < max(open_price, close) or volume <= 0:
        return None

    candle_range = high - low
    if candle_range <= 0 or close <= 0:
        return None

    body = abs(close - open_price)
    lower_wick = min(open_price, close) - low
    upper_wick = high - max(open_price, close)
    wick = lower_wick if side == "LOWER" else upper_wick
    opposite_wick = upper_wick if side == "LOWER" else lower_wick
    if wick <= 0:
        return None

    range_pct = candle_range / close * 100.0
    wick_share = wick / candle_range
    wick_share_pct = wick_share * 100.0
    wick_price_pct = wick / close * 100.0
    body_pct = body / close * 100.0
    wick_body_ratio = float("inf") if body <= 0 else wick / body
    wick_opposite_ratio = (
        float("inf") if opposite_wick <= 0 else wick / opposite_wick
    )

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
            min_range_pct = float(setup.get("min_range_pct", 0.0))
            min_wick_pct = float(setup.get("min_wick_pct", 0.0))
            min_wick_share_pct = float(setup.get("min_wick_share_pct", 0.0))
            min_opposite_share_pct = float(setup.get("min_opposite_wick_share_pct", 0.0))
            min_wick_body_ratio = float(setup.get("min_wick_body_ratio", 0.0))
            min_wick_opposite_ratio = float(
                setup.get("min_wick_opposite_ratio", 0.0)
            )
            min_range_vs_median = float(setup.get("min_range_vs_median", 0.0))
            min_volume_vs_median = float(setup.get("min_volume_vs_median", 0.0))
            max_body_pct = setup.get("max_body_pct")
            max_body_pct = (
                float(max_body_pct) if max_body_pct is not None else None
            )
            lookback_bars = max(1, int(setup.get("lookback_bars", 12)))
            min_prior_bars = max(0, int(setup.get("min_prior_bars", 0)))
            relative_context_optional = bool(
                setup.get("relative_context_optional", False)
            )
        except (TypeError, ValueError):
            continue

        if range_pct < min_range_pct:
            continue
        if wick_price_pct < min_wick_pct:
            continue
        if wick_share_pct < min_wick_share_pct:
            continue
        if opposite_wick / candle_range * 100.0 < min_opposite_share_pct:
            continue
        if wick_body_ratio < min_wick_body_ratio:
            continue
        if wick_opposite_ratio < min_wick_opposite_ratio:
            continue
        if max_body_pct is not None and body_pct > max_body_pct:
            continue

        prior = frame.iloc[max(0, idx - lookback_bars):idx]
        if len(prior) < min_prior_bars:
            continue

        prior_low = pd.to_numeric(prior["low"], errors="coerce").min()
        prior_high = pd.to_numeric(prior["high"], errors="coerce").max()

        prior_ranges = (
            pd.to_numeric(prior["high"], errors="coerce")
            - pd.to_numeric(prior["low"], errors="coerce")
        ).dropna()
        prior_ranges = prior_ranges[prior_ranges > 0]
        range_vs_median = None
        if len(prior_ranges) >= 3:
            median_range = prior_ranges.median()
            if pd.notna(median_range) and median_range > 0:
                range_vs_median = candle_range / float(median_range)

        volume_x = _volume_context(prior, volume)

        if min_range_vs_median > 0:
            if range_vs_median is None:
                if not relative_context_optional:
                    continue
            elif range_vs_median < min_range_vs_median:
                continue

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

        if min_volume_vs_median > 0:
            volume_ok = volume_x is not None and volume_x >= min_volume_vs_median
            if not volume_ok and not (setup.get("volume_or_reclaim", False) and is_sweep):
                continue

        if setup.get("require_reclaim", False) and not is_sweep:
            continue

        matched_setup = setup
        matched_prior = prior
        prior_level = level
        swept = is_sweep
        break

    if matched_setup is None:
        return None

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
        "two_sided": bool(matched_setup.get("two_sided", False)),
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "wick": wick,
        "wick_pct": wick_price_pct,
        "wick_share_pct": wick_share_pct,
        "wick_body_ratio": wick_body_ratio,
        "wick_opposite_ratio": wick_opposite_ratio,
        "body_pct": body_pct,
        "range_pct": range_pct,
        "range_vs_median": range_vs_median,
        "lookback_bars": lookback_bars,
        "prior_level": prior_level,
        "swept_reclaimed": swept,
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

            candidates = [
                _wick_event(ticker, frame, idx, side, setups)
                for side in ("LOWER", "UPPER")
            ]
            candidates = [event for event in candidates if event is not None]
            if candidates:
                # Prefer a real sweep, then the most dominant wick. Only one
                # side can enter the queue for this ticker/candle.
                event = max(candidates, key=lambda e: (
                    e["swept_reclaimed"], e["wick_share_pct"], e["wick"]
                ))
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
    """Format simple wick lines; overflow is sent immediately in the same run."""
    if result and result.get("alerts_dispatched"):
        return ""
    events = result.get("alert_data", []) if result else []
    events = [e for e in events if e.get("type") in {"LOWER_WICK", "UPPER_WICK"}]
    if not events:
        return mean_reversal.prepare_alert(result)

    uk_dates = {
        datetime.strptime(e["bar_time_et"], "%Y-%m-%d %H:%M ET")
        .replace(tzinfo=ET).astimezone(UK).strftime("%Y-%m-%d")
        for e in events
    }
    single_date = len(uk_dates) == 1
    header = f'WICKS | {next(iter(uk_dates))}\n' if single_date else "WICKS\n"
    lines = []
    keys = []
    seen = set()
    for event in events:
        key = _event_key(event)
        if key in seen:
            continue
        seen.add(key)
        uk_time = (
            datetime.strptime(event["bar_time_et"], "%Y-%m-%d %H:%M ET")
            .replace(tzinfo=ET).astimezone(UK).strftime("%H:%M" if single_date else "%Y-%m-%d %H:%M")
        )
        side = "LOWER" if event["type"] == "LOWER_WICK" else "UPPER"
        label = "TWO-SIDED WICK" if event.get("two_sided") else (
            side + (" SWEEP" if event.get("swept_reclaimed") else " WICK")
        )
        line = f'{event["ticker"]} | {label} | {uk_time}\n'
        candidate = CODE_FENCE + "\n" + header + "".join(lines) + line + CODE_FENCE
        if len(candidate) > 1900:
            break
        lines.append(line)
        keys.append(key)

    if not lines:
        raise ValueError("Wick line exceeds Discord limit; event retained")
    message = CODE_FENCE + "\n" + header + "".join(lines) + CODE_FENCE
    _write_json_atomic(batch_file, {"event_keys": keys})
    return message


def send_alerts(result, sender, state_file=STATE_FILE, batch_file=BATCH_FILE):
    """Send all wicks now; size overflow follows immediately, never next schedule.

    The sender must raise or return False on failure. Legacy senders returning
    None retain the existing caller contract, but cannot prove delivery.
    The delivery file tracks acknowledgement of the current Discord message.
    """
    if not result or result.get("alerts_dispatched"):
        return 0
    sent_count = 0
    remaining = list(result.get("alert_data", []))
    while remaining:
        message = prepare_alert({"alert_data": remaining}, state_file, batch_file)
        if not message:
            break
        keys = set(_read_json(batch_file, {}).get("event_keys", []))
        if not keys:
            break
        if sender(message) is False:
            raise RuntimeError("Discord wick delivery failed; unsent events retained")
        _mark_wick_alert_sent(state_file, batch_file)
        remaining = [e for e in remaining if _event_key(e) not in keys]
        result["alert_data"] = remaining
        sent_count += len(keys)

    # Preserve the independent mean-reversal strategy's existing notifications.
    mean_remaining = list(result.get("mean_reversal_alerts", []))
    while mean_remaining:
        message = mean_reversal.prepare_alert({"mean_reversal_alerts": mean_remaining})
        if not message:
            break
        keys = set(mean_reversal._read_json(mean_reversal.BATCH_FILE, {}).get("event_keys", []))
        if not keys:
            break
        if sender(message) is False:
            raise RuntimeError("Discord mean-reversal delivery failed; unsent events retained")
        mean_reversal.mark_alert_sent()
        mean_remaining = [e for e in mean_remaining if mean_reversal._event_key(e) not in keys]
        result["mean_reversal_alerts"] = mean_remaining
        sent_count += len(keys)
    result["alerts_dispatched"] = not result.get("alert_data") and not mean_remaining
    return sent_count


def mark_alert_sent(
    state_file=STATE_FILE,
    batch_file=BATCH_FILE,
):
    """Acknowledge only the batch confirmed sent to Discord."""
    # Wick messages have priority. Do not let a stale mean batch acknowledge
    # the wrong message after the formatter selects a wick batch.
    batch = _read_json(batch_file, {})
    if isinstance(batch, dict) and batch.get("event_keys"):
        return _mark_wick_alert_sent(state_file, batch_file)
    if mean_reversal.has_prepared_batch():
        return mean_reversal.mark_alert_sent()
    return 0


def _mark_wick_alert_sent(state_file=STATE_FILE, batch_file=BATCH_FILE):
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

