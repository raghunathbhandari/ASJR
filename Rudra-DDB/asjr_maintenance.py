#!/usr/bin/env python3
"""ASJR/Rudra-DDB safe Git maintenance, for the existing Discord runner.

Discord entry: !runpy RudraScanner/scan_now\.py --maintenance
Does not register a Discord handler or enable an arbitrary shell.
Live bot: diagnose, optionally push pre-existing commits (no worktree edits).
Stopped bot: backup the local commit, stage only tracked DataLake edits, merge
only if cleanly possible, then push. Never reset, rebase, stash, force-push,
delete data, touch untracked files, or restart Chakra.
"""
from __future__ import annotations

import fcntl
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/root/trading/ASJR")
LOCK = Path("/tmp/asjr_maintenance.lock")
DATALAKE = "ASJR_Analyst/DataLake/"
REMOTE_PATTERN = re.compile(
    r"(?:git@github\.com:|https://github\.com/)"
    r"raghunathbhandari/ASJR(?:\.git)?/?", re.IGNORECASE
)


class MaintenanceRefused(RuntimeError):
    pass


def command(*args: str, timeout: int = 90):
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, text=True, capture_output=True,
            stdin=subprocess.DEVNULL, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MaintenanceRefused("Git subprocess unavailable or timed out") from exc


def checked(*args: str, timeout: int = 90) -> str:
    result = command(*args, timeout=timeout)
    if result.returncode:
        # Do not expose stderr: origin URL might contain credentials.
        raise MaintenanceRefused("Git operation failed: " + " ".join(args[:2]))
    return result.stdout.strip()


def bot_active() -> bool:
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", "trading_bot"],
            capture_output=True, timeout=8, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MaintenanceRefused("Could not verify trading_bot status") from exc
    if result.returncode not in (0, 1):
        raise MaintenanceRefused("Unexpected tmux response")
    return result.returncode == 0


def inside_git_worktree() -> None:
    if not ROOT.is_dir():
        raise MaintenanceRefused("Live ASJR checkout not found")
    if Path(checked("rev-parse", "--show-toplevel")).resolve() != ROOT:
        raise MaintenanceRefused("Unexpected repository location")
    if checked("branch", "--show-current") != "main":
        raise MaintenanceRefused("Expected main branch")
    if not REMOTE_PATTERN.fullmatch(checked("remote", "get-url", "origin")):
        raise MaintenanceRefused("Unexpected GitHub origin")
    gd = Path(checked("rev-parse", "--absolute-git-dir"))
    if any((gd / x).exists() for x in
           ("index.lock", "MERGE_HEAD", "CHERRY_PICK_HEAD", "rebase-apply",
            "rebase-merge", "REBASE_HEAD")):
        raise MaintenanceRefused("Another Git operation is active")


def maintain() -> int:
    inside_git_worktree()
    active = bot_active()
    status = checked("status", "--porcelain", "--untracked-files=no")
    dirty = [row[3:] for row in status.splitlines()]
    staged = checked("diff", "--cached", "--name-only").splitlines()
    checked("fetch", "origin", "main", timeout=120)
    left, right = (int(v) for v in checked(
        "rev-list", "--left-right", "--count", "HEAD...origin/main"
    ).split())
    print(f"RUDRA MAINTENANCE | bot={'RUNNING' if active else 'STOPPED'}")
    print(f"GIT | local-only={left} remote-only={right} tracked-modified={len(dirty)}")

    if active:
        if right == 0 and left == 0:
            print("PASS | Git synchronized; no changes made")
            return 0
        if right == 0 and left and not staged:
            checked("push", "origin", "main", timeout=120)
            print("PASS | Pushed existing local commits; Chakra untouched")
            return 0
        raise MaintenanceRefused(
            "Bot running: cannot safely merge or commit. "
            "Use !mbdstop, then rerun --maintenance."
        )

    if any(not path.startswith(DATALAKE) for path in dirty + staged):
        raise MaintenanceRefused(
            "Tracked non-DataLake edits found; manual review needed."
        )

    # Preserve original commit before any changes. No untracked files touched.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = "backup/rudra-maint-" + stamp
    checked("branch", backup)
    print("SAFETY | Original commit saved as", backup)

    if dirty:
        checked("add", "-u", "--", "ASJR_Analyst/DataLake", timeout=120)
        if command("diff", "--cached", "--quiet").returncode != 0:
            checked("commit", "-m", "Preserve tracked ASJR DataLake " + stamp,
                    timeout=120)
            print("DATALAKE | Tracked modifications committed")

    # Avoid merging while ANY tracked edits remain, especially user code.
    if checked("status", "--porcelain", "--untracked-files=no"):
        raise MaintenanceRefused("Tracked worktree not clean after DataLake commit")

    left, right = (int(v) for v in checked(
        "rev-list", "--left-right", "--count", "HEAD...origin/main"
    ).split())
    if right:
        result = command("merge", "--no-edit", "origin/main", timeout=180)
        if result.returncode:
            merge_head = Path(checked("rev-parse", "--absolute-git-dir")) / "MERGE_HEAD"
            if merge_head.exists():
                undo = command("merge", "--abort", timeout=90)
                if undo.returncode:
                    raise MaintenanceRefused(
                        "Merge conflict; automatic abort failed. STOP and inspect."
                    )
            raise MaintenanceRefused(
                "Merge refused/conflicted; aborted when possible. Backup preserved."
            )
        print("MERGE | Success")
    left, right = (int(v) for v in checked(
        "rev-list", "--left-right", "--count", "HEAD...origin/main"
    ).split())
    if right:
        raise MaintenanceRefused("Remote commits still missing; cannot push")
    if left:
        checked("push", "origin", "main", timeout=180)
        print("PUSH | Success")
    print("PASS | Git synchronized; untracked research files untouched")
    print("CHAKRA | STOPPED; restart separately with !mbdstart")
    return 0


def main() -> int:
    try:
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        with LOCK.open("a+") as file:
            try:
                fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print("MAINTENANCE | BUSY | another maintenance operation is running")
                return 2
            return maintain()
    except MaintenanceRefused as exc:
        print("MAINTENANCE | REFUSED |", exc)
        print("SAFE | no reset, rebase, stash, force-push, deletion or bot restart")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
