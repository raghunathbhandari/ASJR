#!/usr/bin/env python3
"""One-shot ASJR Git recovery, only when Chakra is stopped.

Refuses unrelated local changes and unexpected remotes; preserves commits and
DataLake edits. Never hard-resets, rebases, force-pushes, or deletes a stash.
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
from pathlib import Path

ROOT = Path("/root/trading/ASJR")
BACKUPS = Path("/root/trading/asjr-git-recovery")
EXPECTED = "raghunathbhandari/ASJR"
DATALAKE = "ASJR_Analyst/DataLake/"


def git(*args, timeout=120):
    return subprocess.run(["git", *args], cwd=ROOT, text=True,
                          capture_output=True, check=False, timeout=timeout)


def step(*args, timeout=120):
    result = git(*args, timeout=timeout)
    if result.returncode:
        raise RuntimeError("git " + " ".join(args[:2]) + " failed: " +
                           (result.stderr or result.stdout)[-300:])
    return result.stdout.strip()


def preflight():
    if not ROOT.is_dir():
        raise RuntimeError("ASJR directory missing")
    if Path(step("rev-parse", "--show-toplevel")).resolve() != ROOT:
        raise RuntimeError("Wrong Git working tree")
    if step("branch", "--show-current") != "main":
        raise RuntimeError("Live branch must be main")
    url = step("remote", "get-url", "origin")
    if not re.fullmatch(r"(?:git@github\.com:|https://github\.com/)" +
                        re.escape(EXPECTED) + r"(?:\.git)?/?", url, re.I):
        raise RuntimeError("Unexpected GitHub remote")
    gd = Path(step("rev-parse", "--absolute-git-dir"))
    for marker in ("index.lock", "MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD",
                   "rebase-merge", "rebase-apply"):
        if (gd / marker).exists():
            raise RuntimeError("Active Git operation: " + marker)
    try:
        bot = subprocess.run(["tmux", "has-session", "-t", "trading_bot"],
                             capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("Cannot verify Chakra stopped; refusing")
    if bot.returncode != 1:
        raise RuntimeError("Chakra must be stopped using !mbdstop first")
    status = step("status", "--porcelain", "--untracked-files=no")
    for line in status.splitlines():
        path = line[3:]
        if not path.startswith(DATALAKE):
            raise RuntimeError("Modified non-DataLake file: " + path[:90])
    return status


def main():
    try:
        status = preflight()
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_dir = BACKUPS / stamp
        backup_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
        start_sha = step("rev-parse", "HEAD")
        branch = "backup/asjr-" + stamp
        step("branch", branch, start_sha)
        (backup_dir / "HEAD.txt").write_text(start_sha + "\n" + branch + "\n")
        (backup_dir / "status.txt").write_text(status + "\n")
        patch = step("diff", "HEAD", "--binary", timeout=180)
        (backup_dir / "tracked.patch").write_text(patch + "\n")
        print("BACKUP | original commit and patch saved |", backup_dir, flush=True)

        # Fetch before stashing: a network failure cannot remove working files.
        step("fetch", "origin", "main", timeout=180)
        stash_sha = None
        if status:
            step("stash", "push", "-m", "ASJR recovery " + stamp, timeout=180)
            stash_sha = step("rev-parse", "refs/stash")
            (backup_dir / "stash_sha.txt").write_text(stash_sha + "\n")
        print("LOCAL | tracked DataLake edits preserved", flush=True)
        ahead = step("rev-list", "--left-right", "--count", "HEAD...origin/main")
        print("DIVERGENCE | local-only / remote-only:", ahead.replace("\t", " / "), flush=True)

        merged = git("merge", "--no-edit", "origin/main", timeout=180)
        if merged.returncode:
            gd = Path(step("rev-parse", "--absolute-git-dir"))
            if (gd / "MERGE_HEAD").exists():
                abort = git("merge", "--abort", timeout=120)
                if abort.returncode:
                    print("MERGE ABORT FAILED | manual review required", flush=True)
            if stash_sha and not (gd / "MERGE_HEAD").exists():
                recovery = git("stash", "apply", stash_sha, timeout=180)
                if recovery.returncode:
                    print("RESTORE | MANUAL REVIEW | local edits remain in stash", flush=True)
                else:
                    print("RESTORE | original local edits recovered; stash retained", flush=True)
            print("MERGE | CONFLICT/ERROR | backup/stash retained", flush=True)
            print((merged.stderr or merged.stdout)[-700:], flush=True)
            return 2
        print("MERGE | SUCCESS", flush=True)

        if stash_sha:
            restored = git("stash", "apply", stash_sha, timeout=180)
            if restored.returncode:
                print("RESTORE | CONFLICT | stash retained; manual review", flush=True)
                print((restored.stderr or restored.stdout)[-500:], flush=True)
                return 2
            step("add", "-u", "--", "ASJR_Analyst/DataLake", timeout=120)
            if git("diff", "--cached", "--quiet").returncode != 0:
                step("commit", "-m", "Preserve ASJR DataLake edits " + stamp,
                     timeout=180)
        print("DATALAKE | local edits preserved", flush=True)

        pushed = git("push", "origin", "main", timeout=180)
        if pushed.returncode:
            print("PUSH | FAILED | commits preserved, no force push", flush=True)
            print((pushed.stderr or pushed.stdout)[-500:], flush=True)
            return 2
        print("PUSH | SUCCESS |", step("rev-parse", "--short", "HEAD"), flush=True)
        print("RECOVERY | SUCCESS | backup/stash intentionally retained", flush=True)
        print("CHAKRA | STOPPED | now use !mbdstart", flush=True)
        return 0
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
        print("RECOVERY | REFUSED/FAILED |", str(exc)[-450:], flush=True)
        print("No hard reset, force push, or stash deletion performed.", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
