from pathlib import Path
import subprocess

def _run_git(repo_root, *args, check=True):
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        text=True,
        capture_output=True,
    )

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Git command failed: git {' '.join(args)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    return result


def submit_datalake(
    trade_date,
    day_dir,
    required_files,
    remote="origin",
    branch="main",
    logger=None,
):
    """
    Verify required DataLake outputs, commit only this trading day's
    DataLake folder, rebase on latest remote main, then push.

    No force-push is ever used.
    """
    day_dir = Path(day_dir).resolve()
    repo_root = day_dir.parents[2]

    missing = [
        str(Path(p))
        for p in required_files
        if not Path(p).exists()
    ]

    if missing:
        raise FileNotFoundError(
            "ASJR DataLake submit aborted. Missing required files:\n"
            + "\n".join(missing)
        )

    inside = _run_git(
        repo_root,
        "rev-parse",
        "--is-inside-work-tree",
    ).stdout.strip()

    if inside.lower() != "true":
        raise RuntimeError(
            f"Not inside a Git repository: {repo_root}"
        )

    relative_day_dir = day_dir.relative_to(repo_root)

    print("\n========== GIT DATALAKE SUBMIT ==========")
    print("Repo:", repo_root)
    print("DataLake:", relative_day_dir)
    print("Verified Files:", len(required_files))

    # Stage only today's DataLake folder.
    _run_git(
        repo_root,
        "add",
        str(relative_day_dir),
    )

    staged = _run_git(
        repo_root,
        "diff",
        "--cached",
        "--name-only",
    ).stdout.strip()

    if not staged:
        print("Git: No DataLake changes to commit.")
        return {
            "status": "NO_CHANGES",
            "trade_date": str(trade_date),
            "files_verified": len(required_files),
        }

    print("Staged:")
    print(staged)

    message = f"Update ASJR Analyst DataLake {trade_date}"

    _run_git(
        repo_root,
        "commit",
        "-m",
        message,
    )

    # Remote may contain newer ASJR code. Rebase the local DataLake
    # commit safely before pushing. Never force-push.
    _run_git(
        repo_root,
        "pull",
        "--rebase",
        remote,
        branch,
    )

    push = _run_git(
        repo_root,
        "push",
        remote,
        branch,
    )

    commit_sha = _run_git(
        repo_root,
        "rev-parse",
        "HEAD",
    ).stdout.strip()

    print("Git Push: SUCCESS")
    print("Commit:", commit_sha)

    return {
        "status": "PUSHED",
        "trade_date": str(trade_date),
        "files_verified": len(required_files),
        "commit_sha": commit_sha,
        "push_output": (push.stdout or push.stderr).strip(),
    }
