#!/usr/bin/env python3
"""Restricted GitHub -> ASJR VPS administrative bridge.
Requests on GitHub rudra-admin-results: Rudra-DDB/AdminBridge/requests/admin-<13digits>.json
Results on GitHub rudra-admin-results: Rudra-DDB/AdminBridge/results/<same-id>.json

Strict operations: health, diagnose, maintenance, cleanup_audit.
No arbitrary argv, shell, trade orders, force push, hard reset, deletion,
root shell, scheduler edits, or service restarts. Maintenance uses existing
asjr_maintenance.py, which refuses merges while Chakra is running.
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
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/root/trading/ASJR")
REQUESTS = "Rudra-DDB/AdminBridge/requests"
RESULTS = "Rudra-DDB/AdminBridge/results"
RESULT_BRANCH = "rudra-admin-results"
LOCK = Path("/tmp/asjr_admin_bridge.lock")
OPERATIONS = {"health", "diagnose", "maintenance", "cleanup_audit", "data_inventory", "import_nq_intc_5m", "yahoo_import"}
ID = re.compile(r"admin-[0-9]{13}\Z")
MAX_OUTPUT = 2200


def run(*args, cwd=ROOT, timeout=90):
    return subprocess.run(list(args), cwd=cwd, text=True,
                          stdin=subprocess.DEVNULL, capture_output=True,
                          timeout=timeout, check=False)


def git(*args, cwd=ROOT, timeout=90):
    return run("git", *args, cwd=cwd, timeout=timeout)


def report_error(kind):
    return {"status": "FAILED", "reason": kind}


def valid(job, identifier):
    if type(job) is not dict or not ID.fullmatch(identifier):
        return False
    if job.get("schema_version") != 1 or job.get("id") != identifier:
        return False
    if job.get("operation") == "yahoo_import":
        return set(job) == {"schema_version", "id", "operation", "symbols", "interval", "start", "end"}
    return set(job) == {"schema_version", "id", "operation"} and job.get("operation") in OPERATIONS


def execute(operation, job=None):
    if operation == "yahoo_import":
        import importlib.util
        path = ROOT / "Rudra-DDB/AdminBridge/yahoo_import.py"
        if not path.is_file() or path.is_symlink():
            return report_error("YAHOO_IMPORT_NOT_DEPLOYED")
        spec = importlib.util.spec_from_file_location("admin_yahoo_import", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.import_history(job)
    if operation == "health":
        return {"status": "SUCCESS", "python": sys.version.split()[0],
                "root_exists": ROOT.is_dir()}
    if operation == "diagnose":
        result = {}
        for label, command in {
            "branch": ("branch", "--show-current"),
            "tracked_status": ("status", "--short", "--untracked-files=no"),
            "divergence": ("rev-list", "--left-right", "--count", "HEAD...origin/main"),
        }.items():
            cmd = git(*command)
            if cmd.returncode:
                return report_error("GIT_" + label.upper())
            result[label] = cmd.stdout[:MAX_OUTPUT].strip()
        tmux = run("tmux", "has-session", "-t", "trading_bot", timeout=8)
        result["chakra"] = "RUNNING" if tmux.returncode == 0 else "STOPPED" if tmux.returncode == 1 else "UNKNOWN"
        result["status"] = "SUCCESS"
        return result
    if operation == "import_nq_intc_5m":
        import importlib.util
        path = ROOT / "Rudra-DDB/AdminBridge/import_nq_intc_5m.py"
        if not path.is_file() or path.is_symlink():
            return report_error("IMPORT_MODULE_MISSING")
        spec=importlib.util.spec_from_file_location("admin_fixed_5m", path)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.execute()
    if operation == "data_inventory":
        # Strict fixed paths: metadata only; no user paths, no sample rows,
        # no data changes and no broker/network calls.
        paths = {
            "research_46_metrics": "RudraScanner/ResearchData/EMA50_2026-10-15/research_metrics_46.csv",
            "nq_import_script": "RudraScanner/gann_nq_import.py",
            "nq_october_script": "RudraScanner/gann_october_import.py",
            "yahoo_research_import_script": "RudraScanner/research_ema50_46.py",
            "datalake_root": "ASJR_Analyst/DataLake",
        }
        result = {}
        for name, relative in paths.items():
            item = ROOT / relative
            result[name] = {
                "exists": item.exists() and not item.is_symlink(),
                "bytes": item.stat().st_size if item.is_file() and not item.is_symlink() else None,
            }
        return {"status":"SUCCESS", "mode":"READ_ONLY_METADATA", "assets":result}
    if operation == "cleanup_audit":
        # Never run the potentially destructive cleanup scheduler.
        # Observe candidate dated folders only. No filesystem mutations.
        from datetime import date, timedelta
        import re as _re
        root = ROOT / "ASJR_Analyst" / "DataLake"
        today = datetime.now(timezone.utc).date()
        cutoff = today - timedelta(days=5)
        candidates = []
        if root.exists():
            for folder in root.iterdir():
                if (not folder.is_dir() or folder.is_symlink()
                        or not _re.fullmatch(r"\d{4}-\d{2}-\d{2}", folder.name)):
                    continue
                try:
                    day = date.fromisoformat(folder.name)
                except ValueError:
                    continue
                if day < cutoff:
                    candidates.append(folder.name)
        return {"status":"SUCCESS", "mode":"DRY_RUN_ONLY",
                "cutoff_utc": str(cutoff), "candidate_count":len(candidates),
                "candidate_dates":sorted(candidates)[-25:]}
    if operation == "maintenance":
        # Exact fixed file and argv, never command from job payload.
        script = ROOT / "Rudra-DDB" / "asjr_maintenance.py"
        if not script.is_file():
            return report_error("MAINTENANCE_NOT_DEPLOYED")
        p = run(sys.executable, str(script), timeout=240)
        return {"status": "SUCCESS" if p.returncode == 0 else "REFUSED",
                "exit_code":p.returncode, "output":p.stdout[-MAX_OUTPUT:],
                "error_type": "NONE" if p.returncode == 0 else "MAINTENANCE_REFUSED"}
    return report_error("OP_NOT_ALLOWED")


def publish(identifier, result):
    target = f"{RESULTS}/{identifier}.json"
    origin = git("remote", "get-url", "origin")
    if origin.returncode or not re.fullmatch(
        r"(?:git@github\.com:|https://github\.com/)raghunathbhandari/ASJR(?:\.git)?/?",
        origin.stdout.strip(), re.I
    ):
        return False
    with tempfile.TemporaryDirectory(prefix="asjr_admin_bridge_") as tmp:
        folder = Path(tmp) / "repo"
        if git("clone", "-q", "--no-checkout", str(ROOT), str(folder), timeout=120).returncode:
            return False
        git("remote", "set-url", "origin", origin.stdout.strip(), cwd=folder)
        git("config", "user.name", "ASJR Admin Bridge", cwd=folder)
        git("config", "user.email", "asjr-admin-bridge@users.noreply.github.com", cwd=folder)
        for attempt in range(4):
            if git("fetch", "-q", "origin", RESULT_BRANCH, cwd=folder).returncode:
                return False
            if git("checkout", "-q", "-B", "admin-result", "FETCH_HEAD", cwd=folder).returncode:
                return False
            out = folder / target
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
            if git("add", "--", target, cwd=folder).returncode:
                return False
            if git("commit", "-qm", f"ASJR admin bridge result {identifier}", cwd=folder).returncode:
                return False
            if git("push", "-q", "origin", "HEAD:refs/heads/" + RESULT_BRANCH, cwd=folder, timeout=120).returncode == 0:
                return True
            time.sleep(attempt+1)
    return False


def tick():
    origin = git("remote", "get-url", "origin")
    if origin.returncode or not re.fullmatch(
        r"(?:git@github\.com:|https://github\.com/)raghunathbhandari/ASJR(?:\.git)?/?",
        origin.stdout.strip(), re.I
    ):
        print("ADMIN BRIDGE | unauthorized origin", flush=True)
        return 2
    if git("fetch", "-q", "origin", RESULT_BRANCH).returncode:
        print("ADMIN BRIDGE | fetch failed", flush=True)
        return 2
    listed = git("ls-tree", "-r", "--name-only", "FETCH_HEAD", REQUESTS)
    if listed.returncode:
        return 2
    for path in listed.stdout.splitlines():
        if not path.startswith(REQUESTS + "/") or not path.endswith(".json"):
            continue
        identifier = Path(path).stem
        if not ID.fullmatch(identifier):
            continue
        if git("fetch", "-q", "origin", RESULT_BRANCH).returncode:
            return 2
        if git("cat-file", "-e", f"FETCH_HEAD:{RESULTS}/{identifier}.json").returncode == 0:
            continue
        raw = git("show", f"FETCH_HEAD:{path}")
        if raw.returncode or len(raw.stdout) > 2048:
            continue
        try:
            job = json.loads(raw.stdout)
        except ValueError:
            continue
        if not valid(job, identifier):
            continue
        print(f"ADMIN BRIDGE | {identifier} {job['operation']}", flush=True)
        try:
            result = execute(job["operation"], job)
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = report_error(type(exc).__name__)
        result.update({"id":identifier, "operation":job["operation"],
                       "completed_utc":datetime.now(timezone.utc).isoformat()})
        if not publish(identifier, result):
            print("ADMIN BRIDGE | result publish failed; stop before replay", flush=True)
            return 2
        print(f"ADMIN BRIDGE | result {result['status']}", flush=True)
        return 0
    print("ADMIN BRIDGE | IDLE", flush=True)
    return 0


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--once",action="store_true")
    p.add_argument("--interval",type=int,default=60)
    args=p.parse_args()
    if not 60 <= args.interval <= 3600:
        p.error("interval must be 60..3600")
    LOCK.parent.mkdir(parents=True,exist_ok=True)
    with LOCK.open("a+") as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("ADMIN BRIDGE | another worker active", flush=True)
            return 2
        if args.once: return tick()
        while True:
            try: tick()
            except Exception as exc:
                print("ADMIN BRIDGE | worker failure",type(exc).__name__,flush=True)
            time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
