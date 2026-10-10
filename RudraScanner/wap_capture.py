"""Opt-in WAP sidecar on the EXISTING IBKR EWrapper historicalData callback.

Installed only when the scanner's live shadow gate is explicitly enabled.
The original callback always executes first, unchanged. This does NOT
create another EClient, request data, or monkeypatch module-wide ibapi.
"""
from __future__ import annotations

import math


def install_wap_capture(app):
    """Return true if installed; one install per existing IBKR application."""
    if getattr(app, "_rudra_wap_capture_installed", False):
        return False
    handler = getattr(app, "historicalData", None)
    if not callable(handler):
        raise ValueError("IBKR app must provide historicalData(reqId, bar)")
    app._rudra_wap_sidecar = {}

    def wrapped(req_id, bar):
        # Preserve historicalData business logic and any original errors.
        result = handler(req_id, bar)
        try:
            value = float(getattr(bar, "wap", float("nan")))
            if math.isfinite(value) and value > 0:
                app._rudra_wap_sidecar.setdefault(req_id, []).append(value)
            else:
                app._rudra_wap_sidecar.setdefault(req_id, []).append(None)
        except (TypeError, ValueError, AttributeError):
            app._rudra_wap_sidecar.setdefault(req_id, []).append(None)
        return result

    app.historicalData = wrapped
    app._rudra_wap_capture_installed = True
    return True


def attach_wap(app, req_id, parsed, rows):
    """Attach WAP only if source callback bar counts and parsing match.

    False / missing data cannot silently change exact-vwap readiness.
    Consumes the sidecar regardless of readiness, preventing memory leaks.
    """
    sidecar = getattr(app, "_rudra_wap_sidecar", None)
    recorded = sidecar.pop(req_id, None) if isinstance(sidecar, dict) else None
    if (recorded is None or len(recorded) != len(rows)
            or len(parsed) != len(rows)):
        return parsed
    out = parsed.copy()
    out["WAP"] = recorded
    return out
