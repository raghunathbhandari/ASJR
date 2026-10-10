"""20 full-session cumulative RVOL survives daily DataLake rollover."""
import tempfile
import unittest
import warnings
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from RudraScanner.volume_history import apply_rolling_rvol20


def previous_days(today, amount):
    dates = []
    d = date.fromisoformat(today) - timedelta(days=1)
    while len(dates) < amount:
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d -= timedelta(days=1)
    return sorted(dates)


def artificial_sessions(days, *, partial_date=None, volume=100):
    rows = []
    for day in days:
        minute_values = range(0, 390, 5) if day != partial_date else range(0, 60, 5)
        for minute in minute_values:
            rows.append({
                "ticker": "INTC", "session_date_et": day,
                "session": "RTH", "minutes_into_rth": minute,
                "volume": volume if day != partial_date else 2*volume,
            })
    return pd.DataFrame(rows)


class RollingHistoryTests(unittest.TestCase):
    def test_exact_twenty_full_prior_sessions_required(self):
        with tempfile.TemporaryDirectory() as repo:
            days = previous_days("2026-10-09", 20)
            day = "2026-10-09"
            frames = artificial_sessions(days + [day], partial_date=day)
            updated, state = apply_rolling_rvol20(
                frames, repo, day, save=True)
            current = updated[updated["session_date_et"] == day]
            self.assertEqual(state["state"], "AVAILABLE")
            self.assertEqual(current["prior_complete_sessions"].min(), 20)
            self.assertTrue(current["rvol20_ready"].all())
            self.assertAlmostEqual(float(current.iloc[-1]["rvol20"]), 2.0)
            self.assertTrue(Path(state["output"]).exists())

    def test_rollover_reuses_common_datalake_reference_no_second_root(self):
        with tempfile.TemporaryDirectory() as repo:
            earlier = previous_days("2026-10-09", 20)
            first = artificial_sessions(earlier + ["2026-10-09"])
            _, a = apply_rolling_rvol20(first, repo, "2026-10-09", save=True)
            monday = artificial_sessions(["2026-10-12"], partial_date="2026-10-12")
            result, status = apply_rolling_rvol20(
                monday, repo, "2026-10-12", save=True)
            self.assertEqual(status["state"], "AVAILABLE")
            self.assertIn("DataLake/2026-10-09",
                          status["reference_file"])
            self.assertTrue(result["rvol20_ready"].all())
            self.assertTrue(Path(status["output"]).is_file())
            self.assertIn("DataLake/2026-10-12", status["output"])

    def test_empty_prior_source_does_not_emit_futurewarning(self):
        with tempfile.TemporaryDirectory() as repo:
            # Regression check for pandas changing concat behaviour.
            short = artificial_sessions(["2026-10-09"],
                                        partial_date="2026-10-09")
            with warnings.catch_warnings():
                warnings.simplefilter("error", FutureWarning)
                data, state = apply_rolling_rvol20(
                    short, repo, "2026-10-09")
            self.assertFalse(data["rvol20_ready"].any())
            self.assertEqual(state["stored_rows"], 0)

    def test_insufficient_sessions_remain_unavailable(self):
        with tempfile.TemporaryDirectory() as repo:
            days = previous_days("2026-10-09", 18)
            source = artificial_sessions(days + ["2026-10-09"],
                                         partial_date="2026-10-09")
            frame, result = apply_rolling_rvol20(source, repo, "2026-10-09")
            self.assertEqual(result["state"],
                             "INSUFFICIENT_20_FULL_RTH_SESSIONS")
            self.assertFalse(frame["rvol20_ready"].any())
            self.assertFalse(Path(repo, "ASJR_Analyst", "DataLake",
                                  "2026-10-09").exists())


if __name__ == "__main__":
    unittest.main()
