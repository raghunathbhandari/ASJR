"""Admin-only, allowlisted ASJR server operations through the existing Discord bot.

This module does NOT register commands or start a bot. It is imported once by
the existing external Discord on_message handler. NO arbitrary shell, pipes,
redirection, user-supplied paths or executable arguments are accepted.

Commands: !runSCommand help|bot|uptime|disk|git|version|rvol|top|
          ibkr-raw|tests|final|logs [all|rvol|errors] [1..50]|
          files [reports|raw|processed|state]
"""
from __future__ import annotations

import fcntl
import os
import re
import subprocess
from collections import deque
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path("/root/trading/ASJR")
ALLOWED_IDS_ENV = "ASJR_DISCORD_GIT_ALLOWED_IDS"
ALLOWED_CHANNELS_ENV = "ASJR_DISCORD_SCOMMAND_ALLOWED_CHANNEL_IDS"
LOCK_PATH = Path("/tmp/asjr_discord_scommand.lock")
MAX_MESSAGE = 1700
PYTHON = Path("/root/trading/venv_new/bin/python")
ET = ZoneInfo("America/New_York")
HELP = (
    "ASJR | ADMIN COMMANDS\n"
    "!runSCommand bot | uptime | disk | git | version\n"
    "!runSCommand rvol | top | ibkr-raw | tests | final\n"
    "!runSCommand logs [all|rvol|errors] [1..50]\n"
    "!runSCommand files [reports|raw|processed|state]\n"
    "!runSCommand bridge-start | bridge-status\n"
    "Read-only tools/tests only. Git pull/push remain !gitpull / !gitpush."
)
SECRET = re.compile(
    r"(?i)(password|passphrase|secret|api[_-]?key|auth[_-]?token|"
    r"discord[_-]?token|private[_-]?key|bearer\s+[A-Za-z0-9])"
)
URL_CREDENTIALS = re.compile(r"(https?://)[^\s/@]+@", re.IGNORECASE)


def _ids(value):
    return {v.strip() for v in value.split(",") if v.strip()}


def _authorized(author_id, is_admin, channel_id, guild_id, *, allowed_ids=None,
                allowed_channels=None):
    # Both a Discord Administrator role AND an explicit numeric user ID.
    if is_admin is not True or guild_id is None:
        return False
    uid = str(author_id).strip()
    configured = (_ids(os.environ.get(ALLOWED_IDS_ENV, ""))
                  if allowed_ids is None
                  else {str(x).strip() for x in allowed_ids})
    if not uid.isdecimal() or uid not in configured:
        return False
    channels = (_ids(os.environ.get(ALLOWED_CHANNELS_ENV, ""))
                if allowed_channels is None
                else {str(x).strip() for x in allowed_channels})
    return not channels or str(channel_id) in channels


def _short(value):
    # No raw tracebacks, secrets or huge output in Discord.
    lines = []
    for line in str(value).splitlines():
        if SECRET.search(line):
            lines.append("[redacted sensitive line]")
        else:
            lines.append(URL_CREDENTIALS.sub(r"\1[redacted]@", line)[:250])
    text = "\n".join(lines)
    return text[:MAX_MESSAGE - 80] if text else "(no output)"


