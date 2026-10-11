#!/usr/bin/env python3
"""Install a reversible full-Chakra-round lock in the existing VPS launcher.

The real launcher lives outside the Git repository. This script leaves all
trade/data/Discord statements untouched; adds an exclusive flock decorator
around ibkr_trading_sudarsan_chakra(app), covering both pipeline and send.
"""
from __future__ import annotations
import argparse
import os
import py_compile
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

LAUNCHER = Path("/root/trading/utils/trading_sudarsan_chakra.py")
MARKER = "_ASJR_SHARED_ROUND_LOCK_V1"
TARGET = "\ndef ibkr_trading_sudarsan_chakra(app):"
BLOCK = r'''

# _ASJR_SHARED_ROUND_LOCK_V1
# Lock covers canonical pipeline AND the existing Discord send/ACK.
# The manual run_now process already owns the same lock and sets the
# ASJR_MANUAL_RUN_LOCK_HELD flag only for its own guarded call.
import fcntl as _asjr_lock_fcntl
import os as _asjr_lock_os
from functools import wraps as _asjr_lock_wraps
from pathlib import Path as _asjr_lock_path


def _asjr_guard_full_chakra_round(fn):
    @_asjr_lock_wraps(fn)
    def guarded(*args, **kwargs):
        if _asjr_lock_os.environ.get("ASJR_MANUAL_RUN_LOCK_HELD") == "1":
            return fn(*args, **kwargs)
        lock = _asjr_lock_path("/root/trading/ASJR/.chakra_run_now.lock")
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("a+") as handle:
            try:
                _asjr_lock_fcntl.flock(
                    handle.fileno(),
                    _asjr_lock_fcntl.LOCK_EX | _asjr_lock_fcntl.LOCK_NB,
                )
            except BlockingIOError:
                print("CHAKRA | BUSY: another full scheduled/manual round is running")
                return None
            _asjr_lock_os.environ["ASJR_MANUAL_RUN_LOCK_HELD"] = "1"
            try:
                return fn(*args, **kwargs)
            finally:
                _asjr_lock_os.environ.pop("ASJR_MANUAL_RUN_LOCK_HELD", None)
    return guarded


@_asjr_guard_full_chakra_round
'''


def apply_to_source(source):
    if MARKER in source:
        return source, "ALREADY_INSTALLED"
    if source.count(TARGET) != 1:
        raise ValueError("Expected exactly one canonical Chakra function declaration")
    return source.replace(TARGET, "\n" + BLOCK + TARGET[1:], 1), "READY"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="Read-only safety preview")
    p.add_argument("--apply", action="store_true", help="Backup and patch actual launcher")
    args = p.parse_args(argv)
    if args.check == args.apply:
        p.error("choose exactly one of --check or --apply")
    if not LAUNCHER.is_file():
        print("FAILED: Chakra launcher not found", LAUNCHER)
        return 2
    text = LAUNCHER.read_text(encoding="utf-8")
    try:
        updated, status = apply_to_source(text)
    except ValueError as exc:
        print("REFUSED:", exc)
        return 2
    if status == "ALREADY_INSTALLED":
        print("CHAKRA SHARED ROUND LOCK | ALREADY INSTALLED")
        return 0
    # Validate patched Python syntax without importing broker/Discord modules.
    with tempfile.TemporaryDirectory() as directory:
        trial = Path(directory) / "test_launcher.py"
        trial.write_text(updated, encoding="utf-8")
        py_compile.compile(str(trial), doraise=True)
    if args.check:
        print("CHAKRA SHARED ROUND LOCK | CHECK PASSED; no modifications")
        return 0
    backup = LAUNCHER.with_name(
        LAUNCHER.name + ".backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(LAUNCHER, backup)
    temporary = LAUNCHER.with_suffix(".tmp")
    try:
        temporary.write_text(updated, encoding="utf-8")
        os.chmod(temporary, LAUNCHER.stat().st_mode)
        py_compile.compile(str(temporary), doraise=True)
        os.replace(temporary, LAUNCHER)
    except Exception:
        temporary.unlink(missing_ok=True)
        shutil.copy2(backup, LAUNCHER)
        raise
    print("CHAKRA SHARED ROUND LOCK | INSTALLED")
    print("BACKUP:", backup)
    print("LAUNCHER:", LAUNCHER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
