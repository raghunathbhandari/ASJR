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
from RudraScanner.top_in_play import scan_rankings, raw_ibkr_by_code
import json
from RudraScanner.premarket_diagnostic import print_saved as print_premarket_diagnostic


def show_result(state, root, *, premarket_test=False):
    print("RUDRA SCANNER | MANUAL SSH REQUEST |", state.get("status", "UNKNOWN"))
    for key in ("request_id", "trade_date", "requested_at_utc",
                "completed_at_utc", "discovery_state", "scan_code_states",
                "selected_total", "five_minute_state", "one_hour_state"):
        if key in state:
            print(key.upper() + ":", state[key])
    if state.get("status") == "COMPLETE":
        print("")
        print(read_saved_report(root, state["trade_date"]))
        if premarket_test:
            return print_premarket_diagnostic(root, state["trade_date"])
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
    parser.add_argument("--ibkr-raw", action="store_true", help="Read saved IBKR four-code scan rankings without another API call")
    parser.add_argument("--ibkr-direct", action="store_true", help="One-shot direct IBKR four-category scanner; no Chakra scan")
    parser.add_argument("--top", action="store_true", help="Short saved SMB-style Top In Play shortlist; no new scan")
    parser.add_argument("--status", action="store_true", help="Read current SSH request, do not queue")
    parser.add_argument("--rvol-status", action="store_true", help="Short current RVOL5 data/readiness report, no broker request")
    parser.add_argument("--self-test", action="store_true", help="Run fixed offline WAP/RVOL5 regression tests; no IBKR calls")
    parser.add_argument("--premarket-test", action="store_true",
                        help="Report RVOL5 diagnostic after ONE existing full Chakra pipeline cycle; no Discord")
    parser.add_argument("--saved", action="store_true", help="Print saved report only, do not queue")
    parser.add_argument("--no-wait", action="store_true", help="Queue and return without waiting")
    parser.add_argument("--timeout", type=int, default=900,
                        help="Maximum waiting seconds; does NOT control broker API")
    args = parser.parse_args(argv)
    root = Path(args.repo).resolve()
    if args.self_test:
        # Fixed offline suite only, no arbitrary filename/module from Discord.
        import unittest
        suite = unittest.TestSuite()
        folder = root / "RudraScanner" / "tests"
        loader = unittest.TestLoader()
        for filename in ("test_wap_capture.py", "test_premarket_live.py"):
            suite.addTests(loader.discover(str(folder), pattern=filename))
        print("RUDRA-PREMARKET | OFFLINE WAP + RVOL5 SELF TEST", flush=True)
        outcome = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        print("RUDRA-PREMARKET | SELF TEST |",
              "PASS" if outcome.wasSuccessful() else "FAIL", flush=True)
        return 0 if outcome.wasSuccessful() else 2
    if args.rvol_status:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from RudraScanner.premarket_diagnostic import print_short_status
        day = args.date or datetime.now(ZoneInfo("America/New_York")).date().isoformat()
        return print_short_status(root, day)
    if args.ibkr_raw:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        day = args.date or datetime.now(ZoneInfo("America/New_York")).date().isoformat()
        print(raw_ibkr_by_code(root,day,limit=5),end="")
        return 0
    if args.ibkr_direct:
        from RudraScanner.ibkr_direct import run_direct
        print(run_direct(limit=5,timeout=12),end="")
        return 0
    if args.top:
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        day = args.date or datetime.now(ZoneInfo('America/New_York')).date().isoformat()
        snapshot = root / 'ASJR_Analyst' / 'DataLake' / day / 'processed' / 'rudra_smb_top5.txt'
        if not snapshot.is_file():
            print('RUDRA SCANNER | SMB TOP 5 | NO SAVED RANKING')
            return 2
        # Do not return an obsolete cached ranking as if it were current.
        age = datetime.now(timezone.utc).timestamp() - snapshot.stat().st_mtime
        if age < -60 or age > 1200:
            print('RUDRA SCANNER | SMB TOP 5 | SAVED RANKING STALE')
            print('Latest precomputed ranking unavailable; check Chakra scanner cycles.')
            return 2
        print(snapshot.read_text(encoding='utf-8'), end='')
        return 0
    if args.status:
        state = load_request(root)
        if not state:
            print("RUDRA SCANNER | NO MANUAL REQUEST SAVED")
            return 0
        return show_result(state, root, premarket_test=args.premarket_test)
    if args.saved:
        day = args.date or current_trade_date()
        if not day:
            print("No current US Chakra trading session; use --date YYYY-MM-DD")
            return 2
        print(read_saved_report(root, day))
        if args.premarket_test:
            return print_premarket_diagnostic(root, day)
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
    print("ONE normal FULL Chakra pipeline run, at its NEXT existing 5-minute cycle.", flush=True)
    if args.premarket_test:
        print("Rudra-Premarket RVOL5 report requested; diagnostic only, no Discord.", flush=True)
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
            return show_result(outcome, root, premarket_test=args.premarket_test)
        time.sleep(2)
    print("TIMEOUT waiting for existing Chakra cycle. Request remains queued.")
    print("Inspect: python RudraScanner/scan_now.py --status")
    print("No second IBKR connection or scanner broker request was started by SSH.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