def _run(argv, root, *, timeout=15):
    try:
        result = subprocess.run(
            argv, cwd=str(root), capture_output=True, text=True,
            timeout=timeout, check=False, stdin=subprocess.DEVNULL,
        )
        return result.returncode, _short(
            (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        )
    except subprocess.TimeoutExpired:
        return 124, "Timed out after %ss" % timeout
    except OSError as exc:
        return 127, _short("%s: %s" % (type(exc).__name__, exc))


def _latest_day(root):
    lake = root / "ASJR_Analyst" / "DataLake"
    if not lake.is_dir():
        return None
    valid = []
    for entry in lake.iterdir():
        if not entry.is_dir() or entry.is_symlink():
            continue
        try:
            datetime.strptime(entry.name, "%Y-%m-%d")
        except ValueError:
            continue
        valid.append(entry)
    return sorted(valid, key=lambda p: p.name)[-1] if valid else None


def _logs(root, args):
    if len(args) > 2:
        return "USAGE | !runSCommand logs [all|rvol|errors] [1..50]"
    topic = "errors"
    count = 20
    if args:
        if args[0].isdigit():
            count = int(args[0])
        elif args[0] in ("all", "errors", "rvol"):
            topic = args[0]
        else:
            return "USAGE | !runSCommand logs [all|rvol|errors] [1..50]"
    if len(args) == 2:
        if args[0].isdigit() or not args[1].isdigit():
            return "USAGE | !runSCommand logs [all|rvol|errors] [1..50]"
        count = int(args[1])
    if not 1 <= count <= 50:
        return "DENIED | Log line count must be 1..50"
    day = _latest_day(root)
    if day is None:
        return "LOGS | No DataLake day found"
    files = [f for f in (day / "reports").glob("asjr_pipeline_*.log")
             if f.is_file() and not f.is_symlink()]
    if not files:
        return "LOGS | No pipeline logs in latest DataLake day"
    path = max(files, key=lambda f: f.stat().st_mtime)
    # A bounded tail is enough for 5-minute health; do not expose full logs.
    buf = deque(maxlen=count)
    with path.open("r", encoding="utf-8", errors="replace") as reader:
        for line in reader:
            tag = line.upper()
            if (topic == "rvol" and not any(
                    x in tag for x in ("RUDRA-PREMARKET", "RUDRA WAP", "RVOL5"))):
                continue
            if (topic == "errors" and not any(
                    x in tag for x in ("ERROR", "EXCEPTION", "FAILED", "TIMEOUT"))):
                continue
            buf.append(line.rstrip())
    return "LOGS | %s | %s\n%s" % (
        day.name, topic, _short("\n".join(buf)))


def _files(root, args):
    if len(args) != 1 or args[0] not in ("reports", "raw", "processed", "state"):
        return "USAGE | !runSCommand files [reports|raw|processed|state]"
    if args[0] == "state":
        directory = root / "ASJR_Analyst" / "state"
    else:
        day = _latest_day(root)
        if day is None:
            return "FILES | No DataLake day found"
        directory = day / args[0]
    if not directory.is_dir() or directory.is_symlink():
        return "FILES | Directory not found"
    names = sorted(f.name for f in directory.iterdir()
                   if f.is_file() and not f.is_symlink())[-35:]
    return "FILES | %s\n%s" % (args[0], "\n".join(names) or "(empty)")


def _execute(tokens, root):
    command, *args = tokens
    if command in ("help", "?") and not args:
        return HELP
    if command == "logs":
        return _logs(root, args)
    if command == "files":
        return _files(root, args)
    if args:
        return "DENIED | This command does not accept arguments\n" + HELP

    python = str(PYTHON)
    scan = "RudraScanner/scan_now.py"
    commands = {
        "bridge-start": ([python, "RudraScanner/ResearchBridge/install_bridge.py"], 45),
        "bridge-status": (["systemctl", "is-active", "asjr-research-bridge.service"], 10),
        "uptime": (["uptime"], 10),
        "disk": (["df", "-h", str(root)], 10),
        "git": (["git", "status", "--short", "--untracked-files=no"], 10),
        "version": (["git", "log", "-1", "--format=%h %cs %s"], 10),
        "rvol": ([python, scan, "--rvol-status"], 25),
        "top": ([python, scan, "--top"], 25),
        "ibkr-raw": ([python, scan, "--ibkr-raw"], 25),
        "tests": ([python, scan, "--self-test"], 90),
        "final": ([python, scan, "--final-check"], 90),
        "bot": (["tmux", "has-session", "-t", "trading_bot"], 10),
    }
    entry = commands.get(command)
    if entry is None:
        return "DENIED | Unknown admin operation\n" + HELP
    code, output = _run(entry[0], root, timeout=entry[1])
    if command == "bot":
        if code == 0:
            return "BOT | RUNNING | tmux trading_bot"
        if code == 1:
            return "BOT | STOPPED | tmux trading_bot"
    return "SCOMMAND | %s | exit=%s\n%s" % (
        command.upper(), code, output)


def run_scommand(text, author_id, *, is_admin=False, guild_id=None,
                 channel_id=None, repo_root=REPO_ROOT, allowed_ids=None,
                 allowed_channels=None):
    """Single synchronous handler; run with asyncio.to_thread() on Discord.

    Server-owned predefined operations only. An Administrator role alone
    does NOT grant access; an explicit numeric Discord ID is also required.
    """
    if not _authorized(author_id, is_admin, channel_id, guild_id,
                       allowed_ids=allowed_ids, allowed_channels=allowed_channels):
        return "SCOMMAND | DENIED | Discord admin + user ID required"
    parts = str(text).strip().split()
    if not parts or parts[0].lower() != "!runscommand":
        return "SCOMMAND | UNKNOWN COMMAND"
    if len(parts) > 5 or len(str(text)) > 150:
        return "SCOMMAND | DENIED | Command too long"
    if len(parts) == 1:
        return HELP
    root = Path(repo_root).resolve()
    if not root.is_dir():
        return "SCOMMAND | FAILED | ASJR repo missing"
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LOCK_PATH.open("a+") as guard:
            try:
                fcntl.flock(guard.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return "SCOMMAND | BUSY | Another server command is running"
            return _execute([p.lower() for p in parts[1:]], root)
    except Exception as exc:
        return "SCOMMAND | ERROR | %s" % _short(type(exc).__name__)
