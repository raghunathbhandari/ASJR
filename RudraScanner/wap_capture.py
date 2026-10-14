"""Capture real IBKR historical-bar WAP on the existing Chakra connection.

Callback observation happens BEFORE the legacy handler (which may normalize the
bar). Join captured prices to parsed OHLCV by actual UTC candle timestamp.
Never synthesize WAP from OHLC or attach it by row position.
"""
from __future__ import annotations

import math

import pandas as pd


def install_wap_capture(app):
    """Install one callback tap; no extra client or broker requests."""
    if getattr(app, "_rudra_wap_capture_installed", False):
        return False
    handler = getattr(app, "historicalData", None)
    if not callable(handler):
        raise ValueError("IBKR app must provide historicalData(reqId, bar)")
    app._rudra_wap_sidecar = {}

    def wrapped(req_id, bar):
        # Capture first: downstream callbacks may mutate/reuse bar objects.
        sidecar = getattr(app, "_rudra_wap_sidecar", None)
        if isinstance(sidecar, dict) and req_id in sidecar:
            try:
                price = float(getattr(bar, "wap", float("nan")))
                if not math.isfinite(price) or price <= 0:
                    price = None
            except (TypeError, ValueError, AttributeError):
                price = None
            sidecar[req_id].append((str(getattr(bar, "date", "")), price))
        return handler(req_id, bar)

    app.historicalData = wrapped
    app._rudra_wap_capture_installed = True
    return True


def _stamp(raw):
    """IBKR formatDate=2 is epoch seconds; otherwise require an explicit zone."""
    value = str(raw).strip()
    if not value:
        return None
    try:
        return pd.to_datetime(int(value), unit="s", utc=True)
    except (ValueError, OverflowError):
        try:
            stamp = pd.Timestamp(value)
        except (ValueError, TypeError, OverflowError):
            return None
        if stamp.tzinfo is None:
            return None
        return stamp.tz_convert("UTC")


def attach_wap(app, req_id, parsed, rows):
    """Attach each verified broker WAP by candle start time.

    A single unparseable/filtered broker row must not discard every valid
    candle's WAP. Any unmatched/invalid candle remains NaN, so the downstream
    VWAP prefix validation still fails closed on genuinely missing data.
    """
    sidecar = getattr(app, "_rudra_wap_sidecar", None)
    recorded = sidecar.pop(req_id, None) if isinstance(sidecar, dict) else None
    if parsed is None or parsed.empty:
        return parsed
    out = parsed.copy()
    out["WAP"] = float("nan")
    if recorded is None:
        print(f"RUDRA WAP | reqId={req_id} | NOT_REGISTERED | parsed={len(parsed)}")
        return out

    lookup = {}
    duplicates = set()
    valid_prices = 0
    for start, price in recorded:
        stamp = _stamp(start)
        if stamp is None:
            continue
        if stamp in lookup:
            duplicates.add(stamp)
        else:
            lookup[stamp] = price
        if price is not None:
            valid_prices += 1
    for stamp in duplicates:
        lookup[stamp] = None

    indices = pd.to_datetime(out.index, utc=True, errors="coerce")
    values = [lookup.get(t) if not pd.isna(t) else None for t in indices]
    out["WAP"] = pd.to_numeric(pd.Series(values, index=out.index), errors="coerce")
    matched = int(out["WAP"].notna().sum())
    state = "OK" if matched == len(out) else "PARTIAL_OR_MISSING"
    print(
        f"RUDRA WAP | reqId={req_id} | {state} | "
        f"callbacks={len(recorded)} | parsed={len(out)} | "
        f"broker_wap_positive={valid_prices} | matched={matched} | "
        f"duplicate_times={len(duplicates)}"
    )
    return out
