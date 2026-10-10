"""Offline shared-universe tests; no live IBKR or strategy changes."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from RudraScanner.universe import (
    common_tickers, load_shared_universe, merge_shared_universe,
    read_fixed_watchlist,
)
from RudraScanner.storage import save_discovery
from RudraScanner.tests.test_discovery import FakeApp, FakeSub, FakeTag, NOW


def fixed_file(root, day, rows):
    path = (Path(root) / "ASJR_Analyst" / "DataLake" / day /
            "config" / "fixed_watchlist.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh,
            fieldnames=("ticker", "exchange", "sector", "enabled", "notes"))
        writer.writeheader()
        writer.writerows(rows)
    return path


class CommonUniverseTests(unittest.TestCase):
    def test_fixed_only_ticker_kept_for_both_strategies(self):
        with tempfile.TemporaryDirectory() as root:
            fixed_file(root, "2026-10-09", [
                {"ticker": "MSFT", "sector": "XLK", "enabled": "1"},
                {"ticker": "INTC", "sector": "SOXX", "enabled": "yes"},
                {"ticker": "ONDS", "sector": "Drones", "enabled": "1"},
                {"ticker": "AMD", "enabled": "false"},
            ])
            ai = [{"ticker": "INTC", "bias": "WATCH", "freshness": "UNVERIFIED"},
                  {"ticker": "AKAM", "bias": "LONG", "freshness": "FRESH"}]
            ibkr = [{"ticker": "INTC", "scan_code": "MOST_ACTIVE"},
                    {"ticker": "WDC", "scan_code": "TOP_PERC_GAIN"},
                    {"ticker": "WDC", "scan_code": "HOT_BY_VOLUME"}]
            results, status = load_shared_universe(root, "2026-10-09", ai, ibkr)
            self.assertEqual(common_tickers(results),
                             ["AKAM", "INTC", "MSFT", "WDC"])
            self.assertEqual(status["state"], "PARTIAL")
            self.assertEqual(status["excluded"], ["ONDS"])
            self.assertEqual(status["disabled"], 1)
            by_ticker = {item["ticker"]: item for item in results}
            self.assertEqual(by_ticker["INTC"]["sources"], ["FIXED", "AI", "IBKR"])
            self.assertEqual(by_ticker["WDC"]["scan_codes"],
                             ["TOP_PERC_GAIN", "HOT_BY_VOLUME"])
            self.assertEqual(by_ticker["MSFT"]["sources"], ["FIXED"])
            self.assertEqual(by_ticker["INTC"]["fixed_sector"], "SOXX")

    def test_missing_daily_fixed_list_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as root:
            merged, status = load_shared_universe(
                root, "2026-10-09",
                [{"ticker": "INTC", "bias": "WATCH"}], [])
            self.assertEqual(status["state"], "MISSING")
            self.assertEqual(common_tickers(merged), ["INTC"])

    def test_duplicate_or_invalid_fixed_rows_reported(self):
        with tempfile.TemporaryDirectory() as root:
            fixed_file(root, "2026-10-09", [
                {"ticker": "msft", "enabled": "1"},
                {"ticker": "MSFT", "enabled": "1"},
                {"ticker": "BAD TICKER", "enabled": "1"},
            ])
            rows, status = read_fixed_watchlist(root, "2026-10-09")
            self.assertEqual([r["ticker"] for r in rows], ["MSFT"])
            self.assertEqual(status["state"], "PARTIAL")
            self.assertEqual(len(status["warnings"]), 2)

    def test_saved_output_includes_fixed_provenance(self):
        import sys
        import types
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as root:
            fixed_file(root, "2026-10-09", [
                {"ticker": "MSFT", "enabled": "1"},
                {"ticker": "ONDS", "enabled": "1"},
            ])
            ai_path = (Path(root) / "ASJR_Analyst" /
                       "config" / "ai_scanner_list.csv")
            ai_path.parent.mkdir(parents=True, exist_ok=True)
            ai_path.write_text(
                "ticker,sector_etf,bias,catalyst,source_url,published_at_utc,"
                "researched_at_utc,expires_at_utc,quality_status,priority,"
                "enabled,reason\n"
                "INTC,,WATCH,,,,,,UNVERIFIED,1,true,permanent monitor\n",
                encoding="utf-8",
            )
            app = FakeApp({code: ["WDC", "INTC"] for code in (
                "TOP_PERC_GAIN", "TOP_PERC_LOSE",
                "HOT_BY_VOLUME", "MOST_ACTIVE"
            )})
            scanner_mod = types.ModuleType("ibapi.scanner")
            scanner_mod.ScannerSubscription = FakeSub
            tag_mod = types.ModuleType("ibapi.tag_value")
            tag_mod.TagValue = FakeTag
            with patch.dict(sys.modules, {
                "ibapi": types.ModuleType("ibapi"),
                "ibapi.scanner": scanner_mod,
                "ibapi.tag_value": tag_mod,
            }):
                result = save_discovery(
                    app, "2026-10-09", repo_root=root, now=NOW
                )
            tickers = common_tickers(result["candidates"])
            self.assertEqual(tickers, ["INTC", "MSFT", "WDC"])
            daily = Path(root) / "ASJR_Analyst" / "DataLake" / "2026-10-09"
            status = json.loads((daily / "raw" /
                                 "scanner_status.json").read_text())
            self.assertEqual(status["fixed"]["excluded"], ["ONDS"])
            csv_output = (daily / "processed" /
                          "scalp_radar_candidates.csv").read_text()
            self.assertIn("FIXED", csv_output)
            self.assertIn("MSFT", csv_output)
            self.assertNotIn("ONDS", csv_output)


if __name__ == "__main__":
    unittest.main()
