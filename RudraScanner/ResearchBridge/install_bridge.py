#!/usr/bin/env python3
"""ONE-TIME admin-only installer invoked from fixed Discord SCommand.

No user-supplied arguments. Does not restart Chakra or the Discord bot.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys

ROOT=Path("/root/trading/ASJR")
SOURCE=ROOT/"RudraScanner/ResearchBridge/asjr-research-bridge.service"
TARGET=Path("/etc/systemd/system/asjr-research-bridge.service")

def run(argv):
    try:
        result=subprocess.run(argv, text=True, capture_output=True,
                              timeout=20, check=False)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

def main():
    if not SOURCE.is_file():
        print("BRIDGE INSTALL | FAILED | unit file missing")
        return 2
    if not (ROOT/"RudraScanner/research_bridge_worker.py").is_file():
        print("BRIDGE INSTALL | FAILED | worker missing")
        return 2
    # This command requires systemd administrative rights; don't escalate.
    if not run(["install", "-m", "0644", str(SOURCE), str(TARGET)]):
        print("BRIDGE INSTALL | FAILED | systemd file install denied")
        return 2
    if not run(["systemctl", "daemon-reload"]):
        print("BRIDGE INSTALL | FAILED | daemon-reload")
        return 2
    if not run(["systemctl", "enable", "--now", "asjr-research-bridge.service"]):
        print("BRIDGE INSTALL | FAILED | enable/start")
        return 2
    if not run(["systemctl", "is-active", "--quiet", "asjr-research-bridge.service"]):
        print("BRIDGE INSTALL | FAILED | not active")
        return 2
    print("BRIDGE INSTALL | SUCCESS | service active")
    print("BRIDGE | awaiting GitHub authorized research request")
    print("CHAKRA | UNCHANGED")
    return 0

if __name__=="__main__":
    sys.exit(main())
