"""Bounded same-app first-time RVOL5 imports for new Chakra scanner tickers.

Runs and JOINS inside the canonical locked pipeline. No persistent worker
process; no API requests overlap with the preceding live scanner stage.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

import pandas as pd

from .discovery import EXCLUDED, ticker_valid
from .premarket_backfill import PremarketBackfillQueue, fetch_using_existing_app
from .premarket_rvol import (
    FIELDS, _clean_reference, _complete_profiles, durable_reference_path,
    reference_path,
)

MAX_PER_CYCLE = 3


def config_enabled(repo_root):
    path = Path(repo_root) / "RudraScanner" / "premarket_alert_config.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("auto_backfill") is True
    except (OSError, ValueError, TypeError):
        return False


def _status_path(root):
    return Path(root) / "ASJR_Analyst" / "state" / "rudra_premarket_auto_backfill.json"


def _read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def select_missing(root, day, tickers, limit=MAX_PER_CYCLE):
    path = durable_reference_path(root)
    reference = pd.DataFrame(columns=FIELDS)
    if path.is_file():
        try:
            reference = _clean_reference(pd.read_csv(path), day)
        except (OSError, ValueError, pd.errors.EmptyDataError):
            return [], {"state": "UNREADABLE_DURABLE_REFERENCE"}
    eligible = set()
    if not reference.empty:
        days = reference.groupby(["ticker", "session"])["session_date_et"].nunique()
        eligible = {ticker for (ticker, session), count in days.items()
                    if count >= 5}
    state = _read_json(_status_path(root))
    attempted = set(state.get("attempted", [])) if state.get("day") == str(day) else set()
    chosen = []
    seen = set()
    for value in tickers:
        ticker = str(value).strip().upper()
        if (not ticker_valid(ticker) or ticker in EXCLUDED or ticker in seen
                or ticker in eligible or ticker in attempted):
            continue
        seen.add(ticker)
        chosen.append(ticker)
        if len(chosen) >= limit:
            break
    return chosen, {"state": "OK", "eligible_tickers": len(eligible),
                    "skipped_attempted": len(attempted)}


def backfill_cycle(app, root, day, tickers, *, enabled=None,
                   fetch_one=None, max_new=MAX_PER_CYCLE):
    """At most three imports; caller ensures exclusive canonical pipeline lock."""
    if enabled is None:
        enabled = config_enabled(root)
    if not enabled:
        return {"state": "DISABLED"}
    chosen, selection = select_missing(root, day, tickers, limit=max_new)
    if selection["state"] != "OK":
        return selection
    if not chosen:
        return {**selection, "state": "UP_TO_DATE_OR_ATTEMPTED", "selected": []}

    repo = Path(root)
    store_lock = Lock()

    def fetch(ticker):
        return (fetch_one(ticker) if fetch_one is not None
                else fetch_using_existing_app(app, ticker, duration="10 D"))

    def store(ticker, profile):
        # Serializes all read/merge/atomic-write operations for the three
        # validation workers; can run while another worker waits for broker.
        with store_lock:
            before = durable_reference_path(repo)
            existing = pd.DataFrame(columns=FIELDS)
            if before.is_file():
                existing = pd.read_csv(before)
            incoming = _complete_profiles(profile, before_day=day)
            parts = [x for x in (existing, incoming) if not x.empty]
            if not parts:
                raise ValueError("No complete prior-day reference sessions")
            merged = _clean_reference(pd.concat(parts, ignore_index=True), day)
            if merged.empty:
                raise ValueError("No valid complete reference sessions")
            for dest in (before, reference_path(repo, day)):
                dest.parent.mkdir(parents=True, exist_ok=True)
                temp = dest.with_suffix(".tmp")
                temp.write_text(merged.to_csv(index=False), encoding="utf-8")
                os.replace(temp, dest)

    queue = PremarketBackfillQueue(fetch, store, workers=3,
                                   ibkr_concurrency=1, min_interval_seconds=3.0)
    try:
        futures = {ticker: queue.enqueue(ticker) for ticker in chosen}
        result = {}
        for ticker, future in futures.items():
            try:
                result[ticker] = future.result()
            except Exception as exc:
                result[ticker] = {"ticker": ticker, "status": "ERROR",
                                  "error": str(exc), "saved": False}
    finally:
        queue.close(wait=True)

    status_file = _status_path(repo)
    old = _read_json(status_file)
    attempted = (list(old.get("attempted", []))
                 if old.get("day") == str(day) else [])
    attempted = list(dict.fromkeys(attempted + chosen))
    snapshot = {
        "day": str(day), "attempted": attempted,
        "last_result": result,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_json(status_file, snapshot)
    return {"state": "FINISHED", "selected": chosen, "results": result,
            "previously_eligible": selection["eligible_tickers"]}
