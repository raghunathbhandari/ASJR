#!/usr/bin/env python3
"""Run exactly one canonical Chakra pipeline round, using its existing app helper.

AUTO: when trading_bot tmux session exists, enqueue next scheduled cycle.
When stopped, connect via existing Chakra helper and call the same full
ibkr_trading_sudarsan_chakra(app) method. Never start another bot loop.
"""
from __future__ import annotations
import argparse
import fcntl
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
CHAKRA_FILE = Path("/root/trading/utils/trading_sudarsan_chakra.py")
RUN_LOCK = Path("/root/trading/ASJR/.chakra_run_now.lock")


def bot_running():
    return subprocess.run(["tmux", "has-session", "-t", "trading_bot"],
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, check=False).returncode == 0


def queue_existing(args):
    command = [sys.executable, str(BASE / "scan_now.py"),
               "--repo", str(ROOT), "--timeout", str(args.timeout)]
    for attr, flag in (("status", "--status"), ("saved", "--saved"),
                       ("premarket_test", "--premarket-test"),
                       ("no_wait", "--no-wait")):
        if getattr(args, attr):
            command.append(flag)
    if args.date:
        command.extend(["--date", args.date])
    return subprocess.call(command)


def run_standalone(*, dry_run=False):
    # The full scheduler uses its own app object. Never run standalone while
    # the tmux scheduler exists; this avoids an incompatible second app.
    if bot_running():
        print("RUDRA RUN_NOW | BUSY: trading_bot session exists; use queue mode.")
        return 2
    if not CHAKRA_FILE.is_file():
        print("RUDRA RUN_NOW | Missing Chakra launcher:", CHAKRA_FILE)
        return 2
    RUN_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOCK.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("RUDRA RUN_NOW | BUSY: manual Chakra execution in progress")
            return 2
        # Check again while holding exclusive manual-run lock.
        if bot_running():
            print("RUDRA RUN_NOW | BUSY: trading_bot restarted")
            return 2
        if dry_run:
            print("RUDRA RUN_NOW | DRY RUN PASS: launcher exists, scheduler stopped, lock acquired")
            return 0
        # Import exactly the existing VPS launcher, not a copy of its logic.
        # Its imports are expected to work in the existing trading venv.
        directory = str(CHAKRA_FILE.parent)
        if directory not in sys.path:
            sys.path.insert(0, directory)
        spec = importlib.util.spec_from_file_location("chakra_run_now_launcher", CHAKRA_FILE)
        if spec is None or spec.loader is None:
            print("RUDRA RUN_NOW | ERROR: cannot load Chakra launcher")
            return 2
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app = None
        try:
            app = module.connect_ib_gateway(None)
            if app is None or not app.isConnected():
                print("RUDRA RUN_NOW | ERROR: IBKR app not connected")
                return 2
            print("RUDRA RUN_NOW | FULL CHAKRA PIPELINE START", flush=True)
            result = module.ibkr_trading_sudarsan_chakra(app)
            if result is None:
                print("RUDRA RUN_NOW | PIPELINE FAILED; review Chakra logs")
                return 2
            print("RUDRA RUN_NOW | FULL CHAKRA PIPELINE COMPLETE", flush=True)
            return 0
        finally:
            if app is not None:
                try:
                    app.disconnect()
                except Exception as exc:
                    print("RUDRA RUN_NOW | disconnect warning:", exc)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run/request one full Chakra pipeline cycle")
    parser.add_argument("--mode", choices=("auto", "queue", "standalone"),
                        default="auto")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check stopped-bot standalone launch without connecting")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--saved", action="store_true")
    parser.add_argument("--premarket-test", action="store_true")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--date")
    args = parser.parse_args(argv)
    if args.status or args.saved:
        return queue_existing(args)
    if args.mode == "queue":
        return queue_existing(args)
    if args.mode == "auto" and bot_running():
        print("RUDRA RUN_NOW | Scheduler running: request next FULL Chakra cycle",
              flush=True)
        return queue_existing(args)
    if args.date:
        parser.error("--date is for queued/saved runs only")
    return run_standalone(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
