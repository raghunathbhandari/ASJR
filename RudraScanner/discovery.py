"""Two-source RudraScanner discovery, deliberately independent of the live job.

Pure CSV validation/merging does not require an IBKR connection.
Call run_ibkr_scans(app) only with the existing connected EWrapper/EClient app.
No percentage-move threshold is used for membership.
"""

from __future__ import annotations

import csv
import re
import time
from datetime import datetime, timezone
from pathlib import Path

SCANNER_CODES = (
    "TOP_PERC_GAIN", "TOP_PERC_LOSE", "HOT_BY_VOLUME", "MOST_ACTIVE"
)
AI_FIELDS = (
    "ticker", "sector_etf", "bias", "catalyst", "source_url",
    "published_at_utc", "researched_at_utc", "expires_at_utc",
    "quality_status", "priority", "enabled", "reason"
)
IBKR_FIELDS = ("ticker", "scan_code", "rank", "scanned_at_utc")
EXCLUDED = frozenset({"BEAT", "ONDS"})
_TICKER = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_BIAS = frozenset({"LONG", "SHORT", "BOTH", "WATCH"})
SCAN_FILTERS = (
    ("marketCapAbove1e6", "500"),
    ("usdPriceAbove", "5"),
    ("avgVolumeAbove", "1000000"),
)


def utc_now():
    return datetime.now(timezone.utc)


def utc_text(now=None):
    value = now or utc_now()
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value):
    if not value or not str(value).strip():
        return None
    dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("UTC timestamp must have an explicit timezone")
    return dt.astimezone(timezone.utc)


def ticker_valid(ticker):
    return bool(_TICKER.fullmatch(str(ticker).strip().upper()))


def read_ai_csv(filename, now=None):
    """Return (enabled candidate rows, status). Stale research is never fresh.

    An unresearched permanent WATCH may remain a candidate, but is tagged
    UNVERIFIED; false freshness or verified fundamentals are never implied.
    """
    now = now or utc_now()
    status = {"state": "OK", "rows": 0, "enabled": 0, "expired": 0,
              "unverified": 0, "warnings": []}
    filename = Path(filename)
    if not filename.is_file():
        status.update(state="MISSING", warnings=["AI CSV not present"])
        return [], status
    try:
        with filename.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None or set(AI_FIELDS) - set(reader.fieldnames):
                raise ValueError("Missing AI CSV columns: " +
                                 ", ".join(sorted(set(AI_FIELDS) -
                                                  set(reader.fieldnames or ()))))
            raw = list(reader)
    except (OSError, csv.Error, ValueError) as exc:
        status.update(state="ERROR", warnings=[str(exc)])
        return [], status

    status["rows"] = len(raw)
    rows = []
    seen = set()
    for number, source in enumerate(raw, start=2):
        ticker = (source.get("ticker") or "").strip().upper()
        if not ticker_valid(ticker) or ticker in seen:
            status["warnings"].append(f"line {number}: invalid/duplicate ticker")
            continue
        seen.add(ticker)
        if ticker in EXCLUDED:
            status["warnings"].append(f"{ticker}: excluded")
            continue
        enabled = (source.get("enabled") or "").strip().lower()
        if enabled not in ("true", "1", "yes", "y"):
            continue
        bias = (source.get("bias") or "").strip().upper()
        if bias not in _BIAS:
            status["warnings"].append(f"{ticker}: invalid bias")
            continue
        try:
            researched = parse_utc(source.get("researched_at_utc"))
            expires = parse_utc(source.get("expires_at_utc"))
            published = parse_utc(source.get("published_at_utc"))
        except ValueError as exc:
            status["warnings"].append(f"{ticker}: {exc}")
            continue

        if expires is not None and expires <= now:
            status["expired"] += 1
            continue
        fresh = researched is not None and expires is not None and researched <= now < expires
        if not fresh:
            status["unverified"] += 1
        # A source may verify the publication date but not expose an exact
        # UTC publication time. Preserve the missing timestamp honestly.
        if source.get("catalyst") and not source.get("source_url"):
            status["warnings"].append(f"{ticker}: catalyst has no source URL")
        elif source.get("catalyst") and not published:
            status["warnings"].append(
                f"{ticker}: source date verified; exact published_at_utc unavailable"
            )
        row = {key: (source.get(key) or "").strip() for key in AI_FIELDS}
        row["ticker"], row["bias"] = ticker, bias
        row["freshness"] = "FRESH" if fresh else "UNVERIFIED"
        rows.append(row)
    status["enabled"] = len(rows)
    if status["warnings"] or status["expired"] or status["unverified"]:
        status["state"] = "PARTIAL"
    return rows, status


