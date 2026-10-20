#!/usr/bin/env python3
"""Independent Rudra Data Bridge: approved Yahoo OHLCV import -> isolated Git branch.

Request/result/CSV destination: 'rudra-data-results', never 'main'.
No Chakra/IBKR connection, Git worktree reset, arbitrary shell, service operations.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/root/trading/ASJR")
BRANCH = "rudra-data-results"
REQUESTS = "Rudra-DDB/DataBridge/requests"
RESULTS = "Rudra-DDB/DataBridge/results"
EXPORTS = "Rudra-DDB/DataBridge/exports"
LOCK = Path("/tmp/asjr_data_bridge.lock")
ID_PATTERN = re.compile(r"data-[0-9]{13}\Z")
TICKER = re.compile(r"[A-Z0-9][A-Z0-9.^=_-]{0,19}\Z")
ORIGIN = re.compile(
    r"(?:git@github\.com:|https://github\.com/)"
    r"raghunathbhandari/ASJR(?:\.git)?/?\Z", re.I
)
MAX_DAYS = {
    "1m": 7, "2m": 60, "5m": 60, "15m": 60, "30m": 60,
    "60m": 730, "90m": 60, "1h": 730, "1d": 3650, "5d": 3650,
    "1wk": 3650, "1mo": 3650, "3mo": 3650,
}
MAX_ROWS = 25000
MAX_BYTES = 3_000_000


def run(*args, cwd=ROOT, timeout=120):
    return subprocess.run(list(args), cwd=cwd, text=True,
                          capture_output=True, check=False, timeout=timeout,
                          stdin=subprocess.DEVNULL)


def git(*args, cwd=ROOT, timeout=120):
    return run("git", *args, cwd=cwd, timeout=timeout)


def authorized_origin():
    r = git("remote", "get-url", "origin")
    return r.returncode == 0 and bool(ORIGIN.fullmatch(r.stdout.strip()))


def validate(job, file_id):
    if not isinstance(job, dict) or not ID_PATTERN.fullmatch(file_id):
        return None
    if job.get("schema_version") != 1 or job.get("id") != file_id:
        return None
    if job.get("operation") == "health":
        return ("health", None) if set(job) == {"id", "operation", "schema_version"} else None
    keys = {"schema_version", "id", "operation", "symbols", "interval", "start", "end"}
    if job.get("operation") != "yahoo_import" or set(job) != keys:
        return None
    symbols = job["symbols"]
    if (type(symbols) is not list or not 1 <= len(symbols) <= 5 or
            any(type(v) is not str or not TICKER.fullmatch(v) for v in symbols) or
            len(set(symbols)) != len(symbols)):
        return None
    interval = job["interval"]
    if type(interval) is not str or interval not in MAX_DAYS:
        return None
    if type(job["start"]) is not str or type(job["end"]) is not str:
        return None
    try:
        start = date.fromisoformat(job["start"])
        end = date.fromisoformat(job["end"])
    except ValueError:
        return None
    if not (date(2000, 1, 1) <= start < end <=
            datetime.now(timezone.utc).date() + timedelta(days=1)):
        return None
    if (end - start).days > MAX_DAYS[interval]:
        return None
    return ("yahoo_import", (symbols, interval, start, end))


def collect(symbols, interval, start, end, folder):
    import pandas as pd
    import yfinance as yf

    outcome = {}
    csvs = []
    for symbol in symbols:
        try:
            bars = yf.download(
                symbol, start=start.isoformat(), end=end.isoformat(),
                interval=interval, prepost=True, progress=False,
                auto_adjust=False, threads=False, multi_level_index=False
            )
            if bars is None or bars.empty:
                outcome[symbol] = {"status": "NO_DATA"}
                continue
            if isinstance(bars.columns, pd.MultiIndex):
                bars.columns = bars.columns.get_level_values(0)
            columns = ("Open", "High", "Low", "Close", "Volume")
            if any(col not in bars for col in columns):
                outcome[symbol] = {"status": "BAD_COLUMNS"}
                continue
            bars = bars[list(columns)].dropna(subset=list(columns[:4]))
            bars = bars.sort_index()
            bars = bars[~bars.index.duplicated(keep="first")]
            if not 1 <= len(bars) <= MAX_ROWS:
                outcome[symbol] = {"status": "INVALID_ROW_COUNT"}
                continue
            # Distinct safe names, no user-controlled directories.
            safe = symbol.replace("^", "IDX_").replace("=", "_EQ_").replace(".", "_DOT_").replace("-", "_DASH_")
            path = folder / (safe + ".csv")
            bars.index.name = "datetime_source"
            bars.to_csv(path)
            if path.stat().st_size > MAX_BYTES:
                path.unlink()
                outcome[symbol] = {"status": "TOO_LARGE"}
                continue
            csvs.append((symbol, path))
            outcome[symbol] = {
                "status": "SUCCESS", "rows": len(bars),
                "first": str(bars.index[0]), "last": str(bars.index[-1]),
                "bytes": path.stat().st_size,
            }
        except Exception as exc:
            outcome[symbol] = {"status": "FAILED", "error_type": type(exc).__name__}
    return outcome, csvs


def publish(job, result, csvs):
    ident = job["id"]
    with tempfile.TemporaryDirectory(prefix="asjr_data_publish_") as td:
        folder = Path(td) / "checkout"
        clone = git("clone", "-q", "--no-checkout", str(ROOT), str(folder), timeout=180)
        if clone.returncode:
            return False
        origin = git("remote", "get-url", "origin")
        if origin.returncode:
            return False
        if git("remote", "set-url", "origin", origin.stdout.strip(), cwd=folder).returncode:
            return False
        git("config", "user.name", "ASJR Data Bridge", cwd=folder)
        git("config", "user.email", "asjr-data-bridge@users.noreply.github.com", cwd=folder)
        for attempt in range(4):
            if git("fetch", "-q", "origin", BRANCH, cwd=folder).returncode:
                return False
            if git("checkout", "-q", "-B", "data-publish", "FETCH_HEAD", cwd=folder).returncode:
                return False
            result_path = folder / RESULTS / (ident + ".json")
            if result_path.exists():
                return True
            for symbol, src in csvs:
                dest_rel = f"{EXPORTS}/{ident}/{src.name}"
                dest = folder / dest_rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
                result["symbols"][symbol]["github_path"] = dest_rel
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
            git("add", "--", str(Path(RESULTS) / (ident + ".json")), str(Path(EXPORTS) / ident), cwd=folder)
            if git("commit", "-qm", f"Data bridge result {ident}", cwd=folder).returncode:
                return False
            if git("push", "-q", "origin", "HEAD:refs/heads/" + BRANCH, cwd=folder, timeout=180).returncode == 0:
                return True
            time.sleep(attempt + 1)
    return False


def tick():
    if not authorized_origin() or git("fetch", "-q", "origin", BRANCH).returncode:
        print("DATA BRIDGE | authorized origin/fetch failed", flush=True)
        return 2
    paths = git("ls-tree", "-r", "--name-only", "FETCH_HEAD", REQUESTS)
    if paths.returncode:
        return 2
    for path in paths.stdout.splitlines():
        if not path.startswith(REQUESTS + "/") or not path.endswith(".json"):
            continue
        ident = Path(path).stem
        if not ID_PATTERN.fullmatch(ident):
            continue
        if git("fetch", "-q", "origin", BRANCH).returncode:
            return 2
        if git("cat-file", "-e", f"FETCH_HEAD:{RESULTS}/{ident}.json").returncode == 0:
            continue
        raw = git("show", f"FETCH_HEAD:{path}")
        if raw.returncode or len(raw.stdout) > 2048:
            continue
        try:
            job = json.loads(raw.stdout)
        except ValueError:
            continue
        parsed = validate(job, ident)
        if parsed is None:
            continue
        operation, params = parsed
        print(f"DATA BRIDGE | {ident} | {operation}", flush=True)
        with tempfile.TemporaryDirectory(prefix="asjr_yahoo_import_") as tmp:
            if operation == "health":
                result = {"status": "SUCCESS", "python": sys.version.split()[0],
                          "symbols": {}}
                csvs = []
            else:
                outcomes, csvs = collect(*params, Path(tmp))
                result = {"status": "SUCCESS" if all(v["status"] == "SUCCESS" for v in outcomes.values())
                          else "PARTIAL_OR_FAILED", "symbols": outcomes,
                          "interval": params[1], "start_inclusive": str(params[2]),
                          "end_exclusive": str(params[3]), "source": "Yahoo Finance"}
            result.update({"id": ident, "operation": operation,
                           "completed_utc": datetime.now(timezone.utc).isoformat()})
            if not publish(job, result, csvs):
                print("DATA BRIDGE | export failed; no live checkout modified", flush=True)
                return 2
            print(f"DATA BRIDGE | {ident} | {result['status']}", flush=True)
        return 0
    print("DATA BRIDGE | IDLE", flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    if not 60 <= args.interval <= 3600:
        parser.error("interval must be 60..3600")
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("DATA BRIDGE | already running", flush=True)
            return 2
        if args.once:
            return tick()
        while True:
            try:
                tick()
            except Exception as exc:
                print("DATA BRIDGE | worker error:", type(exc).__name__, flush=True)
            time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
