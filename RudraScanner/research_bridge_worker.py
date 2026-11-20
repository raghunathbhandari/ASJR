#!/usr/bin/env python3
"""Restricted, read-only-to-live-tree GitHub research job worker.

Only polls GitHub main for approved job JSON; no arbitrary shell or
Discord/Chakra/IBKR calls. Results are committed using a separate temporary
git clone to avoid modifying the live ASJR worktree.
"""
from __future__ import annotations
import argparse
import fcntl
import shutil
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

REPO = Path("/root/trading/ASJR")
# Script is launched by absolute path from systemd, so package root is not
# automatically importable when publishing isolated research evidence.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
REQ_DIR = "RudraScanner/ResearchBridge/requests"
RESULT_DIR = "RudraScanner/ResearchBridge/results"
JOB_TYPES = {"health_check", "research_46_batch", "research_46_finalize", "research_46_publish", "gann_nq_20261016", "gann_nq_october_2026", "three_candle_amd_probe", "three_candle_ibkr_one_candle", "ibkr_range_download", "yahoo_range_download", "mnq_month_download", "mes_month_download"}
MAX_JOBS_PER_TICK = 1
SYNC_VERSION = 2
BRIDGE_REF = "refs/asjr/research-bridge/main"
OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
JOB_FILE = re.compile(r"research-[0-9]{13}\.json")

