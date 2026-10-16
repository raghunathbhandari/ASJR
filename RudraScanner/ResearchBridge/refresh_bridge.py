#!/usr/bin/env python3
"""Restart only the already-installed ASJR research bridge systemd service."""
import subprocess
def main():
    name="asjr-research-bridge.service"
    try:
        check=subprocess.run(["systemctl","is-enabled","--quiet",name],timeout=8)
        if check.returncode:
            print("BRIDGE REFRESH | REFUSED | unit not enabled")
            return 2
        result=subprocess.run(["systemctl","restart",name],timeout=20,capture_output=True)
        if result.returncode:
            print("BRIDGE REFRESH | FAILED | restart denied")
            return 2
        active=subprocess.run(["systemctl","is-active","--quiet",name],timeout=8)
        print("BRIDGE REFRESH | "+("SUCCESS | research service active" if active.returncode==0 else "FAILED | inactive"))
        print("CHAKRA | UNCHANGED")
        return 0 if active.returncode==0 else 2
    except (OSError, subprocess.TimeoutExpired):
        print("BRIDGE REFRESH | FAILED | systemctl unavailable")
        return 2
if __name__=="__main__":
    raise SystemExit(main())
