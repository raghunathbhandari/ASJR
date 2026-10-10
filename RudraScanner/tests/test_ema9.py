"""Offline tests for continuous EMA9; use python -m unittest discover.

These tests do not connect to IBKR, send Discord or modify live data.
"""

import math
import unittest

import pandas as pd

from RudraScanner.ema9 import build_continuous_ema9


def make_row(ticker, when, close, *, volume=1000):
    return {
        "Ticker": ticker,
        "Date": when,
        "Open": close,
        "High": close,
        "Low": close,
        "Close": close,
        "Volume": volume,
    }


class ContinuousEMA9Tests(unittest.TestCase):
    def test_carries_previous_day_ema_into_premarket_and_rth(self):
        # Nine Friday RTH 5m candles all close at $100.
        rows = [
            make_row("INTC", f"2026-10-09 {hour:02d}:{minute:02d}:00-04:00", 100)
            for hour, minute in (
                (15, 15), (15, 20), (15, 25), (15, 30), (15, 35),
                (15, 40), (15, 45), (15, 50), (15, 55)
            )
        ]
        # The EMA continues across the weekend: 100 -> 102 -> 105.6.
        rows += [
            make_row("INTC", "2026-10-12 04:00:00-04:00", 110),
            make_row("INTC", "2026-10-12 09:30:00-04:00", 120),
        ]
        features, state = build_continuous_ema9(
            pd.DataFrame(rows), now=pd.Timestamp("2026-10-12T14:00:00Z")
        )
        self.assertEqual(len(features), 11)
        self.assertEqual(state["state"], "OK")
        self.assertEqual(state["tickers"], 1)
        self.assertTrue(bool(features.iloc[8]["ema9_ready"]))
        self.assertEqual(features.iloc[9]["session"], "PREMARKET")
        self.assertEqual(features.iloc[10]["session"], "RTH")
        self.assertTrue(math.isclose(features.iloc[9]["ema9"], 102.0))
        self.assertTrue(math.isclose(features.iloc[10]["ema9"], 105.6))
        self.assertGreater(features.iloc[9]["prior_gap_minutes"], 5)
        self.assertFalse(state["session_reset"])

    def test_no_synthetic_bars_and_no_cross_ticker_contamination(self):
        rows = [
            make_row("INTC", "2026-10-09 15:55:00-04:00", 100),
            make_row("WDC", "2026-10-09 15:55:00-04:00", 300),
            make_row("INTC", "2026-10-12 04:00:00-04:00", 110),
            make_row("WDC", "2026-10-12 04:00:00-04:00", 310),
        ]
        features, status = build_continuous_ema9(
            pd.DataFrame(rows[::-1]), now=pd.Timestamp("2026-10-12T10:00:00Z")
        )
        self.assertEqual(len(features), 4)
        self.assertEqual(status["tickers"], 2)
        self.assertFalse(features["ema9_ready"].any())
        ints = features.loc[features["ticker"] == "INTC"]
        wdc = features.loc[features["ticker"] == "WDC"]
        self.assertAlmostEqual(float(ints.iloc[-1]["ema9"]), 102)
        self.assertAlmostEqual(float(wdc.iloc[-1]["ema9"]), 302)

    def test_unfinished_and_invalid_rows_are_diagnosed_not_used(self):
        rows = [
            make_row("INTC", "2026-10-12 09:50:00-04:00", 100),
            make_row("INTC", "2026-10-12 09:50:00-04:00", 101),  # duplicate
            make_row("INTC", "2026-10-12 09:55:00-04:00", 102, volume=-1),
            make_row("INTC", "2026-10-12 10:00:00-04:00", 105),  # still forming
        ]
        features, status = build_continuous_ema9(
            pd.DataFrame(rows), now=pd.Timestamp("2026-10-12T14:02:00Z")
        )
        self.assertEqual(len(features), 1)
        self.assertEqual(status["duplicate_rows"], 1)
        self.assertEqual(status["invalid_rows"], 1)
        self.assertEqual(status["unfinished_rows"], 1)
        self.assertEqual(status["state"], "PARTIAL")
        self.assertAlmostEqual(float(features.iloc[0]["close"]), 101)

    def test_timezone_naive_bar_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            build_continuous_ema9(
                pd.DataFrame([make_row("INTC", "2026-10-12 09:30:00", 100)]),
                now=pd.Timestamp("2026-10-12T14:00:00Z"),
            )

    def test_empty_data_returns_missing_status(self):
        features, status = build_continuous_ema9(pd.DataFrame())
        self.assertTrue(features.empty)
        self.assertEqual(status["state"], "MISSING")


if __name__ == "__main__":
    unittest.main()
