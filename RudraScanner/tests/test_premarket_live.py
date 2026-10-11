"""Offline end-to-end signal & acknowledgement tests; zero IBKR requests."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from RudraScanner.premarket_live import evaluate, prepare, acknowledge
from RudraScanner.premarket_rvol import (
    normalize_bars, _complete_profiles, _clean_reference,
    durable_reference_path,
)

ET = "America/New_York"
PRIOR = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"]
DAY = "2026-10-12"


def bar(ticker, day, minute, volume=100, close=100):
    timestamp = pd.Timestamp(f"{day} {minute // 60:02}:{minute % 60:02}", tz=ET)
    return {
        "ticker": ticker, "datetime": timestamp,
        "open": 100, "high": max(101, close + 1),
        "low": 99, "close": close,
        "volume": volume, "wap": 99.5,
    }


def fixture():
    old = []
    for day in PRIOR:
        old.extend(bar("INTC", day, minute) for minute in range(240, 570, 5))
    today = [bar("INTC", DAY, minute, volume=40,
                 close=(105 if minute == 255 else 100))
             for minute in range(240, 260, 5)]
    return old, today


class PremarketLiveTests(unittest.TestCase):
    def test_real_wap_and_five_day_baseline(self):
        old, today = fixture()
        with tempfile.TemporaryDirectory() as root:
            reference = _complete_profiles(
                normalize_bars(pd.DataFrame(old)), before_day=DAY)
            reference = _clean_reference(reference, DAY)
            dest = durable_reference_path(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            reference.to_csv(dest, index=False)
            stamp = pd.Timestamp(f"{DAY} 04:20:30", tz=ET)
            events, status = evaluate(pd.DataFrame(old + today), root, DAY, now=stamp)
            self.assertEqual(status["state"], "MATCHES", status)
            self.assertEqual([x["ticker"] for x in events], ["INTC"])
            self.assertAlmostEqual(events[0]["rv5"], .4, places=2)
            message = prepare(events, root)
            self.assertIn("INTC", message)
            self.assertIn("RV5 0.40x", message)
            acknowledge(events, root)
            self.assertEqual(prepare(events, root), "")

    def test_missing_actual_wap_never_signals(self):
        old, today = fixture()
        today[-1]["wap"] = float("nan")
        with tempfile.TemporaryDirectory() as root:
            reference = _clean_reference(
                _complete_profiles(normalize_bars(pd.DataFrame(old)), before_day=DAY),
                DAY,
            )
            dest = durable_reference_path(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            reference.to_csv(dest, index=False)
            stamp = pd.Timestamp(f"{DAY} 04:20:30", tz=ET)
            events, _ = evaluate(pd.DataFrame(old + today), root, DAY, now=stamp)
            self.assertEqual(events, [])

    def test_stale_latest_bar_never_alerts(self):
        old, today = fixture()
        with tempfile.TemporaryDirectory() as root:
            reference = _clean_reference(
                _complete_profiles(normalize_bars(pd.DataFrame(old)), before_day=DAY),
                DAY,
            )
            dest = durable_reference_path(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            reference.to_csv(dest, index=False)
            stamp = pd.Timestamp(f"{DAY} 05:30", tz=ET)
            events, _ = evaluate(pd.DataFrame(old + today), root, DAY, now=stamp)
            self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
