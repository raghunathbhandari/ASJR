#!/usr/bin/env python3
"""Request live RudraScanner scan using the EXISTING Chakra IBKR session.

This does NOT start an independent EClient/Gateway or new live bot.
It queues one request, then waits for the next existing Chakra 5-minute
pipeline cycle, which already runs the four-code discovery/5M research.
No orders and no scanner Discord sends; current SHADOW gates still apply.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from RudraScanner.bot_hook import scanner_runtime
from RudraScanner.manual_request import (
    current_trade_date, load_request, request_scan,
)
from RudraScanner.storage import read_saved_report


def show_result(state, root):
    print("RUDRA SCANNER | MANUAL SSH REQUEST |", state.get("status", "UNKNOWN"))
    for key in ("request_id", "trade_date", "requested_at_utc",
                "completed_at_utc", "discovery_state", "scan_code_states",
                "selected_total", "five_minute_state", "one_hour_state"):
        if key in state:
            print(key.upper() + ":", state[key])
    if state.get("status") == "COMPLETE":
        print("")
        print(read_saved_report(root, state["trade_date"]))
        return 0
    if state.get("status") == "DATA_NOT_READY":
        print("Scanner cycle returned without a fresh saved 5M report;")
        print("check live_status.py and the existing Chakra logs.")
        return 2
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Ask the existing Chakra bot for its NEXT 5M scanner cycle"
    )
    parser.add_argument("--date", help="ET session date; must be today's scheduled Chakra session")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--status", action="store_true", help="Read current SSH request, do not queue")
    parser.add_argument("--saved", action="store_true", help="Print saved report only, do not queue")
    parser.add_argument("--no-wait", action="store_true", help="Queue and return without waiting")
    parser.add_argument("--timeout", type=int, default=900,
                        help="Maximum waiting seconds; does NOT control broker API")
    args = parser.parse_args(argv)
    root = Path(args.repo).resolve()
    if args.status:
        state = load_request(root)
        if not state:
            print("RUDRA SCANNER | NO MANUAL REQUEST SAVED")
            return 0
        return show_result(state, root)
    if args.saved:
        day = args.date or current_trade_date()
        if not day:
            print("No current US Chakra trading session; use --date YYYY-MM-DD")
            return 2
        print(read_saved_report(root, day))
        return 0

    day = current_trade_date()
    if not day:
        print("RUDRA SCANNER | MARKET SESSION CLOSED")
        print("No SSH request queued. The existing Chakra bot is not scheduled now.")
        print("For saved data use print_saved.py --date YYYY-MM-DD.")
        return 2
    if args.date and args.date != day:
        print("RUDRA SCANNER | REFUSED: manual request must target current ET session", day)
        print("For historical results use print_saved.py instead.")
        return 2
    runtime = scanner_runtime(root, day)
    if runtime["mode"] not in ("shadow", "active") or not runtime["research"]:
        print("RUDRA SCANNER | DISABLED; no new request queued.")
        print("Configured mode:", runtime["mode"], "| research:", runtime["research"])
        return 2
    if args.timeout < 1 and not args.no_wait:
        parser.error("--timeout must be >=1 seconds")
    state, created = request_scan(root, day)
    print("RUDRA SCANNER | SSH REQUEST", "QUEUED" if created else "ALREADY QUEUED", flush=True)
    print("REQUEST ID:", state["request_id"], "| ET DATE:", day, flush=True)
    print("Uses SAME existing Chakra process and IBKR app, at its NEXT 5-minute cycle.", flush=True)
    print("NO new connection; NO immediate separate scan; NO orders; scanner Discord OFF.", flush=True)
    if args.no_wait:
        print("To inspect: python RudraScanner/scan_now.py --status", flush=True)
        return 0
    start = time.monotonic()
    while time.monotonic() - start < args.timeout:
        outcome = load_request(root)
        if outcome.get("request_id") != state["request_id"]:
            print("Request was replaced; no result can be attributed safely.")
            return 2
        if outcome.get("status") in ("COMPLETE", "DATA_NOT_READY"):
            return show_result(outcome, root)
        time.sleep(2)
    print("TIMEOUT waiting for existing Chakra cycle. Request remains queued.")
    print("Inspect: python RudraScanner/scan_now.py --status")
    print("No second IBKR connection or scanner broker request was started by SSH.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
