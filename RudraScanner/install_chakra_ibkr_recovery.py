"""Patch the external VPS Chakra IBKR initialization without copying secrets.

Usage: python RudraScanner/install_chakra_ibkr_recovery.py
Only modifies /root/trading/utils/trading_sudarsan_chakra.py after strict
anchors and syntax validation. Backs up before replacing.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime

TARGET = Path("/root/trading/utils/trading_sudarsan_chakra.py")
ENTRY_OLD = """def ibkr_trading_sudarsan_chakra(app):
    try:
        result = tp.run_asjr_manual_pipeline(
"""
ENTRY_NEW = """def ibkr_trading_sudarsan_chakra(app):
    try:
        # Never pass an absent or uninitialized IBKR app into ASJR scanners.
        if not _asjr_ibkr_client_ready(app):
            print("CHAKRA | IBKR client missing/not ready; recovering")
            app = connect_ib_gateway(app)
        if not _asjr_ibkr_client_ready(app):
            raise RuntimeError(
                "IBKR client unavailable/not initialized; Chakra round skipped"
            )
        result = tp.run_asjr_manual_pipeline(
"""
CONNECTION_START = "def connect_ib_gateway("
CONNECTION_END = "\ndef is_market_open():"
CONNECTION_NEW = '''def _asjr_ibkr_client_ready(app):
    """Require socket connection and a usable IBKR request ID."""
    if app is None:
        return False
    try:
        return bool(app.isConnected()) and isinstance(
            getattr(app, "nextReqId", None), int
        ) and app.nextReqId > 0
    except Exception:
        return False


def connect_ib_gateway(app, client_id=656, port=4002, timeout=10,
                       host="127.0.0.1", max_clientid_tries=5):
    """Reconnect or fail safely; never return a stale app."""
    if _asjr_ibkr_client_ready(app):
        chakra_message("[APP] Connected and ready; reuse")
        return app

    def port_open():
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            return False

    if not port_open():
        try:
            chakra_message("[IB] Gateway port unavailable; requesting start")
            ibc.start_ib_gateway()
        except Exception as exc:
            print("[IB START ERROR]", exc)

    deadline = time.monotonic() + timeout
    while not port_open() and time.monotonic() < deadline:
        time.sleep(1)
    if not port_open():
        chakra_message("[IB] Gateway port unavailable; skipping round")
        return None

    for offset in range(max_clientid_tries):
        candidate_id = client_id + offset
        try:
            print(f"[APP] Connecting with clientId={candidate_id} ...")
            new_app = IBH.connectIB(clientId=candidate_id, port=port)
            ready_deadline = time.monotonic() + timeout
            while new_app is not None and time.monotonic() < ready_deadline:
                if _asjr_ibkr_client_ready(new_app):
                    chakra_message(f"[APP] IBKR ready (clientId={candidate_id})")
                    return new_app
                try:
                    if not new_app.isConnected():
                        break
                except Exception:
                    break
                time.sleep(0.25)
            print(f"[APP] clientId={candidate_id} failed readiness check")
            if new_app is not None:
                try:
                    new_app.disconnect()
                except Exception:
                    pass
        except Exception as exc:
            print(f"[APP CONNECT ERROR] clientId={candidate_id}: {exc}")

    chakra_message("[APP] No ready IBKR connection; skipping round")
    return None


'''

def main():
    original = TARGET.read_text()
    if "_asjr_ibkr_client_ready" in original:
        print("CHAKRA IBKR | Already patched; no changes")
        return
    if original.count(ENTRY_OLD) != 1:
        raise RuntimeError("Expected live Chakra entry point not found; refusing")
    if original.count(CONNECTION_START) != 1 or original.count(CONNECTION_END) != 1:
        raise RuntimeError("Expected live connection function not found; refusing")
    updated = original.replace(ENTRY_OLD, ENTRY_NEW, 1)
    start = updated.index(CONNECTION_START)
    end = updated.index(CONNECTION_END, start)
    updated = updated[:start] + CONNECTION_NEW + updated[end:]
    ast.parse(updated, filename=str(TARGET))
    backup = TARGET.with_name(TARGET.name + ".pre_ibkr_fix_" +
                              datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(TARGET, backup)
    fd, tmp = tempfile.mkstemp(dir=str(TARGET.parent), prefix=".chakra_fix_")
    try:
        with os.fdopen(fd, "w") as writer:
            writer.write(updated)
        os.chmod(tmp, TARGET.stat().st_mode & 0o777)
        os.replace(tmp, TARGET)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print("CHAKRA IBKR | PATCHED | syntax PASSED")
    print("BACKUP |", backup)

if __name__ == "__main__":
    main()
