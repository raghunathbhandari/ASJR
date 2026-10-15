"""Offline seven-code IBKR scanner checks; no real IBKR connection or orders."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from RudraScanner import ibkr_seven_scanner as scanner


class FakeClient:
    """IBKR API adapter that replies synchronously in-memory only."""

    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.requests = []
        self.cancelled = []
        self.disconnected = False

    def connect(self, host, port, client_id):
        self.wrapper.nextValidId(1)

    def run(self):
        return None

    def reqScannerParameters(self):
        codes = getattr(self.wrapper, "_advertised_codes", scanner.CODES)
        self.wrapper.scannerParameters(
            "<ScannerParameters>" +
            "".join(f"<ScanCode>{code}</ScanCode>" for code in codes) +
            "</ScannerParameters>"
        )

    def reqScannerSubscription(self, request_id, subscription, options, filters):
        self.requests.append((request_id, subscription.scanCode))
        # Fake 50 ordered rows; contract.symbol is the only accessed field.
        for rank in range(50):
            contract = SimpleNamespace(contract=SimpleNamespace(symbol=f"T{rank:02d}"))
            self.wrapper.scannerData(
                request_id, rank, contract, "", "", "", ""
            )
        self.wrapper.scannerDataEnd(request_id)

    def cancelScannerSubscription(self, request_id):
        self.cancelled.append(request_id)

    def disconnect(self):
        self.disconnected = True


class FakeWrapper:
    pass


class FakeSubscription:
    pass


def fake_ibapi_modules():
    api = types.ModuleType("ibapi")
    api.__path__ = []
    client = types.ModuleType("ibapi.client")
    client.EClient = FakeClient
    wrapper = types.ModuleType("ibapi.wrapper")
    wrapper.EWrapper = FakeWrapper
    subscription = types.ModuleType("ibapi.scanner")
    subscription.ScannerSubscription = FakeSubscription
    return {
        "ibapi": api,
        "ibapi.client": client,
        "ibapi.wrapper": wrapper,
        "ibapi.scanner": subscription,
    }


class SevenCodeOfflineTests(unittest.TestCase):
    def test_exactly_seven_unique_approved_codes(self):
        self.assertEqual(len(scanner.CODES), 7)
        self.assertEqual(len(set(scanner.CODES)), 7)
        self.assertIn("HIGH_LAST_VS_EMA50", scanner.CODES)
        self.assertIn("HIGH_VS_13W_HL", scanner.CODES)
        self.assertIn("HIGH_VS_52W_HL", scanner.CODES)

    def test_each_code_independently_returns_50_with_no_cache_write(self):
        with patch.dict(sys.modules, fake_ibapi_modules()):
            with patch.object(scanner, "_save_snapshot",
                              side_effect=AssertionError("single-code scan changed cache")):
                for code in scanner.CODES:
                    with self.subTest(code=code):
                        result = scanner.run_ibkr_seven(codes=(code,), preview=50)
                        self.assertIn(f"{code} | DONE | 50", result)
                        self.assertIn("RESULT | SUCCESS", result)
                        self.assertIn(f"WATCHLIST | {code} |", result)
                        self.assertIn("T49", result)
                        self.assertIn("SNAPSHOT | UNCHANGED", result)

    def test_all_seven_save_full_ranked_universe(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ibkr_seven_latest.json"
            with patch.dict(sys.modules, fake_ibapi_modules()):
                with patch.object(scanner, "CACHE_PATH", output):
                    result = scanner.run_ibkr_seven()
            self.assertIn("SNAPSHOT | SAVED", result)
            self.assertTrue(output.is_file())
            data = json.loads(output.read_text())
            self.assertEqual(set(data["codes"]), set(scanner.CODES))
            self.assertTrue(all(data["codes"][code]["status"] == "DONE"
                                for code in scanner.CODES))
            self.assertTrue(all(len(data["codes"][code]["tickers"]) == 50
                                for code in scanner.CODES))
            self.assertEqual(len(data["tickers"]), 50)

    def test_unapproved_code_rejected_before_import_or_api(self):
        with patch.dict(sys.modules, {"ibapi": None}):
            output = scanner.run_ibkr_seven(codes=("UNSAFE_UNKNOWN_SCAN",))
        self.assertIn("DENIED", output)

    def test_discord_lists_approved_codes_offline(self):
        from RudraScanner.scan_now import main
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--ibkr-codes"])
        self.assertEqual(code, 0)
        for value in scanner.CODES:
            self.assertIn(value, stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
