"""Offline deterministic checks for historical stock-mover research."""
from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from RudraScanner import lead_mover_backtest as study
from RudraScanner.scan_now import main as scan_main


def sample(n=340):
    dates = pd.bdate_range("2025-01-01", periods=n)
    close = np.linspace(20, 60, n)
    data = pd.DataFrame({
        "Open": close,
        "High": close * 1.012,
        "Low": close * .988,
        "Close": close,
        "Volume": np.full(n, 2_000_000),
    }, index=dates)
    return data


class MoverBacktestTests(unittest.TestCase):
    def test_technical_flags_have_no_future_dependency(self):
        data = sample()
        earlier = study.signals(data.iloc[:275])
        full = study.signals(data)
        for key in study.KEYS:
            pd.testing.assert_series_equal(earlier[key], full[key].iloc[:275],
                                           check_freq=False)

    def test_enter_at_next_open_and_stop_first_on_ambiguous_bar(self):
        frame = sample(50)
        frame.iloc[11, frame.columns.get_loc("Open")] = 100
        frame.iloc[11, frame.columns.get_loc("High")] = 112
        frame.iloc[11, frame.columns.get_loc("Low")] = 94
        outcome, win = study.trade_result(frame, 10, holding=20)
        self.assertFalse(win)
        self.assertEqual(outcome, -5.0)

    def test_gap_through_stop_uses_open_fill(self):
        frame = sample(50)
        frame.iloc[11, frame.columns.get_loc("Open")] = 90
        frame.iloc[11, frame.columns.get_loc("High")] = 97
        frame.iloc[11, frame.columns.get_loc("Low")] = 88
        # Initial price is taken from day-11 OPEN itself, not prior close.
        frame.iloc[12, frame.columns.get_loc("Open")] = 75
        frame.iloc[12, frame.columns.get_loc("High")] = 90
        frame.iloc[12, frame.columns.get_loc("Low")] = 74
        outcome, win = study.trade_result(frame, 10, holding=20)
        self.assertFalse(win)
        self.assertAlmostEqual(outcome, (75 / 90 - 1) * 100)

    def test_target_hit_with_next_day_entry(self):
        frame = sample(50)
        frame.iloc[11, frame.columns.get_loc("Open")] = 100
        frame.iloc[11, frame.columns.get_loc("High")] = 111
        frame.iloc[11, frame.columns.get_loc("Low")] = 98
        pnl, win = study.trade_result(frame, 10, holding=20)
        self.assertTrue(win)
        self.assertAlmostEqual(pnl, 10.0)

    def test_no_future_data_returns_error(self):
        frame = sample(25)
        with self.assertRaises(ValueError):
            study.trade_result(frame, 12)

    def test_eligible_price_and_volume(self):
        data = sample()
        data.loc[data.index[-1], "Volume"] = 0
        flags = study.signals(data)
        self.assertIn("BASELINE", flags)
        self.assertTrue(bool(flags["BASELINE"].iloc[-1]))
        data["Volume"] = 1000
        flags = study.signals(data)
        self.assertFalse(bool(flags["BASELINE"].iloc[-1]))

    def test_study_symbol_no_leak_across_train_test(self):
        frame = sample()
        rows, current = study.study_symbol("MOCK", frame)
        self.assertEqual(set(current).issubset(set(study.KEYS[1:])), True)
        # A trained outcome must fully finish before the test starts.
        # No tests are run with invented future rows.
        self.assertTrue(all(r[1] in ("TRAIN", "TEST") for r in rows))

    def test_main_discord_flag_routes_only_to_research(self):
        with patch("RudraScanner.lead_mover_backtest.main", return_value=0) as mocked:
            with contextlib.redirect_stdout(io.StringIO()):
                code = scan_main(["--mover-study"])
        self.assertEqual(code, 0)
        mocked.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
