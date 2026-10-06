"""
One-time Forex downloader launcher for the external Chakra bot.

Safe to call on every bot cycle. The shell launcher prevents duplicate work and
will only start the EURUSD historical download once unless the .done marker is
removed deliberately.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


ASJR_ROOT = Path("/root/trading/ASJR")
LAUNCHER = ASJR_ROOT / "Backtesting" / "DataLoader" / "run_forex_download_tmux.sh"


def launch_forex_download_once() -> dict:
    """Launch the one-time EURUSD history import in detached tmux."""
    if not LAUNCHER.exists():
        return {
            "started": False,
            "ok": False,
            "message": f"launcher missing: {LAUNCHER}",
        }

    proc = subprocess.run(
        ["bash", str(LAUNCHER)],
        cwd=str(ASJR_ROOT),
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )

    message = (proc.stdout or proc.stderr or "").strip()
    return {
        "started": "started" in message.lower(),
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "message": message,
    }
