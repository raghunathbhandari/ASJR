"""
One-time NQ open-source downloader launcher for the scheduled ASJR pipeline.
Safe to call repeatedly; shell state prevents duplicate downloads.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ASJR_ROOT = Path("/root/trading/ASJR")
LAUNCHER = ASJR_ROOT / "Backtesting" / "DataLoader" / "run_nq_download_tmux.sh"


def launch_nq_download_once() -> dict:
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
