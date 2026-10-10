"""Fake-Gateway tests for the opt-in 1H shared import, no real requests."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from RudraScanner.hourly import get_hourly_history, refresh_hourly_cache
from RudraScanner.bot_hook import run_bot_shadow


class FakeHourlyGateway:
    def __init__(self):
        self.nextReqId = 500
        self.data = {}
        self.hist_done = {}
        self.calls = []
        self.cancelled = []

    def reqHistoricalData(self, req, contract, end, duration,
                          bar_size, what, use_rth, fmt, keep, opts):
        self.calls.append((contract.symbol, duration, bar_size, use_rth))
        bars = []
        origin = pd.Timestamp("2026-09-15T13:30:00Z")
        for i in range(160):
            t = int((origin + pd.Timedelta(hours=i)).timestamp())
            bars.append([str(t), 100, 101, 99, 100, 1000])
        self.data[req] = bars
        self.hist_done[req] = True

    def cancelHistoricalData(self, req):
        self.cancelled.append(req)


class HourlyTests(unittest.TestCase):
    def test_hourly_uses_same_gateway_and_caps_thirty(self):
        app = FakeHourlyGateway()
        tickers = [f"T{i:02d}" for i in range(35)]
        data, status = get_hourly_history(app, tickers)
        self.assertEqual(len(status), 30)
        self.assertEqual(data["ticker"].nunique(), 30)
        self.assertTrue(all(bar == "1 hour" for _, _, bar, _ in app.calls))
        self.assertTrue(all(rth == 0 for _, _, _, rth in app.calls))
        self.assertEqual(len(data[data["ticker"] == "T00"]), 160)
        self.assertEqual(len(app.cancelled), 0)

    def test_hourly_cache_cannot_requery_when_fresh(self):
        app = FakeHourlyGateway()
        with tempfile.TemporaryDirectory() as root:
            now = pd.Timestamp("2026-10-09T18:00:00Z")
            one = refresh_hourly_cache(
                app, root, "2026-10-09", ["INTC", "WDC"], now=now)
            self.assertEqual(one["state"], "COMPLETE")
            self.assertEqual(one["usable_150bars"], ["INTC", "WDC"])
            self.assertTrue(Path(one["file"]).exists())
            original_count = len(app.calls)
            two = refresh_hourly_cache(
                app, root, "2026-10-09", ["WDC", "INTC"],
                now=now + pd.Timedelta(minutes=5))
            self.assertEqual(two["state"], "CACHE_FRESH")
            self.assertEqual(len(app.calls), original_count)

    def test_active_gate_rejects_partial_and_returns_only_verified_selected(self):
        from unittest.mock import patch

        class FakeApp:
            def historicalData(self, req, bar):
                return None
        fake = FakeApp()
        def chosen(states):
            return {
                "candidates": [{
                    "ticker": "INTC", "sources": ["FIXED"],
                    "selection_source": "FIXED"
                }],
                "ai": {"state": "PARTIAL"},
                "fixed": {"state": "OK"},
                "ibkr": {code: {"state": state} for code, state in zip(
                    ["TOP_PERC_GAIN", "TOP_PERC_LOSE",
                     "HOT_BY_VOLUME", "MOST_ACTIVE"], states)},
            }
        with patch("RudraScanner.bot_hook.save_discovery",
                   return_value=chosen(["SUCCESS", "EMPTY", "EMPTY", "EMPTY"])):
            good = run_bot_shadow(fake, "2026-10-09",
                                  repo_root="/tmp/testing", mode="active")
        self.assertEqual(good["state"], "ACTIVE_SELECTED")
        self.assertEqual([x["ticker"] for x in good["candidates"]], ["INTC"])

        with patch("RudraScanner.bot_hook.save_discovery",
                   return_value=chosen(["TIMEOUT", "EMPTY", "EMPTY", "EMPTY"])):
            blocked = run_bot_shadow(fake, "2026-10-09",
                                     repo_root="/tmp/testing", mode="active")
        self.assertEqual(blocked["state"], "PARTIAL")
        self.assertEqual(blocked["candidates"], [])


if __name__ == "__main__":
    unittest.main()
