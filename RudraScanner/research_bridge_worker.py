#!/usr/bin/env python3
"""Restricted, read-only-to-live-tree GitHub research job worker.

Only polls GitHub main for approved job JSON; no arbitrary shell or
Discord/Chakra/IBKR calls. Results are committed using a separate temporary
git clone to avoid modifying the live ASJR worktree.
"""
from __future__ import annotations
import argparse
import shutil
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/root/trading/ASJR")
# Script is launched by absolute path from systemd, so package root is not
# automatically importable when publishing isolated research evidence.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
REQ_DIR = "RudraScanner/ResearchBridge/requests"
RESULT_DIR = "RudraScanner/ResearchBridge/results"
JOB_TYPES = {"health_check", "research_46_batch", "research_46_finalize", "research_46_publish"}
MAX_JOBS_PER_TICK = 1

def git(*args, cwd=REPO, timeout=90):
    return subprocess.run(["git", *args], cwd=cwd, text=True,
                          capture_output=True, timeout=timeout, check=False)

def safe_job(obj, file_id):
    if not isinstance(obj, dict) or set(obj) != {"id", "operation", "batch", "schema_version"}:
        return False
    if obj["schema_version"] != 1 or obj["id"] != file_id or not isinstance(file_id, str):
        return False
    if not (len(file_id) == 22 and file_id.startswith("research-") and
            file_id[9:].isdigit()):
        return False
    if obj["operation"] not in JOB_TYPES:
        return False
    return ((obj["operation"] == "research_46_batch" and type(obj["batch"]) is int
             and 1 <= obj["batch"] <= 5) or
            (obj["operation"] != "research_46_batch" and obj["batch"] is None))

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
        return {"status": "SUCCESS", "python": sys.version.split()[0],
                "repo_present": (REPO / "RudraScanner/scan_now.py").is_file()}
    if operation == "research_46_batch":
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
        if origin.returncode or "github.com" not in origin.stdout:
            return {"status": "FAILED", "error": "ORIGIN"}
        git("remote", "set-url", "origin", origin.stdout.strip(), cwd=folder)
        git("config", "user.name", "ASJR Research Bridge", cwd=folder)
        git("config", "user.email", "asjr-research-bridge@users.noreply.github.com", cwd=folder)
        for attempt in range(4):
            if git("fetch", "-q", "origin", "main", cwd=folder).returncode:
                return {"status": "FAILED", "error": "FETCH"}
            if git("checkout", "-q", "-B", "export-tmp", "FETCH_HEAD", cwd=folder).returncode:
                return {"status": "FAILED", "error": "CHECKOUT"}
            for path in files:
                dest = folder / path.relative_to(REPO)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
            if git("add", "--", *(str(p.relative_to(REPO)) for p in files), cwd=folder).returncode:
                return {"status": "FAILED", "error": "GIT_ADD"}
            if git("diff", "--cached", "--quiet", cwd=folder).returncode == 0:
                return {"status": "SUCCESS", "files": len(files), "git": "UNCHANGED"}
            if git("commit", "-qm", "Research 46 OHLCV evidence", cwd=folder).returncode:
                return {"status": "FAILED", "error": "COMMIT"}
            if git("push", "-q", "origin", "HEAD:refs/heads/main", cwd=folder).returncode == 0:
                return {"status": "SUCCESS", "files": len(files), "git": "PUSHED"}
            time.sleep(attempt + 1)
    return {"status": "FAILED", "error": "PUSH"}

def publish(job_id, report):
    target = f"{RESULT_DIR}/{job_id}.json"
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
        if "github.com" not in remote:
            return False, "ORIGIN_UNEXPECTED"
        git("remote", "set-url", "origin", remote, cwd=folder)
        git("config", "user.name", "ASJR Research Bridge", cwd=folder)
        git("config", "user.email", "asjr-research-bridge@users.noreply.github.com", cwd=folder)
        for attempt in range(4):
            if git("fetch", "-q", "origin", "main", cwd=folder).returncode:
                return False, "FETCH_FAILED"
            if git("checkout", "-q", "-B", "bridge-temp", "FETCH_HEAD", cwd=folder).returncode:
                return False, "CHECKOUT_FAILED"
            out = folder / target
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            git("add", "--", target, cwd=folder)
            committed = git("commit", "-qm", f"Research bridge result {job_id}", cwd=folder)
            if committed.returncode:
                return False, "COMMIT_FAILED"
            pushed = git("push", "-q", "origin", "HEAD:refs/heads/main", cwd=folder)
            if pushed.returncode == 0:
                return True, "PUSHED"
            time.sleep(attempt + 1)
    return False, "PUSH_RETRY_EXHAUSTED"

def tick():
    remote_url = git("remote", "get-url", "origin")
    if remote_url.returncode or "github.com" not in remote_url.stdout:
        print("BRIDGE | invalid GitHub origin", flush=True)
        return 2
    fetch = git("fetch", "-q", "origin", "main")
    if fetch.returncode:
        print("BRIDGE | fetch failed", flush=True)
        return 2
    tree = git("ls-tree", "-r", "--name-only", "FETCH_HEAD", REQ_DIR)
    if tree.returncode:
        print("BRIDGE | request list unavailable", flush=True)
        return 2
    processed = 0
    for path in tree.stdout.splitlines():
        if not path.startswith(REQ_DIR + "/") or not path.endswith(".json"):
            continue
        job_id = Path(path).stem
        if (REPO / RESULT_DIR / f"{job_id}.json").exists():
            # Local repository may not reflect remote result. Check GitHub ref.
            pass
        already = git("cat-file", "-e", f"FETCH_HEAD:{RESULT_DIR}/{job_id}.json")
        if already.returncode == 0:
            continue
        raw = git("show", f"FETCH_HEAD:{path}")
        if raw.returncode or len(raw.stdout) > 2048:
            continue
        try:
            obj = json.loads(raw.stdout)
        except ValueError:
            continue
        if not safe_job(obj, job_id):
            print(f"BRIDGE | rejected malformed request {job_id}", flush=True)
            continue
        print(f"BRIDGE | executing {job_id} {obj['operation']}", flush=True)
        stamp = datetime.now(timezone.utc).isoformat()
        result = run_job(obj)
        report = {"id": job_id, "operation": obj["operation"],
                  "completed_utc": datetime.now(timezone.utc).isoformat(),
                  "started_utc": stamp, **result}
        ok, state = publish(job_id, report)
        print(f"BRIDGE | {job_id} | {state} | {result['status']}", flush=True)
        processed += 1
        if not ok:
            return 2
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
