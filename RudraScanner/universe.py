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


MAX_PER_SOURCE = 10
MAX_STOCK_TICKERS = 3 * MAX_PER_SOURCE
SOURCES = ("FIXED", "AI", "IBKR")


def _fixed_rank(row):
    """Preserve required INTC and explicit open-position monitors first.

    Other fixed entries stay in the manual CSV ordering. This is not a
    claim about price strength or investment quality.
    """
    ticker = str(row.get("ticker", "")).upper()
    notes = str(row.get("notes", "")).upper()
    if ticker == "INTC":
        return 0
    if "OPEN POSITION" in notes:
        return 1
    return 2


def _ai_rank(row):
    """Smallest explicit positive AI priority number wins.

    Research freshness breaks equal priorities; unresolved quality
    checks must stay labelled, never misrepresented as verified.
    """
    try:
        priority = float(row.get("priority", ""))
        if not (0 < priority < float("inf")):
            priority = float("inf")
    except (TypeError, ValueError):
        priority = float("inf")
    freshness = 0 if row.get("freshness") == "FRESH" else 1
    return priority, freshness


def _ibkr_ranking(ibkr_rows):
    """Candidate ranks use available scanner evidence only.

    More distinct successful scan-code appearances sorts first; best
    numerical rank breaks ties. This is NOT a predictive confidence score.
    """
    stats = {}
    for row in ibkr_rows:
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker_valid(ticker) or ticker in EXCLUDED:
            continue
        item = stats.setdefault(ticker, {"codes": set(), "best_rank": float("inf"),
                                         "first_seen": len(stats)})
        code = str(row.get("scan_code", "")).strip()
        if code:
            item["codes"].add(code)
        try:
            rank = float(row.get("rank", ""))
            if 0 < rank < float("inf"):
                item["best_rank"] = min(item["best_rank"], rank)
        except (TypeError, ValueError):
            pass
    return sorted(stats, key=lambda t: (-len(stats[t]["codes"]),
                                        stats[t]["best_rank"],
                                        stats[t]["first_seen"], t))


def merge_shared_universe(fixed_rows, ai_rows, ibkr_rows, *,
                          max_per_source=MAX_PER_SOURCE):
    """Select up to 10 *unique* tickers per source, never more than 30.

    Fixed/AI/IBKR quotas are strict; unused quota is not moved to another
    source. Cross-source overlap does not waste a slot: candidates already
    selected by an earlier bucket are skipped in later buckets.

    Selection source and all discovery provenance are recorded separately.
    The output is the one common stock import list for both strategies;
    Reversal's separate NQ Yahoo instrument is not counted as a stock.
    """
    if not isinstance(max_per_source, int) or not 0 <= max_per_source <= MAX_PER_SOURCE:
        raise ValueError("per-source limit cannot exceed the confirmed 10")

    # Preserve provenance even when a selected ticker was discovered elsewhere.
    metadata = {r["ticker"]: r for r in merge_candidates(ai_rows, ibkr_rows)}
    valid_fixed = []
    for row in fixed_rows:
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker_valid(ticker) or ticker in EXCLUDED:
            continue
        valid_fixed.append((ticker, row))
        item = metadata.setdefault(
            ticker, {"ticker": ticker, "sources": [], "scan_codes": [],
                     "ai_bias": "", "ai_freshness": ""}
        )
        if "FIXED" not in item["sources"]:
            item["sources"].insert(0, "FIXED")
        item.setdefault("fixed_sector", row.get("sector", ""))

    # These are deterministic tie-breakers, NOT a proprietary SMB score.
    fixed_ranked = [t for t, _ in sorted(valid_fixed, key=lambda pair: _fixed_rank(pair[1]))]
    ai_ranked = [str(row.get("ticker", "")).strip().upper()
                 for row in sorted(ai_rows, key=_ai_rank)]
    ibkr_ranked = _ibkr_ranking(ibkr_rows)

    selected = []
    selected_set = set()
    for source, tickers in (
        ("FIXED", fixed_ranked),
        ("AI", ai_ranked),
        ("IBKR", ibkr_ranked),
    ):
        count = 0
        for ticker in tickers:
            if count >= max_per_source:
                break
            if not ticker_valid(ticker) or ticker in EXCLUDED or ticker in selected_set:
                continue
            selected_set.add(ticker)
            count += 1
            row = dict(metadata.get(ticker, {}))
            row.setdefault("ticker", ticker)
            row.setdefault("sources", [source])
            row.setdefault("scan_codes", [])
            row.setdefault("ai_bias", "")
            row.setdefault("ai_freshness", "")
            row["selection_source"] = source
            selected.append(row)

    if len(selected) > MAX_STOCK_TICKERS:
        raise AssertionError("RudraScanner shared ticker cap exceeded")
    # Alphabetical order is the established on-disk convention. Selection
    # source is always explicit, so bucket counts do not depend on this order.
    return sorted(selected, key=lambda row: row["ticker"])


def selection_summary(rows):
    """Auditable selection counts; not a score or performance prediction."""
    buckets = {source: sum(row.get("selection_source") == source for row in rows)
               for source in SOURCES}
    return {
        "max_total": MAX_STOCK_TICKERS,
        "max_per_source": MAX_PER_SOURCE,
        "selected_total": len(rows),
        "selected_by_source": buckets,
        "unused_slots": {
            source: MAX_PER_SOURCE - buckets[source] for source in SOURCES
        },
    }


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
