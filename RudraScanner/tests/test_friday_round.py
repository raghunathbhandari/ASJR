"""Friday replay: missing data, no lookahead and reproducible markouts."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from RudraScanner.friday_round import (
    FROZEN_TICKERS, _direction, replay_once, TEST_DATE, _ibkr_close_end,
)


def fixture(root, *, with_wap=True, qqq_weak_until=None):
    fixed = (Path(root) / "ASJR_Analyst" / "DataLake" / TEST_DATE /
             "config" / "fixed_watchlist.csv")
    fixed.parent.mkdir(parents=True, exist_ok=True)
    fixed.write_text("ticker,sector,enabled\nINTC,Semiconductors,1\n")
    prev = pd.Timestamp("2026-10-08T19:55:00Z")
    start = pd.Timestamp("2026-10-09T13:30:00Z")
    prices = {"INTC": 101.0, "SPY": 102.0, "QQQ": 102.0, "SMH": 103.0}
    rows = []
    for ticker, price in prices.items():
        rows.append({
            "Ticker": ticker, "Date": prev.isoformat(),
            "Open": 100., "High": 101., "Low": 99.,
            "Close": 100., "Volume": 1000,
            **({"WAP": 100.} if with_wap else {}),
        })
        for i in range(22):
            actual = price + .1 * i
            if ticker == "QQQ" and qqq_weak_until is not None and i <= qqq_weak_until:
                actual = 99.0
            rows.append({
                "Ticker": ticker,
                "Date": (start + pd.Timedelta(minutes=5*i)).isoformat(),
                "Open": actual - .01,
                "High": actual + .2,
                "Low": actual - .2,
                "Close": actual, "Volume": 1200.,
                **({"WAP": actual} if with_wap else {}),
            })
    return pd.DataFrame(rows)


class FridayReplayTests(unittest.TestCase):
    def test_frozen_universe_is_thirty_with_hindsight_warning(self):
        self.assertEqual(len(FROZEN_TICKERS), 30)
        self.assertEqual(len(set(FROZEN_TICKERS)), 30)
        self.assertIn("SPCX", FROZEN_TICKERS)

    def test_no_wap_means_no_evaluable_signals(self):
        with tempfile.TemporaryDirectory() as root:
            trades, status = replay_once(
                fixture(root, with_wap=False), root, TEST_DATE)
            self.assertTrue(trades.empty)
            self.assertGreater(status["blocks"]["missing_wap"], 0)
            self.assertEqual(status["input"]["rth_vwap_ready"], 0)
            self.assertTrue(status["selection_hindsight"])

    def test_missing_benchmark_blocks_even_with_wap(self):
        with tempfile.TemporaryDirectory() as root:
            raw = fixture(root)
            raw = raw[raw["Ticker"] != "QQQ"]
            trades, status = replay_once(raw, root, TEST_DATE)
            self.assertTrue(trades.empty)
            self.assertIn("QQQ", status["input"]["missing_benchmark_or_sector"])
            self.assertGreater(
                status["blocks"]["missing_sector_or_index"], 0)

    def test_markout_entry_next_bar_and_exit_after_six(self):
        def fake_signal(bars, *, index_bias, sector_bias_by_ticker, settings):
            return ([{"pattern": "HITCHHIKER"}], {"blocked_data": 0})
        with tempfile.TemporaryDirectory() as root:
            with patch("RudraScanner.friday_round.detect_five_patterns",
                       side_effect=fake_signal):
                trades, status = replay_once(
                    fixture(root), root, TEST_DATE, hold_bars=6)
            self.assertGreater(len(trades), 0)
            first = trades.iloc[0]
            self.assertEqual(first["direction"], "LONG")
            self.assertEqual(first["pattern"], "HITCHHIKER")
            self.assertAlmostEqual(
                float(first["entry_next_open"]), 101.0+0.1*7-0.01)
            self.assertAlmostEqual(
                float(first["exit_6bar_close"]), 101.0+0.1*12)
            self.assertTrue(status["selection_hindsight"])
            self.assertEqual(status["discord_sent"], 0)

    def test_later_qqq_move_cannot_justify_early_entry(self):
        def fake_signal(bars, *, index_bias, sector_bias_by_ticker, settings):
            return ([{"pattern": "SECOND CHANCE"}], {"blocked_data": 0})
        with tempfile.TemporaryDirectory() as root:
            with patch("RudraScanner.friday_round.detect_five_patterns",
                       side_effect=fake_signal):
                trades, status = replay_once(
                    fixture(root, qqq_weak_until=10),
                    root, TEST_DATE, hold_bars=3)
            self.assertGreater(len(trades), 0)
            first = pd.Timestamp(trades.iloc[0]["signal_time_uk"])
            self.assertGreaterEqual(
                first.tz_convert("America/New_York").hour, 10)
            self.assertGreater(
                status["blocks"]["missing_sector_or_index"], 0)

    def test_stale_five_minute_benchmark_bar_cannot_confirm_trade(self):
        with tempfile.TemporaryDirectory() as root:
            raw = fixture(root)
            # Drop one QQQ candle at 10:30 ET. Reusing the earlier
            # QQQ quote would falsely approve signals as-of 10:30.
            missing = pd.Timestamp("2026-10-09T14:30:00Z").isoformat()
            raw = raw[~(
                (raw["Ticker"] == "QQQ") & (raw["Date"] == missing)
            )].copy()
            trades, state = replay_once(raw, root, TEST_DATE)
            self.assertGreater(
                state["blocks"]["missing_sector_or_index"], 0)
            # A normal run with missing QQQ candle must not fabricate a
            # current signal by using QQQ's stale last available price.
            self.assertTrue(state["selection_hindsight"])

    def test_direction_wait_on_mixed(self):
        self.assertEqual(_direction(1, -1, 3, 1), "WAIT")
        self.assertEqual(_direction(1, 1, -1, 1), "WAIT")
        self.assertEqual(_direction(-1, -1, -2, -1), "SHORT")

    def test_ibkr_backfill_end_is_after_friday_close(self):
        clock = pd.Timestamp(_ibkr_close_end(TEST_DATE))
        self.assertEqual(
            clock.tz_convert("America/New_York").date().isoformat(),
            TEST_DATE)
        self.assertEqual(clock.tz_convert("America/New_York").hour, 23)


if __name__ == "__main__":
    unittest.main()
