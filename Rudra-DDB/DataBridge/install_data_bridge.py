#!/usr/bin/env python3
"""Install/restart ONLY the isolated ASJR Data Bridge systemd service."""
import os
import shutil
import subprocess
from pathlib import Path

ROOT=Path("/root/trading/ASJR")
SRC=ROOT/"Rudra-DDB/DataBridge/asjr-data-bridge.service"
DST=Path("/etc/systemd/system/asjr-data-bridge.service")
WORKER=ROOT/"Rudra-DDB/DataBridge/data_bridge_worker.py"

def cmd(*args):
    r=subprocess.run(args, capture_output=True, text=True, timeout=30)
    if r.returncode: raise RuntimeError("failed: "+" ".join(args))
    return r.stdout.strip()

def main():
    if os.geteuid()!=0: raise RuntimeError("root required for systemd installation")
    if not SRC.is_file() or not WORKER.is_file(): raise RuntimeError("deploy source first")
    shutil.copyfile(SRC,DST)
    DST.chmod(0o644)
    cmd("systemctl","daemon-reload")
    cmd("systemctl","enable","--now",DST.name)
    print("DATA BRIDGE |",cmd("systemctl","is-active",DST.name))
    print("Chakra and Admin Bridge unchanged")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
