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
from pathlib import Path

from .storage import save_discovery
from .universe import selection_summary

MODE_ENV = "RUDRA_SCANNER_MODE"
OFF = "off"
SHADOW = "shadow"


def run_bot_shadow(app, trade_date, *, repo_root, mode=None, logger=None,
                   timeout=5.0):
    """Return a small structured status; only SHADOW contacts IBKR.

    The caller of this hook must keep the legacy pipeline running even
    if this isolated discovery step raises. Pass the existing connected
    EClient/EWrapper app: no second IBKR connection may be started.
    """
    if mode is None:
        mode = os.environ.get(MODE_ENV, OFF)
    normalized_mode = str(mode).strip().lower()
    if normalized_mode != SHADOW:
        state = "OFF" if normalized_mode in ("", OFF) else "INVALID_MODE"
        return {"mode": normalized_mode or OFF, "state": state,
                "selected_total": 0, "selected_by_source": {
                    "FIXED": 0, "AI": 0, "IBKR": 0
                }}
    if app is None:
        raise ValueError("Shadow scan needs the connected existing IBKR app")

    result = save_discovery(
        app, trade_date, repo_root=Path(repo_root),
        timeout=timeout,
    )
    selected = selection_summary(result["candidates"])
    codes = {code: entry["state"] for code, entry in result["ibkr"].items()}
    complete = all(state in ("SUCCESS", "EMPTY") for state in codes.values())
    data_ready = result["fixed"]["state"] not in ("MISSING", "ERROR")
    return {
        "mode": SHADOW,
        "state": "SHADOW_SAVED" if complete and data_ready else "PARTIAL",
        "selected_total": selected["selected_total"],
        "selected_by_source": selected["selected_by_source"],
        "ai_state": result["ai"]["state"],
        "fixed_state": result["fixed"]["state"],
        "ibkr_scan_states": codes,
        "alert_delivery": "DISABLED",
        "legacy_universe_changed": False,
    }
