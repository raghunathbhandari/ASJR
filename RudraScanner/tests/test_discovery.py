"""Offline RudraScanner phase-1 tests; no Gateway, Discord or VPS required."""

import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from RudraScanner.discovery import (
    AI_FIELDS, SCANNER_CODES, merge_candidates, read_ai_csv, run_ibkr_scans
)
from RudraScanner.storage import read_saved_report, save_discovery


NOW = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)


class FakeSub:
    pass


class FakeTag:
    def __init__(self, name, value):
        self.tag, self.value = name, value


class FakeApp:
    def __init__(self, responses=None):
        self.nextReqId = 101
        self.scanner_results = {}
        self.scanner_done = {}
        self.responses = responses or {}
        self.calls = []
        self.cancellations = []

    def reqScannerSubscription(self, req, subscription, _, filters):
        self.calls.append((subscription.scanCode, filters))
        symbols = self.responses.get(subscription.scanCode, [])
        if symbols == "ERROR":
            raise RuntimeError("simulated scanner connection loss")
        if symbols == "TIMEOUT":
            self.scanner_results[req] = ["DELL"]
            return
        self.scanner_results[req] = symbols
        self.scanner_done[req] = True

    def cancelScannerSubscription(self, req):
        self.cancellations.append(req)


def make_ai(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=AI_FIELDS)
        writer.writeheader()
        writer.writerows(entries)


class DiscoveryTests(unittest.TestCase):
    def test_missing_ai_file_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows, status = read_ai_csv(Path(tmp) / "none.csv", now=NOW)
            self.assertEqual(rows, [])
            self.assertEqual(status["state"], "MISSING")

    def test_ai_expiration_exclusions_and_unverified_watch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ai.csv"
            make_ai(path, [
                {"ticker": "intc", "bias": "WATCH", "enabled": "true",
                 "quality_status": "UNVERIFIED"},
                {"ticker": "AMD", "bias": "LONG", "enabled": "true",
                 "researched_at_utc": "2026-10-09T10:00:00Z",
                 "expires_at_utc": "2026-10-09T20:00:00Z"},
                {"ticker": "BEAT", "bias": "WATCH", "enabled": "true"},
                {"ticker": "INTC", "bias": "LONG", "enabled": "true"},
            ])
            rows, status = read_ai_csv(path, now=NOW)
            self.assertEqual([r["ticker"] for r in rows], ["INTC"])
            self.assertEqual(rows[0]["freshness"], "UNVERIFIED")
            self.assertEqual(status["expired"], 1)
            self.assertEqual(status["state"], "PARTIAL")

    def test_ibkr_codes_filters_rank_and_partial_failure(self):
        app = FakeApp({
            "TOP_PERC_GAIN": ["INTC", "WDC", "INTC", "BEAT"],
            "TOP_PERC_LOSE": ["AKAM", "INTC"],
            "HOT_BY_VOLUME": "TIMEOUT",
            "MOST_ACTIVE": "ERROR",
        })
        rows, status = run_ibkr_scans(
            app, scanner_cls=FakeSub, tag_cls=FakeTag, timeout=0.001, now=NOW
        )
        self.assertEqual([x["ticker"] for x in rows if x["scan_code"] == "TOP_PERC_GAIN"],
                         ["INTC", "WDC"])
        self.assertEqual(status["HOT_BY_VOLUME"]["state"], "TIMEOUT")
        self.assertEqual(status["MOST_ACTIVE"]["state"], "ERROR")
        self.assertEqual(len(app.cancellations), 3)  # ERROR before start
        self.assertEqual(tuple(code for code, _ in app.calls), SCANNER_CODES)
        self.assertEqual({item.tag for item in app.calls[0][1]},
                         {"marketCapAbove1e6", "usdPriceAbove", "avgVolumeAbove"})
        self.assertFalse(any(item.tag.startswith("changePerc") for item in app.calls[0][1]))

    def test_merge_provenance(self):
        merged = merge_candidates(
            [{"ticker": "INTC", "bias": "WATCH", "freshness": "UNVERIFIED"}],
            [{"ticker": "INTC", "scan_code": "MOST_ACTIVE"},
             {"ticker": "WDC", "scan_code": "TOP_PERC_GAIN"},
             {"ticker": "INTC", "scan_code": "HOT_BY_VOLUME"},
             {"ticker": "ONDS", "scan_code": "MOST_ACTIVE"}]
        )
        self.assertEqual([x["ticker"] for x in merged], ["INTC", "WDC"])
        self.assertEqual(merged[0]["sources"], ["AI", "IBKR"])
        self.assertEqual(merged[0]["scan_codes"], ["MOST_ACTIVE", "HOT_BY_VOLUME"])

    def test_save_paths_are_common_datalake_not_second_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai = root / "ASJR_Analyst" / "config" / "ai_scanner_list.csv"
            make_ai(ai, [{"ticker": "INTC", "bias": "WATCH", "enabled": "true"}])
            app = FakeApp({code: ["WDC"] for code in SCANNER_CODES})
            # storage uses the default ibapi classes, which need not be installed
            import sys
            import types
            from unittest.mock import patch
            scanner_mod = types.ModuleType("ibapi.scanner")
            scanner_mod.ScannerSubscription = FakeSub
            tag_mod = types.ModuleType("ibapi.tag_value")
            tag_mod.TagValue = FakeTag
            with patch.dict(sys.modules, {"ibapi": types.ModuleType("ibapi"),
                                          "ibapi.scanner": scanner_mod,
                                          "ibapi.tag_value": tag_mod}):
                result = save_discovery(app, "2026-10-09", repo_root=root, now=NOW)
            base = root / "ASJR_Analyst" / "DataLake" / "2026-10-09"
            self.assertTrue((base / "raw" / "scanner_status.json").is_file())
            self.assertTrue((base / "raw" / "ai_scanner_list.csv").is_file())
            self.assertTrue((base / "processed" / "scalp_radar_candidates.csv").is_file())
            self.assertEqual(len(result["candidates"]), 2)
            self.assertIn("DATA NOT READY", read_saved_report(root, "2026-10-09"))


if __name__ == "__main__":
    unittest.main()
