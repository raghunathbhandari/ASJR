"""Shared ticker candidates for RudraScanner and Rudra-Reversal.

The fixed watchlist is an existing ASJR day-config input, NOT a third
dynamic discovery feed. AI and IBKR still provide the two discovery CSVs.
This module is read-only and does not modify locked strategy rules or fetches.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .discovery import EXCLUDED, merge_candidates, ticker_valid


FIXED_FIELDS = ("ticker", "enabled")
FIXED_SOURCE = "FIXED"


def read_fixed_watchlist(repo_root, trade_date):
    """Load the day's existing fixed list; return (enabled rows, health status).

    The production ASJR day-bootstrap already copies forward the most recent
    earlier list. Do not independently choose an earlier/future date here.
    Missing, disabled, duplicate and explicitly excluded rows are visible.
    """
    day = date.fromisoformat(str(trade_date)[:10]).isoformat()
    path = (
        Path(repo_root) / "ASJR_Analyst" / "DataLake" / day
        / "config" / "fixed_watchlist.csv"
    )
    status = {
        "state": "OK", "path": str(path), "rows": 0,
        "included": 0, "disabled": 0, "excluded": [],
        "warnings": [],
    }
    if not path.is_file():
        status["state"] = "MISSING"
        status["warnings"].append("Day-specific fixed_watchlist.csv missing; do not pretend fixed tickers were loaded")
        return [], status
    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            fields = set(reader.fieldnames or ())
            if not set(FIXED_FIELDS).issubset(fields):
                raise ValueError("fixed watchlist must have ticker and enabled columns")
            raw = list(reader)
    except (OSError, csv.Error, ValueError) as exc:
        status["state"] = "ERROR"
        status["warnings"].append(str(exc))
        return [], status

    status["rows"] = len(raw)
    candidates = []
    seen = set()
    for line, item in enumerate(raw, start=2):
        ticker = (item.get("ticker") or "").strip().upper()
        if not ticker_valid(ticker):
            status["warnings"].append(f"line {line}: invalid ticker")
            continue
        if ticker in seen:
            status["warnings"].append(f"line {line}: duplicate ticker {ticker}")
            continue
        seen.add(ticker)
        enabled = (item.get("enabled") or "").strip().lower() in ("1", "true", "yes")
        if not enabled:
            status["disabled"] += 1
            continue
        # User's explicit exclusions take precedence; keep audit of conflict.
        if ticker in EXCLUDED:
            status["excluded"].append(ticker)
            status["warnings"].append(f"{ticker}: enabled fixed row conflicts with explicit exclusion")
            continue
        candidates.append({
            "ticker": ticker, "source": FIXED_SOURCE,
            "sector": (item.get("sector") or "").strip(),
            "exchange": (item.get("exchange") or "").strip(),
            "notes": (item.get("notes") or "").strip(),
        })
    status["included"] = len(candidates)
    if status["warnings"]:
        status["state"] = "PARTIAL"
    return candidates, status


def merge_shared_universe(fixed_rows, ai_rows, ibkr_rows):
    """Return one deduplicated stock universe used as input for both strategies.

    Fixed tickers survive even if absent from the two discovery CSVs.
    AI bias is context, never a direction override on either strategy.
    """
    merged = {r["ticker"]: r for r in merge_candidates(ai_rows, ibkr_rows)}
    for row in fixed_rows:
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker_valid(ticker) or ticker in EXCLUDED:
            continue
        item = merged.setdefault(
            ticker, {
                "ticker": ticker, "sources": [], "scan_codes": [],
                "ai_bias": "", "ai_freshness": "",
            }
        )
        if FIXED_SOURCE not in item["sources"]:
            item["sources"].insert(0, FIXED_SOURCE)
        if "fixed_sector" not in item:
            item["fixed_sector"] = row.get("sector", "")
    return [merged[t] for t in sorted(merged)]


def load_shared_universe(repo_root, trade_date, ai_rows, ibkr_rows):
    """Resolve both strategies' common stock inputs without mutating anything."""
    fixed, fixed_status = read_fixed_watchlist(repo_root, trade_date)
    rows = merge_shared_universe(fixed, ai_rows, ibkr_rows)
    return rows, fixed_status


def common_tickers(rows):
    """The exact same US stock ticker list for 5M and 1H import/detectors.

    Reversal's separately configured NQ Yahoo instrument is not a US stock
    candidate and is deliberately handled outside the common stock universe.
    """
    return [item["ticker"] for item in rows]
