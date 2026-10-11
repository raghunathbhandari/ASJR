#!/usr/bin/env python3
"""Single entry point for a full existing-Chakra pipeline run.

Running scheduler: request one existing complete 5-minute cycle via the
existing scan_now IPC. No duplicate API clients or independent loop.

Stopped scheduler: deliberately fail closed pending verification of the
external VPS launcher (/root/trading/utils/trading_sudarsan_chakra.py).
The launcher is outside this repository; guessing an invocation could
create a second EClient or overwrite live state. This is NOT a standalone
broker runner yet.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent

def main(argv=None):
    parser = argparse.ArgumentParser(description="One full Chakra pipeline cycle")
    parser.add_argument("--mode", choices=("auto", "queue", "standalone"),
                        default="auto")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--saved", action="store_true")
    parser.add_argument("--premarket-test", action="store_true")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--date")
    args = parser.parse_args(argv)
    if args.mode == "standalone":
        print("RUDRA RUN_NOW | STANDALONE NOT CONFIGURED")
        print("Need audited VPS Chakra launcher and shared IBKR/run-lock wiring.")
        print("No API connection or Discord send attempted.")
        return 2
    # Auto currently means safe queued mode until standalone launch is audited.
    command = [sys.executable, str(BASE / "scan_now.py"),
               "--repo", str(ROOT), "--timeout", str(args.timeout)]
    if args.status:
        command.append("--status")
    if args.saved:
        command.append("--saved")
    if args.premarket_test:
        command.append("--premarket-test")
    if args.no_wait:
        command.append("--no-wait")
    if args.date:
        command.extend(["--date", args.date])
    if args.mode == "auto":
        print("RUDRA RUN_NOW | SAFE AUTO: queue via current full Chakra cycle;",
              "stopped-bot execution not enabled.", flush=True)
    return subprocess.call(command)

if __name__ == "__main__":
    raise SystemExit(main())
