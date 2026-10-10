"""Opt-in capture of IBKR's actual historical-bar WAP.

Original EWrapper callback runs unchanged. Match WAP using the bar's
timestamp, never positionally: the six-field parser sorts timestamps
and incoming callbacks need not arrive in sorted order.
"""
from __future__ import annotations

import math

import pandas as pd


def install_wap_capture(app):
    """Tap the existing connected EWrapper; no new broker connection."""
    if getattr(app, "_rudra_wap_capture_installed", False):
        return False
    handler = getattr(app, "historicalData", None)
    if not callable(handler):
        raise ValueError("IBKR app must provide historicalData(reqId, bar)")
    app._rudra_wap_sidecar = {}

    def wrapped(req_id, bar):
        result = handler(req_id, bar)
        try:
            value = float(getattr(bar, "wap", float("nan")))
            price = value if math.isfinite(value) and value > 0 else None
        except (TypeError, ValueError, AttributeError):
            price = None
        # Only explicitly registered five-minute request IDs are tracked;
        # do not retain every unrelated Gateway historical callback.
        if req_id in app._rudra_wap_sidecar:
            app._rudra_wap_sidecar[req_id].append(
                (str(getattr(bar, "date", "")), price)
            )
        return result

    app.historicalData = wrapped
    app._rudra_wap_capture_installed = True
    return True


def _stamp(raw):
    """IBKR formatDate=2 is epoch seconds, otherwise require tz suffix."""
    value = str(raw).strip()
    if not value:
        return None
    try:
        return pd.to_datetime(int(value), unit="s", utc=True)
    except ValueError:
        try:
            stamp = pd.Timestamp(value)
        except (ValueError, TypeError):
            return None
        if stamp.tzinfo is None:
            return None
        return stamp.tz_convert("UTC")


def attach_wap(app, req_id, parsed, rows):
    """Attach real bar WAP only on exact timestamp/row-count match.

    Missing or duplicate timestamps are DATA NOT READY for VWAP. The
    sidecar is consumed regardless of success to prevent memory growth.
    """
    sidecar = getattr(app, "_rudra_wap_sidecar", None)
    recorded = sidecar.pop(req_id, None) if isinstance(sidecar, dict) else None
    if recorded is None or len(recorded) != len(rows) or len(parsed) != len(rows):
        return parsed
    lookup = {}
    for start, price in recorded:
        stamp = _stamp(start)
        if stamp is None or stamp in lookup:
            return parsed
        lookup[stamp] = price
    indexes = pd.to_datetime(parsed.index, utc=True, errors="coerce")
    if indexes.isna().any() or any(t not in lookup for t in indexes):
        return parsed
    out = parsed.copy()
    out["WAP"] = [lookup[t] for t in indexes]
    return out