def git(*args, cwd=None, timeout=90, input_text=None):
    return subprocess.run(["git", *args], cwd=REPO if cwd is None else cwd,
                          text=True, input=input_text,
                          env={**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"},
                          capture_output=True, timeout=timeout, check=False)

def origin_ok(url):
    if re.fullmatch(r"git@github\.com:raghunathbhandari/ASJR(?:\.git)?", url, re.I):
        return True
    parts = urlsplit(url)
    return (parts.scheme in {"https", "ssh"} and parts.hostname == "github.com"
            and parts.path.lower().rstrip("/").removesuffix(".git") == "/raghunathbhandari/asjr"
            and not parts.query and not parts.fragment)

def fetch_main(folder):
    # Dedicated ref; neither write nor consume the live bot's FETCH_HEAD.
    result = git("fetch", "-q", "--no-write-fetch-head", "--no-tags", "--refmap=",
                 "origin", "refs/heads/main:" + BRIDGE_REF, cwd=folder)
    if result.returncode:
        return None
    pinned = git("rev-parse", "--verify", BRIDGE_REF + "^{commit}", cwd=folder)
    sha = pinned.stdout.strip()
    return sha if not pinned.returncode and OID.fullmatch(sha) else None

def race_rejection(result):
    # --porcelain emits the rejection reason in stdout; never echo remote URLs.
    lines = (result.stdout + "\n" + result.stderr).splitlines()
    cas = re.search(r"cannot lock ref 'refs/heads/main': is at [0-9a-f]{40,64} "
                    r"but expected [0-9a-f]{40,64}\b", result.stderr)
    return bool(cas) or any(line.startswith("!\t") and "[rejected]" in line
               and ("(fetch first)" in line or "(non-fast-forward)" in line)
               for line in lines)

def safe_job(obj, file_id):
    if not isinstance(obj, dict) or not isinstance(file_id, str):
        return False
    if not (len(file_id) == 22 and file_id.startswith("research-") and
            file_id[9:].isdigit()):
        return False
    if obj.get("id") != file_id or obj.get("schema_version") != 1:
        return False
    operation = obj.get("operation")
    if operation not in JOB_TYPES:
        return False
    if operation in {"mnq_month_download", "mes_month_download"}:
        if set(obj) != {"id", "operation", "batch", "schema_version", "month"}:
            return False
        if obj["batch"] is not None:
            return False
        return isinstance(obj["month"], str) and obj["month"] in {
            "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
            "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"}
    if operation in {"ibkr_range_download", "yahoo_range_download"}:
        if set(obj) != {"id", "operation", "batch", "schema_version",
                        "ticker", "start_date", "end_date", "timeframe"}:
            return False
        if obj["batch"] is not None:
            return False
        import re
        from datetime import date
        ticker = obj["ticker"]
        if (not isinstance(ticker, str) or not re.fullmatch(
                r"[A-Z][A-Z0-9.]{0,9}" if operation == "ibkr_range_download"
                else r"[A-Z][A-Z0-9.=-]{0,14}", ticker)):
            return False
        if obj["timeframe"] not in {"1min", "5min", "15min", "30min", "1h", "1d"}:
            return False
        try:
            start_date, end_date = date.fromisoformat(obj["start_date"]), date.fromisoformat(obj["end_date"])
            days = (end_date - start_date).days + 1
        except (TypeError, ValueError):
            return False
        return (1 <= days <= 31 and
                not (obj["timeframe"] == "1min" and days > 7) and
                end_date <= datetime.now(timezone.utc).date())
    if set(obj) != {"id", "operation", "batch", "schema_version"}:
        return False
    return ((operation == "research_46_batch" and type(obj["batch"]) is int
             and 1 <= obj["batch"] <= 5) or
            (operation != "research_46_batch" and obj["batch"] is None))

def run_job(obj):
    operation = obj["operation"]
    if operation == "research_46_publish":
        try:
            return publish_research_files()
        except Exception as exc:
            # An export failure must be reported, not infinitely retried and
            # block every following research job.
            return {"status": "FAILED", "error": type(exc).__name__}
    if operation == "health_check":
        head = git("rev-parse", "--verify", "HEAD^{commit}")
        return {"status": "SUCCESS", "python": sys.version.split()[0],
                "worker_sync_version": SYNC_VERSION,
                "checkout_head": head.stdout.strip() if not head.returncode else None,
                "repo_present": (REPO / "RudraScanner/scan_now.py").is_file()}
    if operation == "mes_month_download":
        cmd = [sys.executable, "three_candle/ibkr_mes_bridge_month_download.py",
               "--job-id", obj["id"], "--month", obj["month"]]
        timeout = 1500
    elif operation == "mnq_month_download":
        cmd = [sys.executable, "three_candle/ibkr_mnq_bridge_month_download.py",
               "--job-id", obj["id"], "--month", obj["month"]]
        timeout = 1500
    elif operation == "yahoo_range_download":
        cmd = [sys.executable, "three_candle/yahoo_bridge_range_download.py",
               "--job-id", obj["id"], "--ticker", obj["ticker"],
               "--start", obj["start_date"], "--end", obj["end_date"],
               "--timeframe", obj["timeframe"]]
        timeout = 300
    elif operation == "ibkr_range_download":
        cmd = [sys.executable, "three_candle/ibkr_bridge_range_download.py",
               "--job-id", obj["id"], "--ticker", obj["ticker"],
               "--start", obj["start_date"], "--end", obj["end_date"],
               "--timeframe", obj["timeframe"]]
        timeout = 1800
    elif operation == "three_candle_ibkr_one_candle":
        cmd = [sys.executable, "three_candle/probe_ibkr_one_candle.py"]
        timeout = 60
    elif operation == "three_candle_amd_probe":
        # Read-only download test: returns metrics, never writes market datasets.
        cmd = [sys.executable, "three_candle/probe_amd_direct_download.py"]
        timeout = 90
    elif operation == "gann_nq_october_2026":
        cmd = [sys.executable, "RudraScanner/gann_october_import.py"]
        timeout = 300
    elif operation == "gann_nq_20261016":
        cmd = [sys.executable, "RudraScanner/gann_nq_import.py"]
        timeout = 180
    elif operation == "research_46_batch":
        cmd = [sys.executable, "RudraScanner/research_ema50_46.py",
               "--batch", str(obj["batch"])]
        timeout = 750
    else:
        cmd = [sys.executable, "RudraScanner/research_ema50_46.py", "--finalize"]
        timeout = 150
    # Strict fixed argv, no shell, only allowlisted scripts.
    try:
        done = subprocess.run(cmd, cwd=REPO, capture_output=True,
                              text=True, timeout=timeout, check=False)
        return {"status": "SUCCESS" if done.returncode == 0 else "FAILED",
                "exit_code": done.returncode,
                "stdout_tail": done.stdout[-4500:],
                "stderr_tail": done.stderr[-1300:]}
    except subprocess.TimeoutExpired:
        return {"status": "FAILED", "error": "TIMEOUT"}
    except Exception as exc:
        return {"status": "FAILED", "error": type(exc).__name__}


def publish_research_files():
    """Push only allowlisted research data files using an isolated git clone."""
    from RudraScanner.research_ema50_46 import NAMES
    source = REPO / "RudraScanner/ResearchData/EMA50_2026-10-15"
    files = [source / "research_metrics_46.csv", source / "RESEARCH_REPORT.md"]
    if not all(p.is_file() and not p.is_symlink() for p in files):
        return {"status": "FAILED", "error": "FINALIZE_REQUIRED"}
    for kind in ("daily", "five_minute"):
        files.extend(source / kind / (symbol + ".csv.gz") for symbol in NAMES
                     if (source / kind / (symbol + ".csv.gz")).is_file())
    if any(p.is_symlink() or p.stat().st_size > 3000000 for p in files):
        return {"status": "FAILED", "error": "UNSAFE_EXPORT"}
    with tempfile.TemporaryDirectory(prefix="asjr_research_export_") as temp:
        folder = Path(temp) / "repo"
        cp = subprocess.run(["git", "clone", "-q", "--no-checkout", "--shared",
                             str(REPO), str(folder)], capture_output=True, timeout=90)
        if cp.returncode: return {"status": "FAILED", "error": "CLONE"}
        origin = git("remote", "get-url", "origin")
        if origin.returncode or not origin_ok(origin.stdout.strip()):
            return {"status": "FAILED", "error": "ORIGIN"}
        if not setup_publisher(folder, origin.stdout.strip()):
            return {"status": "FAILED", "error": "PUBLISHER_SETUP"}
        for attempt in range(4):
            snapshot = fetch_main(folder)
            if not snapshot:
                return {"status": "FAILED", "error": "FETCH"}
            if git("checkout", "-q", "-B", "export-tmp", snapshot, cwd=folder).returncode:
                return {"status": "FAILED", "error": "CHECKOUT"}
            for path in files:
                dest = folder / path.relative_to(REPO)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
            if git("add", "--", *(str(p.relative_to(REPO)) for p in files), cwd=folder).returncode:
                return {"status": "FAILED", "error": "GIT_ADD"}
            diff = git("diff", "--cached", "--quiet", cwd=folder).returncode
            if diff == 0:
                return {"status": "SUCCESS", "files": len(files), "git": "UNCHANGED"}
            if diff != 1:
                return {"status": "FAILED", "error": "DIFF"}
            if git("commit", "-qm", "Research 46 OHLCV evidence", cwd=folder).returncode:
                return {"status": "FAILED", "error": "COMMIT"}
            pushed = git("push", "--porcelain", "origin", "HEAD:refs/heads/main", cwd=folder)
            if not pushed.returncode:
                return {"status": "SUCCESS", "files": len(files), "git": "PUSHED"}
            if not race_rejection(pushed):
                return {"status": "FAILED", "error": "PUSH_REJECTED_OR_UNCONFIRMED"}
            time.sleep(attempt + 1)
    return {"status": "FAILED", "error": "PUSH"}

def setup_publisher(folder, remote):
    return all(not git(*cmd, cwd=folder).returncode for cmd in (
        ("remote", "set-url", "origin", remote),
        ("config", "user.name", "ASJR Research Bridge"),
        ("config", "user.email", "asjr-research-bridge@users.noreply.github.com")))

def tree_rows(folder, sha, *paths):
    result = git("ls-tree", "-z", sha, "--", *paths, cwd=folder)
    if result.returncode:
        raise RuntimeError("cannot read pinned tree")
    entries = {}
    for record in result.stdout.split("\0"):
        if record:
            meta, path = record.split("\t", 1)
            mode, kind, oid = meta.split()
            if not OID.fullmatch(oid):
                raise ValueError("invalid Git object")
            entries[path] = (mode, kind, oid)
    return entries

def publish(job_id, report, request_oid):
    target = f"{RESULT_DIR}/{job_id}.json"
    request = f"{REQ_DIR}/{job_id}.json"
    # Separate scratch clone: never reset, stage or commit changes in live ASJR.
    with tempfile.TemporaryDirectory(prefix="asjr_research_bridge_") as temp:
        folder = Path(temp) / "repo"
        cloned = subprocess.run(
            ["git", "clone", "-q", "--no-checkout", "--shared", str(REPO), str(folder)],
            text=True, capture_output=True, timeout=90)
        if cloned.returncode:
            return False, "TEMP_CLONE_FAILED"
        # Use the same checked GitHub origin as main repo, not a new URL.
        origin = git("remote", "get-url", "origin")
        if origin.returncode:
            return False, "ORIGIN_MISSING"
        remote = origin.stdout.strip()
        # Remote may contain a credential; never expose it in report/log.
        if not origin_ok(remote):
            return False, "ORIGIN_UNEXPECTED"
        if not setup_publisher(folder, remote):
            return False, "PUBLISHER_SETUP_FAILED"
        for attempt in range(4):
            snapshot = fetch_main(folder)
            if not snapshot:
                return False, "FETCH_FAILED"
            # Recheck *on every attempt*, including races lost to another worker.
            entries = tree_rows(folder, snapshot, target, request)
            if target in entries:
                if entries[target][:2] != ("100644", "blob"):
                    return False, "RESULT_PATH_CONFLICT"
                return True, "ALREADY_PUBLISHED"
            if entries.get(request) != ("100644", "blob", request_oid):
                return False, "REQUEST_CHANGED"
            # Only a temporary index and one JSON blob; never materialise the
            # trading tree just to publish a small report.
            if git("read-tree", snapshot, cwd=folder).returncode:
                return False, "READ_TREE_FAILED"
            raw = json.dumps(report, indent=2, sort_keys=True) + "\n"
            blob = git("hash-object", "-w", "--stdin", input_text=raw, cwd=folder)
            oid = blob.stdout.strip()
            if (blob.returncode or not OID.fullmatch(oid) or
                    git("update-index", "--add", "--cacheinfo", "100644", oid, target,
                        cwd=folder).returncode):
                return False, "STAGE_FAILED"
            tree = git("write-tree", cwd=folder)
            if tree.returncode or not OID.fullmatch(tree.stdout.strip()):
                return False, "TREE_FAILED"
            delta = git("diff-tree", "--no-renames", "--no-commit-id", "--name-status",
                        "-r", snapshot, tree.stdout.strip(), cwd=folder)
            if delta.returncode or delta.stdout.splitlines() != ["A\t" + target]:
                return False, "UNEXPECTED_RESULT_DIFF"
            committed = git("commit-tree", tree.stdout.strip(), "-p", snapshot, "-m",
                            f"Research bridge result {job_id}", cwd=folder)
            sha = committed.stdout.strip()
            if committed.returncode or not OID.fullmatch(sha):
                return False, "COMMIT_FAILED"
            pushed = git("push", "--porcelain", "origin", sha + ":refs/heads/main", cwd=folder)
            if pushed.returncode == 0:
                latest = fetch_main(folder)
                if latest and tree_rows(folder, latest, target).get(target) == ("100644", "blob", oid):
                    return True, "PUSHED"
                return False, "PUSH_NOT_VERIFIED"
            if not race_rejection(pushed):
                return False, "PUSH_REJECTED_OR_UNCONFIRMED"
    return False, "PUSH_RETRY_EXHAUSTED"

def tick():
    common = git("rev-parse", "--git-common-dir")
    if common.returncode:
        print("BRIDGE | no Git directory", flush=True)
        return 2
    state = REPO / common.stdout.strip() / "asjr-research-bridge"
    state.mkdir(mode=0o700, exist_ok=True)
    # PrivateTmp differs between systemd and --once; use shared Git metadata.
    with (state / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("BRIDGE | BUSY", flush=True)
            return 0
        return tick_locked(state)

def save_pending(path, obj):
    # A later tick can retry the Git upload without repeating a completed job.
    with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", delete=False) as out:
        name = out.name
        try:
            json.dump(obj, out)
            out.flush()
            os.fsync(out.fileno())
        except BaseException:
            os.unlink(name)
            raise
    os.replace(name, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def tick_locked(state):
    remote_url = git("remote", "get-url", "origin")
    if remote_url.returncode or not origin_ok(remote_url.stdout.strip()):
        print("BRIDGE | invalid GitHub origin", flush=True)
        return 2
    snapshot = fetch_main(REPO)
    if not snapshot:
        print("BRIDGE | fetch failed", flush=True)
        return 2
    # One verified snapshot for both lists. An unreadable result tree is an
    # error, never evidence that every job needs to be executed again.
    requests = tree_rows(REPO, snapshot, REQ_DIR + "/")
    results = tree_rows(REPO, snapshot, RESULT_DIR + "/")
    processed = 0
    for path, (mode, kind, request_oid) in requests.items():
        parent, _, name = path.rpartition("/")
        if (parent != REQ_DIR or not JOB_FILE.fullmatch(name)
                or (mode, kind) != ("100644", "blob")):
            continue
        job_id = name[:-5]
        pending = state / name
        if f"{RESULT_DIR}/{name}" in results:
            pending.unlink(missing_ok=True)
            continue
        size = git("cat-file", "-s", request_oid)
        if size.returncode:
            raise RuntimeError("cannot read request size")
        if int(size.stdout) > 2048:
            continue
        raw = git("cat-file", "blob", request_oid)
        if raw.returncode:
            raise RuntimeError("cannot read request")
        try:
            obj = json.loads(raw.stdout)
        except ValueError:
            continue
        if not safe_job(obj, job_id):
            print(f"BRIDGE | rejected malformed request {job_id}", flush=True)
            continue
        if pending.exists():
            saved = json.loads(pending.read_text())
            if saved["request_oid"] != request_oid:
                print(f"BRIDGE | {job_id} | pending request changed; preserved", flush=True)
                continue
            report = saved["report"]
        else:
            print(f"BRIDGE | executing {job_id} {obj['operation']}", flush=True)
            stamp = datetime.now(timezone.utc).isoformat()
            result = run_job(obj)
            if obj["operation"] == "health_check":
                result["request_main"] = snapshot
            report = {"id": job_id, "operation": obj["operation"],
                      "completed_utc": datetime.now(timezone.utc).isoformat(),
                      "started_utc": stamp, **result}
            save_pending(pending, {"request_oid": request_oid, "report": report})
        ok, outcome = publish(job_id, report, request_oid)
        print(f"BRIDGE | {job_id} | {outcome} | {report['status']}", flush=True)
        processed += 1
        if not ok:
            return 2
        pending.unlink(missing_ok=True)
        if processed >= MAX_JOBS_PER_TICK:
            break
    if not processed:
        print("BRIDGE | IDLE", flush=True)
    return 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    if args.once:
        return tick()
    if not 60 <= args.interval <= 3600:
        parser.error("interval must be 60..3600 seconds")
    while True:
        try:
            tick()
        except Exception as exc:
            print(f"BRIDGE | worker error: {type(exc).__name__}", flush=True)
        time.sleep(args.interval)

if __name__ == "__main__":
    raise SystemExit(main())
