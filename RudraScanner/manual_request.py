"""Safe SSH -> same-process Chakra RudraScanner manual request handshake.

NO new IBKR connection. NO scanner broker request here. The existing
5-minute Chakra job consumes an on-demand request and acknowledges
the existing single scanner pass after it saves the common DataLake.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SCHEMA = 1
NAME = "rudra_scanner_manual_request.json"


def utc_now():
    return datetime.now(timezone.utc)


def iso_now(now=None):
    return (now or utc_now()).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def current_trade_date(now=None):
    """Mirror Chakra scheduled-date policy including the overnight session."""
    value = (now or datetime.now(ET)).astimezone(ET)
    weekday = value.weekday()
    if weekday == 5 or (weekday == 6 and value.hour < 20):
        return None
    if weekday == 4 and value.hour >= 20:
        return None
    day = value.date()
    if value.hour >= 20:
        day += timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day.isoformat()


def request_path(root):
    return Path(root) / "ASJR_Analyst" / NAME


def _read(path):
    try:
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def load_request(root):
    return _read(request_path(root))


def _atomic(path, state):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2, default=str) + "\n",
                    encoding="utf-8")
    os.replace(temp, path)


def _locked_update(root, fn):
    """Atomic persistent one-slot queue; a CLI never deletes another request."""
    import fcntl
    path = request_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            return fn(path)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def request_scan(root, day, *, now=None):
    """Ask for NEXT normal Chakra cycle. Idempotent while pending."""
    value = iso_now(now)
    def save(path):
        existing = _read(path)
        if (existing.get("status") == "QUEUED" and
                existing.get("trade_date") == str(day)):
            return existing, False
        state = {
            "schema_version": SCHEMA,
            "request_id": uuid.uuid4().hex,
            "trade_date": str(day),
            "requested_at_utc": value,
            "status": "QUEUED",
            "source": "SSH_EXISTING_CHAKRA_NEXT_CYCLE",
            "broker_connections_created": 0,
            "orders": 0,
            "scanner_discord_sends": 0,
        }
        _atomic(path, state)
        return state, True
    return _locked_update(root, save)


def capture_pending(root, day):
    """Called BEFORE existing Chakra's scanner pass; no extra IBKR calls."""
    state = load_request(root)
    if (state.get("status") == "QUEUED" and
            state.get("trade_date") == str(day) and
            state.get("schema_version") == SCHEMA):
        return state["request_id"]
    return None


def complete_pending(root, day, request_id, *, discovery, five_minute, hourly):
    """ACK only a specific request that preceded this real scanner pass."""
    if not request_id:
        return None

    def finish(path):
        prior = _read(path)
        if (prior.get("status") != "QUEUED" or
                prior.get("request_id") != request_id or
                prior.get("trade_date") != str(day)):
            return None
        mode = discovery.get("mode", "off")
        report = five_minute.get("report")
        day_root = Path(root) / "ASJR_Analyst" / "DataLake" / str(day)
        expected = day_root / "reports" / "scalp_radar.txt"
        # Don't claim success from an old report or an error response.
        good = (mode in ("shadow", "active") and
                five_minute.get("state") not in ("OFF", "ERROR") and
                report and Path(report).resolve() == expected.resolve() and
                expected.is_file())
        status = "COMPLETE" if good else "DATA_NOT_READY"
        updated = dict(prior,
                       status=status,
                       completed_at_utc=iso_now(),
                       discovery_state=discovery.get("state", "NOT_READY"),
                       scan_code_states=discovery.get("ibkr_scan_states", {}),
                       selected_total=discovery.get("selected_total", 0),
                       five_minute_state=five_minute.get("state", "NOT_READY"),
                       one_hour_state=hourly.get("state", "NOT_READY"),
                       report_path=str(expected) if good else "",
                       result_source="EXISTING_CHARKA_CYCLE_NO_NEW_CONNECTION")
        _atomic(path, updated)
        return updated
    return _locked_update(root, finish)
