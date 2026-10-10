"""Feature-gated four-code discovery inside the existing Chakra loop.

From Monday 2026-10-12, the checked-in runtime config schedules SHADOW:
the selected <=30 names are passed to the independent 5M/1H sidecar.
The hook itself collects four new IBKR scanner lists using the same app.
Actual Wicks/Reversal and their original imported ticker list are
always preserved; no autonomous job or order executor is created.
Scanner Discord remains double-gated and OFF until approved.
"""

from __future__ import annotations

import os
import json
from pathlib import Path

from .storage import save_discovery
from .universe import selection_summary

MODE_ENV = "RUDRA_SCANNER_MODE"
OFF = "off"
SHADOW = "shadow"
REPLAY = "replay"
ACTIVE = "active"


def scanner_runtime(repo_root, trade_date):
    """Hot-read scheduled scanner config every Chakra 5M cycle.

    Explicit environment RUDRA_SCANNER_MODE always takes precedence.
    Older dates remain OFF; a Git pull does not itself prove a running
    VPS process has reloaded code or reached the scheduled market.
    """
    path = (Path(repo_root) / "ASJR_Analyst" / "config" /
            "rudra_scanner_runtime.json")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("invalid scanner runtime config")
    except (OSError, ValueError):
        state = {}
    start = str(state.get("enabled_from_et", "9999-12-31"))[:10]
    if str(trade_date)[:10] < start:
        configured = OFF
    else:
        configured = str(state.get("mode", OFF)).lower()
    return {"mode": os.environ.get(MODE_ENV, configured),
            "research": bool(state.get("research", False)),
            "alerts_enabled": bool(state.get("alerts_enabled", False)),
            "thresholds_approved": bool(state.get(
                "thresholds_approved", False)),
            "source": str(path) if path.exists() else "DEFAULT_OFF"}


def run_bot_shadow(app, trade_date, *, repo_root, mode=None, logger=None,
                   timeout=5.0, allow_replay=False,
                   save_replay=False, replay_source_date=None):
    """Discover selected candidates in SHADOW or explicitly ACTIVE mode.

    This is only the discovery stage, not an order or alert sender.
    The caller must keep the existing Chakra pipeline running even if
    an isolated scanner stage fails. Use its current connected app.
    """
    if mode is None:
        mode = scanner_runtime(repo_root, trade_date)["mode"]
    normalized_mode = str(mode).strip().lower()
    if normalized_mode == REPLAY:
        if not allow_replay:
            return {"mode": REPLAY, "state": "REPLAY_NOT_ALLOWED_IN_LIVE_BOT",
                    "selected_total": 0, "alert_delivery": "DISABLED"}
        from .replay import build_replay, persist_replay
        replay_result = build_replay(
            repo_root, trade_date, source_date=replay_source_date,
        )
        if save_replay:
            replay_result["report_path"] = persist_replay(repo_root, replay_result)
        return replay_result
    if normalized_mode not in (SHADOW, ACTIVE):
        state = "OFF" if normalized_mode in ("", OFF) else "INVALID_MODE"
        return {"mode": normalized_mode or OFF, "state": state,
                "selected_total": 0, "selected_by_source": {
                    "FIXED": 0, "AI": 0, "IBKR": 0
                }}
    if app is None:
        raise ValueError("Shadow scan needs the connected existing IBKR app")
    # Shadow gate also enables real WAP capture for existing 5M requests
    # later in the SAME legacy Chakra cycle; no independent data call.
    from .wap_capture import install_wap_capture
    install_wap_capture(app)

    result = save_discovery(
        app, trade_date, repo_root=Path(repo_root),
        timeout=timeout,
    )
    selected = selection_summary(result["candidates"])
    codes = {code: entry["state"] for code, entry in result["ibkr"].items()}
    complete = all(state in ("SUCCESS", "EMPTY") for state in codes.values())
    data_ready = result["fixed"]["state"] not in ("MISSING", "ERROR")
    active_ready = (complete and data_ready and
                    result["ai"]["state"] not in ("MISSING", "ERROR"))
    return {
        "mode": normalized_mode,
        "state": (("ACTIVE_SELECTED" if normalized_mode == ACTIVE
                   else "SHADOW_SAVED") if active_ready else "PARTIAL"),
        "selected_total": selected["selected_total"],
        "selected_by_source": selected["selected_by_source"],
        "ai_state": result["ai"]["state"],
        "fixed_state": result["fixed"]["state"],
        "ibkr_scan_states": codes,
        "alert_delivery": "DISABLED",
        # The existing Chakra pipeline decides whether the live
        # universe is safe to replace. An incomplete scanner response
        # must NOT silently activate a partial stock list.
        "candidates": result["candidates"] if active_ready else [],
        "eligible_for_full_scan": bool(active_ready),
        "legacy_universe_changed": False,
    }
