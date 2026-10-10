"""Independent RudraScanner Discord delivery; separate from Wicks/Reversal.

Caller MUST enable both scanner alerts and explicit experimental pattern
approval after replay validation. Failed sends remain unacknowledged.
No orders and no announcements for empty or unavailable signals.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .storage import _atomic


def event_key(event):
    return "|".join(str(event[k]) for k in (
        "ticker", "pattern", "direction", "bar_start_utc"
    ))


def format_alert(events, *, trade_date):
    if not events:
        return ""
    lines = [f"RUDRA RADAR | 5M | {trade_date} | UK TIME",
             "EXPERIMENTAL PATTERNS - VALIDATION REQUIRED"]
    names = []
    for e in events:
        lines.append(
            f'{e["pattern"]} | {e["ticker"]} | {e["direction"]} | '
            f'{e["bar_time_uk"]} | {e["price"]:.2f} '
            f'EMA9 {e["ema9"]:.2f} VWAP {e["vwap"]:.2f}'
        )
        if e["ticker"] not in names:
            names.append(e["ticker"])
    lines += ["", ", ".join(names)]
    return "\n".join(lines)


def deliver_scanner_alerts(events, sender, *, state_file, trade_date,
                           enabled=False, thresholds_approved=False):
    """Return diagnostic; never call sender unless BOTH gates true."""
    if not enabled or not thresholds_approved:
        return {"state": "DISABLED", "sent": 0, "pending": len(events)}
    if sender is None:
        return {"state": "NO_SENDER", "sent": 0, "pending": len(events)}
    path = Path(state_file)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    if state.get("schema") != 1 or state.get("trade_date") != str(trade_date):
        state = {"schema": 1, "trade_date": str(trade_date), "sent": []}
    delivered = set(state.get("sent", []))
    new = []
    seen = set()
    for event in events:
        if event.get("status") != "EXPERIMENTAL_RESEARCH":
            continue
        key = event_key(event)
        if key not in delivered and key not in seen:
            new.append(event)
            seen.add(key)
    if not new:
        return {"state": "NO_NEW_EVENTS", "sent": 0, "pending": 0}
    total = 0
    chunk = []
    for event in new:
        candidate = chunk + [event]
        if len(format_alert(candidate, trade_date=trade_date)) > 1850:
            if not chunk:
                raise ValueError("One scanner event exceeds Discord limit")
            message = format_alert(chunk, trade_date=trade_date)
            if sender("".join(["\x60\x60\x60\n", message, "\n\x60\x60\x60"])) is False:
                raise RuntimeError("Scanner Discord send returned false")
            for sent in chunk:
                delivered.add(event_key(sent))
            total += len(chunk)
            state["sent"] = sorted(delivered)
            _atomic(path, json.dumps(state, indent=2) + "\n")
            chunk = [event]
        else:
            chunk = candidate
    if chunk:
        message = format_alert(chunk, trade_date=trade_date)
        if sender("".join(["\x60\x60\x60\n", message, "\n\x60\x60\x60"])) is False:
            raise RuntimeError("Scanner Discord send returned false")
        for sent in chunk:
            delivered.add(event_key(sent))
        total += len(chunk)
        state["sent"] = sorted(delivered)
        _atomic(path, json.dumps(state, indent=2) + "\n")
    return {"state": "SENT", "sent": total, "pending": len(new) - total}


# The existing VPS Chakra caller obtains ONE prepared Discord message
# using tp.prepare_alert(result), then invokes tp.mark_alert_sent()
# only after an apparent successful send. Reuse that established path,
# but keep scanner queue, sent IDs and batch independent of Wicks and
# Rudra-Reversal. Research and thresholds MUST be double approved
# by the pipeline before queue_scanner_events is called.

def _scanner_read(path, default):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else default
    except (OSError, ValueError, TypeError):
        return default


def _state_for_day(state_file, trade_date):
    state = _scanner_read(state_file, {})
    if state.get("schema") != 1 or state.get("trade_date") != str(trade_date):
        return {"schema": 1, "trade_date": str(trade_date),
                "sent": [], "pending": []}
    state.setdefault("pending", [])
    state.setdefault("sent", [])
    return state


def queue_scanner_events(events, *, state_file, trade_date):
    """Queue eligible new event keys without sending or acknowledging."""
    state = _state_for_day(state_file, trade_date)
    seen = set(state["sent"])
    seen.update(event_key(e) for e in state["pending"])
    added = 0
    for event in events:
        if event.get("status") != "EXPERIMENTAL_RESEARCH":
            continue
        key = event_key(event)
        if key in seen:
            continue
        state["pending"].append(event)
        seen.add(key)
        added += 1
    if added:
        _atomic(state_file, json.dumps(state, indent=2, default=str) + "\n")
    return {"queued_new": added, "pending_total": len(state["pending"]),
            "already_seen": len(events)-added}


def prepare_queued_alert(*, state_file, batch_file):
    """Prepare one Discord-sized scanner message; do NOT ACK here."""
    state = _scanner_read(state_file, {})
    pending = state.get("pending", [])
    day = state.get("trade_date")
    if not day or not pending:
        return ""
    selected = []
    keys = []
    for event in pending:
        candidate = selected + [event]
        body = format_alert(candidate, trade_date=day)
        if len(body) + 8 > 1900:
            if not selected:
                raise ValueError("Scanner alert exceeds Discord message limit")
            break
        selected = candidate
        keys.append(event_key(event))
    if not selected:
        return ""
    _atomic(batch_file, json.dumps(
        {"trade_date": day, "event_keys": keys}, indent=2) + "\n")
    fence = chr(96)*3
    return fence + "\n" + format_alert(selected, trade_date=day) + "\n" + fence


def mark_queued_sent(*, state_file, batch_file):
    """ACK only prepared keys; preserve other pending scanner alerts."""
    state = _scanner_read(state_file, {})
    batch = _scanner_read(batch_file, {})
    if state.get("trade_date") != batch.get("trade_date"):
        return 0
    keys = set(batch.get("event_keys", []))
    if not keys:
        return 0
    before = list(state.get("pending", []))
    state["pending"] = [event for event in before if event_key(event) not in keys]
    present = set(state.get("sent", []))
    state["sent"] = sorted(present | {event_key(e) for e in before if event_key(e) in keys})
    _atomic(state_file, json.dumps(state, indent=2, default=str) + "\n")
    try:
        Path(batch_file).unlink()
    except OSError:
        pass
    return len(before) - len(state["pending"])
