"""Feature-gated first-stage Chakra integration for RudraScanner.

Default OFF. In 'shadow', fetch discovery-only IBKR scanners inside the
already existing Chakra five-minute pipeline, combine the fixed/AI/IBKR
candidates under the 10+10+10 cap, and save into the common day DataLake.

It does NOT change the legacy import universe or the live Wicks/Reversal
detectors, request 5M/1H historical bars, dispatch Discord messages, or
create another scheduler. This is a deliberate integration test gate.
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
    """Return a small structured status; only SHADOW contacts IBKR.

    The caller of this hook must keep the legacy pipeline running even
    if this isolated discovery step raises. Pass the existing connected
    EClient/EWrapper app: no second IBKR connection may be started.
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
