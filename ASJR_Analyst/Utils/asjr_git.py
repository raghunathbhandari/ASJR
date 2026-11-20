"""Safe, isolated publisher for ASJR Analyst daily DataLake reports.

Drop-in replacement for ASJR_Analyst/Utils/asjr_git.py.
The live trading repository is never committed, checked out, or rebased.
"""

from pathlib import Path
from datetime import date
import os
import re
import shutil
import subprocess
import tempfile
import time


def _git_error(stage, result):
    # Git can include a configured credential in either argv or stderr.
    # Preserve a useful failure class, not the remote URL or raw messages.
    msg = (result.stderr or "").lower()
    if any(s in msg for s in ("authentication", "permission denied", "could not read username")):
        reason = "authentication/permission"
    elif any(s in msg for s in ("protected branch", "hook declined", "repository rule")):
        reason = "remote policy"
    elif any(s in msg for s in ("resolve host", "timed out", "connection", "network")):
        reason = "connection"
    else:
        reason = "not confirmed"
    return RuntimeError(f"Git {stage} failed (exit {result.returncode}; {reason})")


def _git(cwd, *args, check=True):
    result = subprocess.run(
        ["git", *args], cwd=str(cwd), text=True, capture_output=True, timeout=300,
        env={**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"},
    )
    if check and result.returncode:
        raise _git_error("commit" if args[0] == "-c" else args[0], result)
    return result


def _publish_snapshot(branch, relative_dir, snapshot_dir, workdir,
                      base_sha, attempts=3):
    for attempt in range(1, attempts + 1):
        _git(workdir, "fetch", "origin", branch)
        remote_sha = _git(workdir, "rev-parse", "FETCH_HEAD").stdout.strip()

        # Never silently replace a remote edit to this day's DataLake folder.
        if remote_sha != base_sha:
            changes = _git(
                workdir, "diff", "--name-only", base_sha, remote_sha,
                "--", str(relative_dir),
            ).stdout.splitlines()
            if changes:
                raise RuntimeError(
                    "Remote DataLake folder changed during publication: "
                    + ", ".join(changes)
                )

        # The temporary checkout is disposable. Reset never touches production.
        _git(workdir, "checkout", "--force", "-B", "asjr-publish", remote_sha)
        target = workdir / relative_dir
        if (any(p.is_symlink() for p in (target, target.parent, target.parent.parent))
                or (target.exists() and any(p.is_symlink() for p in target.rglob("*")))):
            raise RuntimeError("Refused symlink in remote DataLake destination")
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(snapshot_dir, target, dirs_exist_ok=True)
        _git(workdir, "add", "--", str(relative_dir))
        staged = _git(workdir, "diff", "--cached", "--name-only").stdout.strip()
        if not staged:
            return {"status": "NO_CHANGES", "commit_sha": remote_sha}

        _git(workdir, "-c", "user.name=ASJR DataLake Publisher",
             "-c", "user.email=asjr-publisher@localhost", "commit", "-m",
             f"Update ASJR Analyst DataLake {snapshot_dir.name}")
        sha = _git(workdir, "rev-parse", "HEAD").stdout.strip()
        push = _git(workdir, "push", "--porcelain", "origin", f"HEAD:refs/heads/{branch}",
                    check=False)
        if push.returncode == 0:
            return {"status": "PUSHED", "commit_sha": sha,
                    "push_output": "Remote accepted the fast-forward push"}

        # Only retry races; authentication, hooks and network errors stop.
        cas = re.search(r"cannot lock ref 'refs/heads/" + re.escape(branch)
                        + r"': is at [0-9a-f]{40,64} but expected [0-9a-f]{40,64}\b",
                        push.stderr or "")
        if not cas and not any(line.startswith("!\t") and "[rejected]" in line and
                   ("(fetch first)" in line or "(non-fast-forward)" in line)
                   for line in (push.stdout or "").splitlines()):
            raise _git_error("push", push)
        if attempt < attempts:
            time.sleep(attempt)

    raise RuntimeError("Git push race persisted after 3 attempts")


def submit_datalake(trade_date, day_dir, required_files,
                    remote="origin", branch="main", logger=None):
    original = Path(day_dir)
    if any(p.is_symlink() for p in (original, original.parent, original.parent.parent)):
        raise ValueError("Refusing symlinked DataLake path")
    day_dir = original.resolve()
    repo_root = day_dir.parents[2]
    missing = [str(p) for p in required_files if not Path(p).is_file()]
    if missing:
        raise FileNotFoundError("Missing DataLake outputs: " + ", ".join(missing))
    if not day_dir.is_dir() or not day_dir.is_relative_to(repo_root):
        raise RuntimeError("DataLake directory is outside repository")
    relative_dir = day_dir.relative_to(repo_root)
    if relative_dir.parts[:2] != ("ASJR_Analyst", "DataLake"):
        raise RuntimeError(f"Refusing to publish unexpected path: {relative_dir}")
    if (len(relative_dir.parts) != 3 or day_dir.name != str(trade_date)
            or date.fromisoformat(day_dir.name).isoformat() != day_dir.name):
        raise ValueError("Expected exactly the requested ISO date folder")
    if not branch or branch.startswith("-") or "/" in branch:
        raise ValueError("Invalid publication branch")

    # Preserve the files at invocation time; bots may continue generating data.
    with tempfile.TemporaryDirectory(prefix="asjr-publisher-") as temporary:
        root = Path(temporary)
        snapshot = root / "snapshot" / day_dir.name
        workdir = root / "checkout"
        try:
            remote_url = _git(repo_root, "remote", "get-url", remote).stdout.strip()
            _git(root, "clone", "--quiet", "--depth", "1", "--no-checkout", "--single-branch",
                 "--branch", branch, remote_url, str(workdir))
            base_sha = _git(workdir, "rev-parse", "HEAD").stdout.strip()
            # Pin BEFORE copying. A same-day edit during the snapshot must
            # surface as a conflict, not become a silent part of the base.
            shutil.copytree(day_dir, snapshot, symlinks=True)
            if any(p.is_symlink() for p in snapshot.rglob("*")):
                raise RuntimeError("Refused symlink in local DataLake snapshot")
            result = _publish_snapshot(branch, relative_dir,
                                       snapshot, workdir, base_sha)
        except Exception as exc:
            # Reporting a publish failure must not mislabel successful collection.
            # TimeoutExpired includes complete argv, which may contain credentials.
            error = "Git operation timed out" if isinstance(exc, subprocess.TimeoutExpired) else str(exc)
            if logger:
                logger.error("DataLake publish pending: %s", error)
            return {"status": "PENDING", "trade_date": str(trade_date),
                    "files_verified": len(required_files), "error": error}

    return {"trade_date": str(trade_date),
            "files_verified": len(required_files), **result}
