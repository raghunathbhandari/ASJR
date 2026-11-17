#!/usr/bin/env python3
"""Read-only IBKR scanner-parameter diagnostic; no scans or market data."""
from __future__ import annotations
import re
import threading
from xml.etree import ElementTree as ET

TERMS = ("EMA9", "EMA20", "RSI", "ADX")
TIME_TERMS = ("TIMEFRAME", "TIME_FRAME", "BAR SIZE", "BARSIZE", "INTERVAL")


def summarize_parameters(xml: str) -> str:
    root = ET.fromstring(xml)
    records, seen = [], set()
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1].lower()
        if tag not in {"abstractfield", "rangefilter", "filter"}:
            continue
        fields = {}
        for child in element.iter():
            if child is element or len(child):
                continue
            value = (child.text or "").strip()
            if value:
                fields[child.tag.rsplit("}", 1)[-1].lower()] = value
        description = " | ".join(f"{key}={val}" for key, val in fields.items())
        if (description and
                any(term.lower() in description.lower() for term in TERMS + TIME_TERMS)
                and description not in seen):
            records.append(description[:240])
            seen.add(description)

    all_text = " ".join((el.text or "").strip() for el in root.iter())
    lines = [f"IBKR SCANNER PARAMETERS | XML RECEIVED | {len(xml)} bytes"]
    for term in TERMS:
        found = bool(re.search(re.escape(term), all_text, re.IGNORECASE))
        lines.append(f"{term} | {'CATALOGUE MATCH' if found else 'NOT FOUND IN XML'}")
    selectors = [term for term in TIME_TERMS if term.lower() in all_text.lower()]
    lines.append("TIMEFRAME-LIKE TERMS | " + (", ".join(selectors) if selectors else "NONE FOUND"))
    lines.append("EXACT 15M EMA20 SERVER-SIDE FILTER | UNVERIFIED")
    lines.append("MATCHING FIELD DEFINITIONS (capped at 24):")
    lines.extend("- " + rec for rec in records[:24])
    if not records:
        count = 0
        for m in re.finditer(r"ema(?:9|20)|rsi|adx|timeframe|barsize|interval", xml, re.I):
            sample = re.sub(r"\s+", " ", xml[max(0, m.start()-65):m.end()+100])
            lines.append("- CONTEXT " + sample[:180])
            count += 1
            if count >= 12:
                break
    lines.append("READ ONLY | NO MARKET DATA | NO ORDERS | NO SCHEDULE")
    return "\n".join(lines) + "\n"


def run_parameter_check(*, host="127.0.0.1", port=4002, client_id=686, timeout=12):
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper

    class Client(EWrapper, EClient):
        def __init__(self):
            EClient.__init__(self, self)
            self.ready = threading.Event()
            self.received = threading.Event()
            self.payload = None
            self.errors = []

        def nextValidId(self, orderId):
            self.ready.set()

        def scannerParameters(self, xml):
            self.payload = str(xml)
            self.received.set()

        def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
            if errorCode not in (2104, 2106, 2107, 2108, 2158):
                self.errors.append((errorCode, str(errorString)[:100]))

    client = Client()
    try:
        client.connect(host, port, client_id)
        threading.Thread(target=client.run, daemon=True).start()
        if not client.ready.wait(timeout=min(timeout, 7)):
            return "IBKR PARAMETERS | GATEWAY NOT READY | " + str(client.errors[:3]) + "\n"
        client.reqScannerParameters()
        if not client.received.wait(timeout):
            return "IBKR PARAMETERS | NO XML RECEIVED | " + str(client.errors[:3]) + "\n"
        try:
            return summarize_parameters(client.payload)
        except ET.ParseError as exc:
            return "IBKR PARAMETERS | XML PARSE ERROR | " + str(exc) + "\n"
    except (OSError, RuntimeError, ValueError) as exc:
        return "IBKR PARAMETERS | ERROR | " + type(exc).__name__ + ": " + str(exc)[:100] + "\n"
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    print(run_parameter_check(), end="")
