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
