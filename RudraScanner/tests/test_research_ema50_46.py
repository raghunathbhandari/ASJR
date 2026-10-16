"""Offline checks for the isolated 46-symbol Yahoo research collector.

No IBKR/TWS connection, no Yahoo HTTP request, no Git operations.
"""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from RudraScanner import research_ema50_46 as research


def daily(n=120):
    days = pd.bdate_range(end="2026-10-14", periods=n, tz="America/New_York")
    closes = [20 + i * 0.1 for i in range(n)]
    return pd.DataFrame({
        "Open": closes, "High": [c + 1 for c in closes],
        "Low": [c - 1 for c in closes], "Close": closes,
        "Volume": [2_000_000] * n,
    }, index=days)


def intraday():
    days = pd.bdate_range(end="2026-10-14", periods=25)
    times = [pd.Timestamp(d).tz_localize("America/New_York").replace(hour=h, minute=m)
             for d in days for h, m in ((9, 30), (9, 35))]
    return pd.DataFrame({
        "Open": [100.0] * len(times), "High": [101.0] * len(times),
        "Low": [99.0] * len(times), "Close": [100.5] * len(times),
        "Volume": [1000] * len(times),
    }, index=pd.DatetimeIndex(times))


class Research46Tests(unittest.TestCase):
    def test_exact_ibkr_list_and_batch_count(self):
        self.assertEqual(len(research.NAMES), 46)
        self.assertEqual(len(set(research.NAMES)), 46)
        self.assertIn("VEEV", research.NAMES)
        self.assertIn("HIGH_LAST_VS_EMA50", research.SOURCE)
        self.assertEqual(research.BATCHES, 5)

    def test_daily_history_features_have_return_and_nonfabricated_volume(self):
        x = research._daily_features(daily())
        self.assertEqual(x["daily_status"], "OK")
        self.assertGreater(x["return_20d_pct"], 0)
        self.assertEqual(x["daily_rvol5_prev_days"], 1.0)
        self.assertEqual(x["daily_rvol20_prev_days"], 1.0)
        self.assertGreater(x["ema20_slope5_pct"], 0)
        self.assertFalse(x["volume_contraction_daily"])

    def test_same_slot_5_and_20_day_rvol_are_distinct_from_bar_rvol(self):
        x = research._intraday_features(intraday())
        self.assertEqual(x["five_minute_status"], "OK")
        self.assertEqual(x["rvol5bar"], 1.0)
        self.assertEqual(x["rvol20bar"], 1.0)
        self.assertEqual(x["rvol5day_same_slot"], 1.0)
        self.assertEqual(x["rvol20day_same_slot"], 1.0)

    def test_invalid_ohlc_is_discarded(self):
        frame = daily(90)
        frame.iloc[-1, frame.columns.get_loc("High")] = 10
        clean = research._frame(frame, "VEEV")
        self.assertEqual(len(clean), 89)

    def test_missing_batches_refuse_finalize(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(research, "OUT", Path(folder)):
                with contextlib.redirect_stdout(io.StringIO()):
                    result = research.finalize()
        self.assertEqual(result, 2)

    def test_discord_router_fixed_batch_only(self):
        from RudraScanner.scan_now import main
        with patch("RudraScanner.research_ema50_46.main", return_value=0) as mocked:
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["--research-46-batch", "3"])
        self.assertEqual(result, 0)
        mocked.assert_called_once_with(["--batch", "3"])

    def test_discord_finalize_routes(self):
        from RudraScanner.scan_now import main
        with patch("RudraScanner.research_ema50_46.main", return_value=0) as mocked:
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["--research-46-finalize"])
        self.assertEqual(result, 0)
        mocked.assert_called_once_with(["--finalize"])


if __name__ == "__main__":
    unittest.main()
