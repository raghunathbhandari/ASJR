"""Safe, isolated publisher for ASJR Analyst daily DataLake reports.

Drop-in replacement for ASJR_Analyst/Utils/asjr_git.py.
The live trading repository is never committed, checked out, or rebased.
"""

from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import time


def _git(cwd, *args, check=True):
    result = subprocess.run(
        ["git", *args], cwd=str(cwd), text=True, capture_output=True
    )
    if check and result.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({result.returncode})\n"
            f"{result.stdout}\n{result.stderr}"
        )
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
        push = _git(workdir, "push", "origin", f"HEAD:refs/heads/{branch}",
                    check=False)
        if push.returncode == 0:
            return {"status": "PUSHED", "commit_sha": sha,
                    "push_output": (push.stdout or push.stderr).strip()}

        # Only retry races; authentication, hooks and network errors stop.
        _git(workdir, "fetch", "origin", branch)
        latest = _git(workdir, "rev-parse", "FETCH_HEAD").stdout.strip()
        if latest == remote_sha:
            raise RuntimeError(f"Git push failed: {push.stderr}")
        if attempt < attempts:
            time.sleep(attempt)

    raise RuntimeError("Git push race persisted after 3 attempts")


def submit_datalake(trade_date, day_dir, required_files,
                    remote="origin", branch="main", logger=None):
    day_dir = Path(day_dir).resolve()
    repo_root = day_dir.parents[2]
    missing = [str(p) for p in required_files if not Path(p).is_file()]
    if missing:
        raise FileNotFoundError("Missing DataLake outputs: " + ", ".join(missing))
    if not day_dir.is_dir() or not day_dir.is_relative_to(repo_root):
        raise RuntimeError("DataLake directory is outside repository")
    relative_dir = day_dir.relative_to(repo_root)
    if relative_dir.parts[:2] != ("ASJR_Analyst", "DataLake"):
        raise RuntimeError(f"Refusing to publish unexpected path: {relative_dir}")
    if not branch or branch.startswith("-") or "/" in branch:
        raise ValueError("Invalid publication branch")

    # Preserve the files at invocation time; bots may continue generating data.
    with tempfile.TemporaryDirectory(prefix="asjr-publisher-") as temporary:
        root = Path(temporary)
        snapshot = root / "snapshot" / day_dir.name
        shutil.copytree(day_dir, snapshot, symlinks=False)
        remote_url = _git(repo_root, "remote", "get-url", remote).stdout.strip()
        workdir = root / "checkout"
        _git(root, "clone", "--quiet", "--depth", "1", "--no-checkout", "--single-branch",
             "--branch", branch, remote_url, str(workdir))
        base_sha = _git(workdir, "rev-parse", "HEAD").stdout.strip()

        try:
            result = _publish_snapshot(branch, relative_dir,
                                       snapshot, workdir, base_sha)
        except Exception as exc:
            # Reporting a publish failure must not mislabel successful collection.
            if logger:
                logger.error("DataLake publish pending: %s", exc)
            return {"status": "PENDING", "trade_date": str(trade_date),
                    "files_verified": len(required_files), "error": str(exc)}

    return {"trade_date": str(trade_date),
            "files_verified": len(required_files), **result}
