"""Opt-in Top 5 Discord publisher for the EXISTING Chakra sender.

The canonical bot must call send_if_changed(sender=existing_send_callable)
AFTER each saved 5-minute round. This module never creates a Discord
connection, never sends orders, and never imports the disabled signal alerts.
"""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from .top_in_play import choose, render
from .storage import _atomic


def send_if_changed(repo_root, trade_date, sender, *, now=None):
    """Send a changed shortlist; record successful sends only.

    sender(message) must be the *existing* bot notification function and
    must raise on failure. Synchronous; caller handles exceptions/logging.
    """
    now = now or datetime.now(timezone.utc)
    day = str(trade_date)[:10]
    root = Path(repo_root)
    board_path = root/"ASJR_Analyst"/"DataLake"/day/"processed"/"rudra_scanner_categories.json"
    if not board_path.is_file():
        return {"state": "NO_BOARD"}
    board = json.loads(board_path.read_text(encoding="utf-8"))
    message = render(board, now=now)
    if ("DATA STALE" in message or
            "NO RANKED DISCOVERY CANDIDATES" in message or
            "NO VERIFIED CURRENT 5M CANDIDATES" in message):
        return {"state": "NOT_READY"}
    picks = choose(board)
    # Avoid sending duplicate WATCH names repeatedly as bars and timestamps move.
    signature = json.dumps([(x[1],x[2]) for x in picks], separators=(",",":"))
    digest = hashlib.sha256(signature.encode()).hexdigest()
    state_path = root/"ASJR_Analyst"/"state"/"rudra_top5_discord_state.json"
    try:
        prior = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError,ValueError):
        prior = {}
    if prior.get("trade_date")==day and prior.get("digest")==digest:
        return {"state":"UNCHANGED","ticker_count":len(picks)}
    if not callable(sender):
        return {"state":"NO_SENDER"}
    # Existing sender must raise on unsuccessful delivery, otherwise dedup
    # cannot distinguish failure from success.
    sender(message)
    _atomic(state_path,json.dumps({"trade_date":day,"digest":digest,
        "sent_at_utc":now.isoformat(),"tickers":[x[1] for x in picks]},indent=2)+"\n")
    return {"state":"SENT","ticker_count":len(picks)}
