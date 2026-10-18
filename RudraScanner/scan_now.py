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
    parser.add_argument("--ibkr-7", action="store_true", help="Read-only, on-demand seven-code IBKR discovery; cache ticker universe")
    from RudraScanner.ibkr_seven_scanner import CODES as IBKR_ALLOWED_CODES
    parser.add_argument("--ibkr-codes", action="store_true", help="List supported named IBKR scanner codes; no broker call")
    parser.add_argument("--ibkr-code", choices=IBKR_ALLOWED_CODES,
                        help="On-demand ONE IBKR scanner category; full list, no snapshot overwrite")
    parser.add_argument("--mover-study", action="store_true",
                        help="Read-only 2-year Yahoo historical test of conditions before +10% moves")
    parser.add_argument("--research-46-batch", type=int, choices=range(1, 6),
                        help="One of five fixed, Yahoo-only research collection batches")
    parser.add_argument("--research-46-finalize", action="store_true",
                        help="Finalize research results after all five batches; no broker call")
    parser.add_argument("--bridge-start", action="store_true",
                        help="One-time install/start of fixed ASJR research bridge service; no Chakra restart")
    parser.add_argument("--bridge-refresh", action="store_true",
                        help="Reload only the research bridge service to deploy approved research export; no Chakra restart")
    parser.add_argument("--gann-nq-import", action="store_true",
                        help="One-time NQ Oct16 Yahoo 5m research import, no Chakra")
    parser.add_argument("--bridge-check", action="store_true",
                        help="Run one bridge polling iteration and report health, without installing service")
    parser.add_argument("--ibkr-ema50", action="store_true", help="Direct read-only HIGH_LAST_VS_EMA50 list, up to 50 symbols")
    momentum_modes = parser.add_mutually_exclusive_group()
    momentum_modes.add_argument("--momentum", action="store_true", help="1M and 3M movers together")
    momentum_modes.add_argument("--momentum-1m", action="store_true", help="1-month movers and copy-ready watchlist")
    momentum_modes.add_argument("--momentum-3m", action="store_true", help="3-month movers and copy-ready watchlist")
    parser.add_argument("--top", action="store_true", help="Short saved SMB-style Top In Play shortlist; no new scan")
    parser.add_argument("--status", action="store_true", help="Read current SSH request, do not queue")
    parser.add_argument("--rvol-status", action="store_true", help="Short current RVOL5 data/readiness report, no broker request")
    parser.add_argument("--self-test", action="store_true", help="Run fixed offline WAP/RVOL5 regression tests; no IBKR calls")
    parser.add_argument("--final-check", action="store_true", help="One-step offline regression + current RVOL5 data health; no broker calls")
    parser.add_argument("--premarket-test", action="store_true",
                        help="Report RVOL5 diagnostic after ONE existing full Chakra pipeline cycle; no Discord")
    parser.add_argument("--saved", action="store_true", help="Print saved report only, do not queue")
    parser.add_argument("--no-wait", action="store_true", help="Queue and return without waiting")
    parser.add_argument("--timeout", type=int, default=900,
                        help="Maximum waiting seconds; does NOT control broker API")
    args = parser.parse_args(argv)
    root = Path(args.repo).resolve()
    if args.self_test or args.final_check:
        # This reads only two fixed repository test suites. Never run a
        # user-provided script or make a new IBKR connection.
        import unittest
        suite = unittest.TestSuite()
        folder = Path(__file__).resolve().parent / "tests"
        # A TestLoader remembers its first discover() top-level directory.
        # Use a fresh loader for every discovery and pin the common repo root,
        # otherwise the second test folder triggers "Path must be within
        # the project" on Python 3.10.
        for filename in ("test_wap_capture.py", "test_premarket_live.py",
                         "test_ibkr_seven_scanner.py",
                         "test_lead_mover_backtest.py"):
            suite.addTests(unittest.TestLoader().discover(
                str(folder), pattern=filename, top_level_dir=str(root)))
        suite.addTests(unittest.TestLoader().discover(
            str(root / "ASJR_Analyst" / "Tests"),
            pattern="test_discord_server_commands.py",
            top_level_dir=str(root)))
        print("RUDRA-PREMARKET | OFFLINE WAP + RVOL5 TEST", flush=True)
        outcome = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        passed = outcome.wasSuccessful()
        print("OFFLINE TEST |", "PASS" if passed else "FAIL", flush=True)
        if args.self_test or not passed:
            return 0 if passed else 2

        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        import pandas as pd
        from RudraScanner.premarket_live import enabled as discord_enabled
        from RudraScanner.premarket_live_backfill import config_enabled
        from RudraScanner.premarket_diagnostic import (
            print_short_status, report_path,
        )
        day = args.date or datetime.now(ZoneInfo("America/New_York")).date().isoformat()
        print("RUDRA-PREMARKET | FINAL CHECK |", day, flush=True)
        report_status = print_short_status(root, day)
        data_path = root / "ASJR_Analyst" / "DataLake" / day / "raw" / "intraday_5m.csv"
        broker_wap = 0
        if data_path.is_file():
            raw = pd.read_csv(data_path, low_memory=False)
            if {"Date", "WAP", "Volume"}.issubset(raw.columns):
                rows = raw.loc[raw["Date"].astype(str).str.startswith(day)]
                wap = pd.to_numeric(rows["WAP"], errors="coerce")
                volume = pd.to_numeric(rows["Volume"], errors="coerce")
                broker_wap = int((wap.gt(0) & volume.gt(0)).sum())
        print("IBKR RAW | positive-volume real WAP bars today =", broker_wap)
        path = report_path(root, day)
        report = json.loads(path.read_text()) if path.is_file() else {}
        q = report.get("signal_quality") or {}
        report_age = (datetime.now(timezone.utc).timestamp() -
                      path.stat().st_mtime) if path.is_file() else float("inf")
        ready = (discord_enabled() and config_enabled(root)
                 and report_status == 0 and -60 <= report_age <= 1200
                 and broker_wap > 0
                 and int(q.get("latest_vwap_ready") or 0) > 0)
        print("RESULT |", "DATA PATH READY" if ready else "DATA PATH NOT READY")
        print("DISCORD | Existing Chakra hook configured; "
              "actual delivery requires a qualifying live signal")
        return 0 if ready else 2
    if args.rvol_status:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from RudraScanner.premarket_diagnostic import print_short_status
        day = args.date or datetime.now(ZoneInfo("America/New_York")).date().isoformat()
        return print_short_status(root, day)
    if args.momentum or args.momentum_1m or args.momentum_3m:
        from RudraScanner.momentum_movers import main as momentum_main
        period = "1m" if args.momentum_1m else ("3m" if args.momentum_3m else "both")
        return momentum_main(["--compact", "--period", period])
    if args.gann_nq_import:
        from RudraScanner.gann_nq_import import main as gann_import_main
        return gann_import_main()
    if args.bridge_refresh:
        from RudraScanner.ResearchBridge.refresh_bridge import main as bridge_refresh
        return bridge_refresh()
    if args.bridge_start:
        from RudraScanner.ResearchBridge.install_bridge import main as bridge_install
        return bridge_install()
    if args.bridge_check:
        from RudraScanner.research_bridge_worker import main as bridge_worker
        # Called with a pinned argument set, never Discord-supplied shell.
        import unittest.mock
        with unittest.mock.patch.object(sys, "argv", ["bridge-worker", "--once"]):
            return bridge_worker()
    if args.research_46_batch is not None or args.research_46_finalize:
        from RudraScanner.research_ema50_46 import main as research_main
        if args.research_46_batch is not None:
            return research_main(["--batch", str(args.research_46_batch)])
        return research_main(["--finalize"])
    if args.mover_study:
        from RudraScanner.lead_mover_backtest import main as mover_main
        return mover_main()
    if args.ibkr_codes:
        print("IBKR SCANNER | APPROVED CODES | 7")
        for code in IBKR_ALLOWED_CODES:
            print(code)
        print("Usage: !runpy RudraScanner/scan_now\\.py --ibkr-code HIGH_LAST_VS_EMA50")
        return 0
    if args.ibkr_code:
        from RudraScanner.ibkr_seven_scanner import run_ibkr_seven
        report = run_ibkr_seven(codes=(args.ibkr_code,), preview=50)
        print(report, end="")
        return 0 if "RESULT | SUCCESS" in report else 2
    if args.ibkr_7:
        from RudraScanner.ibkr_seven_scanner import run_ibkr_seven
        report = run_ibkr_seven()
        print(report, end="")
        return 0 if "SNAPSHOT | SAVED" in report else 2
    if args.ibkr_ema50:
        from RudraScanner.ibkr_seven_scanner import run_ibkr_seven
        report = run_ibkr_seven(
            codes=("HIGH_LAST_VS_EMA50",), preview=50,
        )
        print(report, end="")
        return 0 if "RESULT | SUCCESS" in report else 2
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
