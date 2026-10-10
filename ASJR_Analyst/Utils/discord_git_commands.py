"""Allow-listed Discord helpers for ASJR GitHub pull/push via existing bot.

Load these from the existing external Discord message bot. This module does
NOT register commands, start a bot, stage files, commit, restart services,
or install an IBKR connection.

VPS repo: /root/trading/ASJR
Commands: !gitpull -> git pull --ff-only origin main
          !gitpush -> git push origin main (existing commits ONLY)

SECURITY: Discord user ID MUST match ASJR_DISCORD_GIT_ALLOWED_IDS.
No whitelist -> DENIED. Never accept a shell command or arbitrary Git args.
"""

from __future__ import annotations

import fcntl
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path("/root/trading/ASJR")
BRANCH = "main"
REMOTE = "origin"
ALLOWED_IDS_ENV = "ASJR_DISCORD_GIT_ALLOWED_IDS"
LOCK_PATH = Path("/tmp/asjr_discord_git_commands.lock")
MAX_MESSAGE = 1700
TIMEOUT_SECONDS = 90
_COMMANDS = {"!gitpull", "!gitpush"}


def _run(repo: Path, *args: str, timeout: int = TIMEOUT_SECONDS):
    """Run fixed argument-vector git commands. No shell interpolation."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(["git", *args], 124, "", "Git command timed out")
    except OSError as exc:
        return subprocess.CompletedProcess(["git", *args], 127, "", str(exc))


def _allowed(author_id, allowed_ids=None):
    """Fail closed if no actual Discord ID allowlist has been configured."""
    if allowed_ids is None:
        values = os.environ.get(ALLOWED_IDS_ENV, "")
        allowed_ids = {s.strip() for s in values.split(",") if s.strip()}
    else:
        allowed_ids = {str(value).strip() for value in allowed_ids}
    value = str(author_id).strip()
    return bool(value and value.isdecimal() and value in allowed_ids)


def _correct_origin(remote_url: str) -> bool:
    """Require the intended ASJR GitHub remote, not an arbitrary destination."""
    url = remote_url.strip()
    if re.fullmatch(
        r"git@github\.com:raghunathbhandari/ASJR(?:\.git)?",
        url, flags=re.IGNORECASE,
    ):
        return True
    parsed = urlparse(url)
    return (
        parsed.scheme in ("https", "ssh")
        and (parsed.hostname or "").lower() == "github.com"
        and parsed.path.lower().rstrip("/").removesuffix(".git")
        == "/raghunathbhandari/asjr"
    )


def _safe_excerpt(value: str) -> str:
    """Never echo full Git command stderr (might contain credential URL)."""
    lines = []
    for raw in value.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Redact any embedded HTTP basic-auth credential/userinfo in a URL.
        line = re.sub(r"https?://[^\s/@]+@github\.com", "https://github.com",
                      line, flags=re.IGNORECASE)
        lines.append(line[:260])
    return "\n".join(lines[-7:])[:MAX_MESSAGE]


def _failure(action: str, result) -> str:
    detail = _safe_excerpt((result.stderr or "") + "\n" + (result.stdout or ""))
    return (f"ASJR | {action} FAILED | exit={result.returncode}"
            + (f"\n{detail}" if detail else ""))


def run_git_command(command: str, author_id, *,
                    repo_root=REPO_ROOT, allowed_ids=None) -> str:
    """Handle EXACT !gitpull / !gitpush after validating Discord author ID.

    Suitable for calling in asyncio.to_thread() from existing Discord bot.
    No staging/commit in !gitpush: it pushes previously committed changes.
    """
    cmd = str(command).strip().lower()
    if cmd not in _COMMANDS:
        return "ASJR | UNKNOWN GIT COMMAND (allowed: !gitpull, !gitpush)"
    if not _allowed(author_id, allowed_ids=allowed_ids):
        return "ASJR | GIT ACCESS DENIED | authorised Discord users only"

    root = Path(repo_root).resolve()
    if not root.is_dir():
        return "ASJR | GIT FAILED | repository directory missing"

    # Nonblocking lock prevents two Discord users pulling/pushing concurrently.
    try:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOCK_PATH.open("a+") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return "ASJR | GIT BUSY | another Discord Git command is running"
            try:
                return _execute_checked(cmd, root)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    except Exception as exc:
        # Report errors to Discord without leaking credentials or traceback.
        return ("ASJR | GIT EXCEPTION | " +
                _safe_excerpt(f"{type(exc).__name__}: {exc}"))


def _execute_checked(cmd: str, root: Path) -> str:
    # No shell arguments ever come from Discord except the 2 fixed commands.
    worktree = _run(root, "rev-parse", "--show-toplevel")
    if worktree.returncode or Path(worktree.stdout.strip()).resolve() != root:
        return "ASJR | GIT FAILED | incorrect repository worktree"

    branch = _run(root, "branch", "--show-current")
    if branch.returncode or branch.stdout.strip() != BRANCH:
        return "ASJR | GIT REFUSED | checkout must be on main"

    origin = _run(root, "remote", "get-url", REMOTE)
    if origin.returncode or not _correct_origin(origin.stdout):
        return "ASJR | GIT REFUSED | origin is not the authorised ASJR GitHub repo"

    before = _run(root, "rev-parse", "--short", "HEAD")
    if before.returncode:
        return _failure("REF CHECK", before)

    if cmd == "!gitpull":
        # An ASJR cycle may be actively updating tracked DataLake/log files.
        # Do not overwrite, stash or reset any of that data via Discord.
        changed = _run(root, "status", "--porcelain", "--untracked-files=no")
        if changed.returncode:
            return _failure("STATUS", changed)
        if changed.stdout.strip():
            return ("ASJR | GIT PULL REFUSED | tracked files have local changes. "
                    "No reset, stash, or data loss performed.")
        result = _run(root, "pull", "--ff-only", REMOTE, BRANCH)
        if result.returncode:
            return _failure("PULL", result)
        after = _run(root, "rev-parse", "--short", "HEAD")
        if after.returncode:
            return _failure("PULL VERIFY", after)
        old, new = before.stdout.strip(), after.stdout.strip()
        state = "ALREADY UP TO DATE" if old == new else "UPDATED"
        return (f"ASJR | GIT PULL {state}\n"
                f"main: {old} -> {new}\n"
                "Updated files are on disk; restart the running bot only if needed.")

    # !gitpush: never implicitly add files/commit logs/stage credentials.
    result = _run(root, "push", REMOTE, BRANCH)
    if result.returncode:
        return _failure("PUSH", result)
    summary = _safe_excerpt((result.stdout or "") + "\n" + (result.stderr or ""))
    return (f"ASJR | GIT PUSH SUCCESS\n"
            f"main: {before.stdout.strip()}\n"
            "Existing commits pushed; uncommitted files were NOT uploaded."
            + (f"\n{summary}" if summary else ""))

