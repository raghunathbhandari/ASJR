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
    branch=None,
    logger=None,
):
    """
    Verify required DataLake outputs, commit only this trading day's
    DataLake folder, rebase on the checked-out branch, then push it.

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

    current_branch = _run_git(
        repo_root, "symbolic-ref", "--quiet", "--short", "HEAD"
    ).stdout.strip()
    if branch is not None and branch != current_branch:
        raise RuntimeError(
            f"Refusing to submit DataLake from {current_branch} to {branch}. "
            "Switch to the target branch first."
        )
    branch = current_branch

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

    # Rebase only onto the checked-out branch. Auto-stash unrelated local
    # edits (such as a previous day's log) while preserving them afterward.
    _run_git(
        repo_root,
        "pull",
        "--rebase",
        "--autostash",
        remote,
        branch,
    )

    push = _run_git(
        repo_root,
        "push",
        remote,
        f"HEAD:refs/heads/{branch}",
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
