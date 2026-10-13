"""Offline tests for strict Rudra-Premarket RVOL baseline."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from RudraScanner.premarket_rvol import (
    ET, SEGMENTS, calculate, candidates, normalize_bars, update_history,
    reference_path,
)


def session_bars(ticker, day, segment="RTH", volume=100, upto=None):
    first, end = SEGMENTS[segment]
    minutes = range(first, end if upto is None else min(upto, end), 5)
    rows = []
    for minute in minutes:
        stamp = pd.Timestamp(
            "%s %02d:%02d" % (day, minute // 60, minute % 60),
            tz=ET,
        ).tz_convert(timezone.utc)
        rows.append({"ticker": ticker, "datetime": stamp, "volume": volume})
    return rows


class TestPremarketRVOL(unittest.TestCase):
    def test_five_only_same_minute_cumulative(self):
        prior = []
        for n in range(20):
            day = (datetime(2026, 9, 1) + timedelta(days=n)).date().isoformat()
            prior.extend(session_bars("INTC", day, volume=100))
        current = session_bars("INTC", "2026-10-12", volume=40, upto=590)
        with tempfile.TemporaryDirectory() as root:
            out, state = update_history(
                pd.DataFrame(prior + current), root, "2026-10-12", save=True)
            self.assertTrue(state["saved"])
            self.assertTrue(reference_path(root, "2026-10-12").is_file())
            last = out.sort_values("minute").iloc[-1]
            self.assertAlmostEqual(last.rvol5, .4)
            self.assertTrue(last.rvol5_ready)

    def test_no_partial_or_future_lookahead(self):
        baseline = []
        for n in range(20):
            day = (datetime(2026, 9, 1) + timedelta(days=n)).date().isoformat()
            baseline.extend(session_bars("AKAM", day, volume=100))
        # Entirely missing 5m bars must invalidate that historical day.
        baseline = [x for x in baseline
                    if not (str(x["datetime"].tz_convert(ET).date()) == "2026-09-03"
                            and x["datetime"].tz_convert(ET).hour == 10)]
        baseline.extend(session_bars("AKAM", "2026-10-13", volume=1))
        current = session_bars("AKAM", "2026-10-12", volume=40, upto=590)
        with tempfile.TemporaryDirectory() as root:
            out, _ = update_history(pd.DataFrame(baseline + current),
                                    root, "2026-10-12")
            last = out.iloc[-1]
            self.assertTrue(last.rvol5_ready)

    def test_session_isolation_and_early_rth_exclusion(self):
        reference = []
        for n in range(20):
            d = (datetime(2026, 9, 1) + timedelta(days=n)).date().isoformat()
            for segment in ("PRE", "RTH", "POST"):
                reference.extend(session_bars("INTC", d, segment, volume=100))
        raw = pd.DataFrame(
            reference
            + session_bars("INTC", "2026-10-12", "PRE", volume=50)
            + session_bars("INTC", "2026-10-12", "RTH", volume=50)
            + session_bars("INTC", "2026-10-12", "POST", volume=50))
        with tempfile.TemporaryDirectory() as root:
            x, _ = update_history(raw, root, "2026-10-12")
        self.assertEqual(set(x["session"].unique()), {"PRE", "RTH", "POST"})
        for col in ("rvol5",):
            self.assertTrue(x[col].dropna().between(.4999, .5001).all())
        x["close"] = 101
        x["ema9"] = 100
        x["vwap"] = 99
        watch = candidates(x)
        self.assertFalse(watch["minute"].between(570, 599).any())
        self.assertTrue(watch["minute"].eq(600).any())
        self.assertTrue(watch["session"].eq("PRE").any())
        self.assertTrue(watch["session"].eq("POST").any())

    def test_v2_both_rvol_bands_and_all_tickers(self):
        # Any DataLake ticker may qualify, not just the original three.
        frame = pd.DataFrame([
            {"ticker": name, "close": 101, "ema9": 100, "vwap": 99,
             "rvol5": rv, "rvol5_ready": True, "minute": 620, "session": "RTH"}
            for name, rv in [
                ("MSFT", 2.50), ("WTTR", 0.58), ("INTC", 0.59),
                ("WDC", 2.49), ("AKAM", 0.40), ("GOOG", 3.0)]
        ])
        output = candidates(frame)
        self.assertEqual(set(output["ticker"]), {"MSFT", "WTTR", "AKAM", "GOOG"})
        self.assertEqual(dict(zip(output["ticker"], output["rvol5_signal"])),
                         {"MSFT": "HIGH_RVOL", "WTTR": "LOW_RVOL",
                          "AKAM": "LOW_RVOL", "GOOG": "HIGH_RVOL"})
        # Every alert requires both bullish price conditions.
        frame.loc[frame.ticker == "MSFT", "ema9"] = 102
        frame.loc[frame.ticker == "WTTR", "vwap"] = 102
        frame.loc[frame.ticker == "GOOG", "minute"] = 575
        frame.loc[frame.ticker == "AKAM", "rvol5_ready"] = False
        self.assertTrue(candidates(frame).empty)

    def test_gap_in_current_session_is_not_approved(self):
        baseline = []
        for n in range(20):
            d = (datetime(2026, 9, 1) + timedelta(days=n)).date().isoformat()
            baseline.extend(session_bars("INTC", d, volume=100))
        current = session_bars("INTC", "2026-10-12", volume=40, upto=600)
        current = [r for r in current if r["datetime"].tz_convert(ET).minute != 40]
        with tempfile.TemporaryDirectory() as root:
            out, _ = update_history(pd.DataFrame(baseline + current),
                                    root, "2026-10-12")
        self.assertFalse(out.iloc[-1].rvol5_ready)

    def test_utc_time_conversion_and_partial_history(self):
        bars = pd.DataFrame(session_bars("INTC", "2026-10-12", "RTH", 100, 580))
        normalized = normalize_bars(bars)
        self.assertEqual(normalized["minute"].tolist(), [570, 575])
        out = calculate(bars, pd.DataFrame(), trading_day="2026-10-12")
        self.assertFalse(out["rvol5_ready"].any())


if __name__ == "__main__":
    unittest.main()
