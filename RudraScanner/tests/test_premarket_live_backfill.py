"""No-IBKR tests for new-ticker live baseline maintenance."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from RudraScanner.premarket_live_backfill import backfill_cycle, select_missing
from RudraScanner.premarket_rvol import durable_reference_path

DAYS = ["2026-10-05", "2026-10-06", "2026-10-07",
        "2026-10-08", "2026-10-09"]
DAY = "2026-10-12"


def history(ticker):
    return pd.DataFrame([
        {"ticker": ticker,
         "datetime": pd.Timestamp(
             f"{day} {minute//60:02d}:{minute%60:02d}",
             tz="America/New_York"),
         "volume": 100}
        for day in DAYS for minute in range(240, 570, 5)
    ])


class BackfillLiveTests(unittest.TestCase):
    def test_initial_baseline_and_no_duplicate(self):
        with tempfile.TemporaryDirectory() as root:
            fetched = []
            def fetch(symbol):
                fetched.append(symbol)
                return history(symbol)
            outcome = backfill_cycle(None, root, DAY,
                                     ["INTC", "ONDS", "INTC"],
                                     enabled=True, fetch_one=fetch)
            self.assertEqual(outcome["state"], "FINISHED")
            self.assertEqual(fetched, ["INTC"])
            ref = pd.read_csv(durable_reference_path(root))
            self.assertEqual(ref["ticker"].nunique(), 1)
            self.assertEqual(ref["session_date_et"].nunique(), 5)
            second = backfill_cycle(None, root, DAY, ["INTC"],
                                    enabled=True, fetch_one=fetch)
            self.assertEqual(second["state"], "UP_TO_DATE_OR_ATTEMPTED")
            self.assertEqual(fetched, ["INTC"])

    def test_disabled_has_no_broker_calls(self):
        with tempfile.TemporaryDirectory() as root:
            def forbidden(_):
                raise AssertionError("Must not connect")
            result = backfill_cycle(None, root, DAY,
                                    ["NVDA"], enabled=False,
                                    fetch_one=forbidden)
            self.assertEqual(result["state"], "DISABLED")

    def test_no_duplicate_or_explicitly_excluded_symbols(self):
        with tempfile.TemporaryDirectory() as root:
            selected, status = select_missing(root, DAY,
                                              ["ONDS", "BEAT", "INTC", "INTC",
                                               "NVDA", "AKAM"], limit=3)
            self.assertEqual(status["state"], "OK")
            self.assertEqual(selected, ["INTC", "NVDA", "AKAM"])


if __name__ == "__main__":
    unittest.main()
