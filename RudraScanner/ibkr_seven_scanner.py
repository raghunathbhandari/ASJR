#!/usr/bin/env python3
"""Read-only, on-demand IBKR discovery using seven selected US stock scan codes.

Explicit invocation only. Does not run Chakra, import historical bars, place
orders, or modify any of the scheduled bot's scanner subscriptions.
IBKR advertises up to 10 concurrent API scanner subscriptions, so requests
are batched 3 at a time to leave room for Chakra's existing four scans.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CODES = (
    "TOP_PERC_GAIN",
    "TOP_PERC_LOSE",
    "HOT_BY_VOLUME",
    "MOST_ACTIVE",
    "HIGH_VS_13W_HL",
    "HIGH_VS_52W_HL",
    "HIGH_LAST_VS_EMA50",
)
EXCLUDED = {"BEAT", "ONDS"}
ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "RudraScanner" / "state" / "ibkr_seven_latest.json"
UK = ZoneInfo("Europe/London")
ET = ZoneInfo("America/New_York")
ERROR_END_CODES = {162, 200, 321, 354, 10167, 10168}


def _valid_symbol(value):
    name = str(value).upper().strip()
    return name if re.fullmatch(r"[A-Z][A-Z0-9.-]{0,7}", name) and name not in EXCLUDED else None


def _save_snapshot(rows, statuses):
    # Save the full 50 results per successful scan as an on-demand discovery
    # snapshot; do not touch ASJR DataLake or its tracked import files.
    completed = {code: [s for _, s in rows[code]]
                 for code in CODES if statuses.get(code) == "DONE"}
    if not any(completed.values()):
        return False
    unique = list(dict.fromkeys(sym for code in CODES for sym in completed.get(code, [])))
    payload = {
        "schema": 1,
        "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "session_date_et": datetime.now(ET).date().isoformat(),
        "source": "IBKR direct 7-code stock scanner, on-demand",
        "codes": {code: {"status": statuses.get(code, "UNKNOWN"),
                         "tickers": completed.get(code, [])} for code in CODES},
        "tickers": unique,
    }
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".ibkr_seven_", suffix=".tmp",
                                 dir=str(CACHE_PATH.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as writer:
            json.dump(payload, writer, indent=2)
            writer.write("\n")
        os.replace(temp, CACHE_PATH)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return True


def load_saved_tickers(*, max_age_seconds=86400, date=None):
    """Return fresh, correctly dated on-demand IBKR tickers, or [] (fail closed)."""
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        seen = datetime.fromisoformat(data["as_of_utc"])
        age = (datetime.now(timezone.utc) - seen).total_seconds()
        expected = date or datetime.now(ET).date().isoformat()
        if seen.tzinfo is None or not 0 <= age <= max_age_seconds:
            return []
        if data.get("session_date_et") != expected:
            return []
        return list(dict.fromkeys(s for x in data.get("tickers", [])
                                  if (s := _valid_symbol(x)) is not None))
    except (OSError, ValueError, KeyError, TypeError):
        return []


def run_ibkr_seven(*, host="127.0.0.1", port=4002, client_id=684,
                   per_code=50, timeout_per_batch=8, preview=5,
                   codes=None):
    # Restrict any single-scan requests to the fixed, reviewed scanner codes.
    selected = tuple(CODES if codes is None else codes)
    if not selected or len(set(selected)) != len(selected) or any(
        code not in CODES for code in selected
    ):
        return "IBKR SCANNER | DENIED | invalid scanner selection\n"
    single = len(selected) == 1
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.scanner import ScannerSubscription

    class Reader(EWrapper, EClient):
        def __init__(self):
            EClient.__init__(self, self)
            self.connected = threading.Event()
            self.parameters_ready = threading.Event()
            self.parameters_xml = ""
            self.request_to_code = {}
            self.done = {code: threading.Event() for code in selected}
            self.rows = {code: [] for code in selected}
            self.errors = []

        def nextValidId(self, orderId):
            self.connected.set()

        def scannerParameters(self, xml):
            self.parameters_xml = str(xml)
            self.parameters_ready.set()

        def scannerData(self, reqId, rank, contractDetails, distance,
                        benchmark, projection, legsStr):
            code = self.request_to_code.get(reqId)
            if code:
                sym = _valid_symbol(contractDetails.contract.symbol)
                if sym is not None:
                    self.rows[code].append((int(rank) + 1, sym))

        def scannerDataEnd(self, reqId):
            code = self.request_to_code.get(reqId)
            if code:
                self.done[code].set()

        def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
            if errorCode in (2104, 2106, 2158, 2107, 2108):
                return
            code = self.request_to_code.get(reqId)
            message = str(errorString).replace("\n", " ")[:120]
            self.errors.append((code or reqId, errorCode, message))
            if code and errorCode in ERROR_END_CODES:
                self.done[code].set()

    app = Reader()
    try:
        app.connect(host, port, client_id)
        worker = threading.Thread(target=app.run, daemon=True)
        worker.start()
        if not app.connected.wait(7):
            return "IBKR SCANNER | GATEWAY NOT READY\n" + str(app.errors[:3])

        lines = ["IBKR SCANNER | %s | %s UK | ON-DEMAND" %
                 ("SINGLE " + selected[0] if single else "SEVEN CODES",
                  datetime.now(UK).strftime("%Y-%m-%d %H:%M"))]
        try:
            app.reqScannerParameters()
            params_received = app.parameters_ready.wait(3)
        except Exception:
            params_received = False
        xml = app.parameters_xml.upper() if params_received else ""
        lines.append("CODE PARAMETERS | %s" %
                     ("RECEIVED" if params_received else "NOT RETURNED; testing subscriptions"))
        # The parameter XML advertises more scans than are necessarily
        # executable via the API. Attempt subscriptions even when advertised.
        statuses = {}
        for start in range(0, len(selected), 3):
            batch = selected[start:start + 3]
            requested = []
            for i, code in enumerate(batch):
                if params_received and code not in xml:
                    statuses[code] = "NOT ADVERTISED"
                    continue
                req = 963000 + start + i
                app.request_to_code[req] = code
                sub = ScannerSubscription()
                sub.instrument = "STK"
                sub.locationCode = "STK.US.MAJOR"
                sub.scanCode = code
                sub.numberOfRows = min(50, max(1, int(per_code)))
                sub.stockTypeFilter = "CORP"
                sub.abovePrice = 10.0
                try:
                    app.reqScannerSubscription(req, sub, [], [])
                    requested.append((req, code))
                except Exception as exc:
                    statuses[code] = "SEND ERROR"
                    app.errors.append((code, "SEND", type(exc).__name__))
                    app.done[code].set()
            deadline = time.monotonic() + timeout_per_batch
            for _, code in requested:
                app.done[code].wait(max(0, deadline - time.monotonic()))
            for req, code in requested:
                errors = [e for e in app.errors if e[0] == code and e[1] in ERROR_END_CODES]
                statuses[code] = ("API ERROR" if errors else
                                  "DONE" if app.done[code].is_set() else "TIMEOUT")
                try:
                    app.cancelScannerSubscription(req)
                except Exception:
                    pass

        ordered = {}
        for code in selected:
            ordered[code] = sorted(set(app.rows[code]), key=lambda item: item[0])
            shortlist = [sym for _, sym in ordered[code]][:preview]
            lines.append("%s | %s | %d | %s" %
                         (code, statuses.get(code, "UNKNOWN"), len(ordered[code]),
                          ", ".join(shortlist) if shortlist else "-"))
        seen = list(dict.fromkeys(sym for code in selected
                                  if statuses.get(code) == "DONE"
                                  for _, sym in ordered[code]))
        lines.append("UNIQUE DISCOVERED | %d" % len(seen))
        if single:
            # Do not replace the complete seven-code snapshot with a partial
            # universe: this direct code-specific call is output-only.
            lines.append("SNAPSHOT | UNCHANGED | single scanner, no cache writes")
        else:
            saved = False
            try:
                saved = _save_snapshot(ordered, statuses)
            except OSError as exc:
                lines.append("CACHE ERROR | %s" % type(exc).__name__)
            lines.append("SNAPSHOT | %s | full results from completed scans" %
                         ("SAVED" if saved else "NOT SAVED"))
        if app.errors:
            lines.append("API ERRORS | " + " ; ".join(
                "%s:%s %s" % (c, err, msg[:50])
                for c, err, msg in app.errors[:4]))
        lines.append("READ-ONLY | NO CHAKRA RUN | NO ORDERS")
        if single:
            lines.append("RESULT | %s" %
                         ("SUCCESS" if statuses.get(selected[0]) == "DONE" and seen
                          else "NOT READY"))
        if seen:
            if single:
                lines.append("WATCHLIST | %s | %s" %
                             (selected[0], ", ".join(seen[:50])))
            else:
                lines.append("WATCHLIST | IBKR FIRST 30 | " + ", ".join(seen[:30]))
        return "\n".join(lines) + "\n"
    except (OSError, ValueError, RuntimeError) as exc:
        return "IBKR SCANNER | CONNECTION/SCANNER ERROR | %s: %s" % (
            type(exc).__name__, str(exc)[:160])
    finally:
        try:
            app.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    print(run_ibkr_seven(), end="")