def _next_req_id(app):
    lock = getattr(app, "id_lock", None)
    if lock is not None:
        with lock:
            value = app.nextReqId
            app.nextReqId += 1
            return value
    value = app.nextReqId
    app.nextReqId += 1
    return value


def run_ibkr_scans(app, *, codes=SCANNER_CODES, timeout=5.0,
                   scanner_cls=None, tag_cls=None, now=None):
    """Return (provenance rows, per-code status), with explicit incomplete scans.

    Compatible with the existing app.scanner_results/scanner_done callback
    contract. Rank is only the position of returned symbols, not a universal
    score. Never silently convert a timeout to EMPTY or SUCCESS.
    """
    if scanner_cls is None or tag_cls is None:
        from ibapi.scanner import ScannerSubscription
        from ibapi.tag_value import TagValue
        scanner_cls = scanner_cls or ScannerSubscription
        tag_cls = tag_cls or TagValue

    now = now or utc_now()
    rows, statuses = [], {}
    for code in codes:
        if code not in SCANNER_CODES:
            statuses[code] = {"state": "ERROR", "reason": "unsupported scan code", "rows": 0}
            continue
        req = None
        started = False
        completed = False
        error = None
        symbols = []
        try:
            req = _next_req_id(app)
            app.scanner_results[req] = []
            app.scanner_done[req] = False
            sub = scanner_cls()
            sub.instrument = "STK"
            sub.locationCode = "STK.US.MAJOR"
            sub.scanCode = code
            sub.numberOfRows = 50
            sub.stockTypeFilter = "CORP"
            filters = [tag_cls(name, value) for name, value in SCAN_FILTERS]
            app.reqScannerSubscription(req, sub, [], filters)
            started = True
            start = time.monotonic()
            while time.monotonic() - start < timeout:
                if app.scanner_done.get(req, False):
                    completed = True
                    break
                time.sleep(0.1)
            # On a race at timeout, still recognise a completed callback.
            completed = completed or bool(app.scanner_done.get(req, False))
            symbols = list(app.scanner_results.get(req, []))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        finally:
            if started:
                try:
                    app.cancelScannerSubscription(req)
                except Exception as exc:
                    error = error or f"Cancel failed: {type(exc).__name__}: {exc}"
            if req is not None:
                app.scanner_results.pop(req, None)
                app.scanner_done.pop(req, None)

        unique = set()
        for symbol in symbols:
            ticker = str(symbol).strip().upper()
            if not ticker_valid(ticker) or ticker in EXCLUDED or ticker in unique:
                continue
            unique.add(ticker)
            rows.append({"ticker": ticker, "scan_code": code,
                         "rank": len(unique), "scanned_at_utc": utc_text(now)})
        state = "ERROR" if error else ("TIMEOUT" if not completed else
                 ("SUCCESS" if unique else "EMPTY"))
        statuses[code] = {"state": state, "rows": len(unique)}
        if error:
            statuses[code]["reason"] = error
    return rows, statuses


def merge_candidates(ai_rows, ibkr_rows):
    """Union of the two named sources with provenance, without fixed 4% gate."""
    merged = {}
    for row in ai_rows:
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker_valid(ticker) or ticker in EXCLUDED:
            continue
        item = merged.setdefault(ticker, {"ticker": ticker, "sources": [],
                                          "scan_codes": [], "ai_bias": "",
                                          "ai_freshness": ""})
        if "AI" not in item["sources"]:
            item["sources"].append("AI")
        item["ai_bias"] = row.get("bias", "WATCH")
        item["ai_freshness"] = row.get("freshness", "UNVERIFIED")
    for row in ibkr_rows:
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker_valid(ticker) or ticker in EXCLUDED:
            continue
        item = merged.setdefault(ticker, {"ticker": ticker, "sources": [],
                                          "scan_codes": [], "ai_bias": "",
                                          "ai_freshness": ""})
        if "IBKR" not in item["sources"]:
            item["sources"].append("IBKR")
        code = row.get("scan_code", "")
        if (code in SCANNER_CODES or code == "LEGACY_GAPUP_REPLAY") and code not in item["scan_codes"]:
            item["scan_codes"].append(code)
    return [merged[t] for t in sorted(merged)]
