#!/usr/bin/env python3
"""One-time root installer for fixed ASJR admin bridge service.

Run only after reviewing source, on a synchronized VPS checkout.
Does not stop/restart Chakra and does not modify trading data.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/root/trading/ASJR")
SERVICE = ROOT / "Rudra-DDB/AdminBridge/asjr-admin-bridge.service"
TARGET = Path("/etc/systemd/system/asjr-admin-bridge.service")
WORKER = ROOT / "Rudra-DDB/AdminBridge/admin_bridge_worker.py"
PYTHON = Path("/root/trading/venv_new/bin/python")

def run(*args):
    result = subprocess.run(args, text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError("Command failed: " + " ".join(args))
    return result.stdout.strip()

def main():
    if os.geteuid() != 0:
        raise RuntimeError("Installer needs root privileges")
    if not (SERVICE.is_file() and WORKER.is_file() and PYTHON.exists()):
        raise RuntimeError("Missing deployed bridge files/venv")
    if Path(run("git", "-C", str(ROOT), "rev-parse", "--show-toplevel")).resolve() != ROOT:
        raise RuntimeError("Unexpected working tree")
    # Installed service is a fixed source-controlled template, not a dynamic string.
    shutil.copyfile(SERVICE, TARGET)
    TARGET.chmod(0o644)
    run("systemctl", "daemon-reload")
    run("systemctl", "enable", "--now", TARGET.name)
    print("ADMIN BRIDGE | INSTALLED")
    print("SERVICE |",run("systemctl","is-active",TARGET.name))
    print("NOTE | Chakra was not restarted")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("INSTALL FAILED |",type(exc).__name__,str(exc))
        raise SystemExit(2)
