"""New shared Reversal tickers seed only completed historic 1H bars."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from RudraScanner.reversal_bridge import seed_new_symbols
from ASJR_Analyst.Strategies.RudraReversal1H import rudra_reversal as rr


def sample(n):
    stamps = pd.date_range("2026-09-01T14:30:00Z", periods=n, freq="1h")
    return pd.DataFrame({"datetime": stamps,
                         "open": [100]*n, "high": [101]*n,
                         "low": [99]*n, "close": [100]*n})


class ReversalBridgeTests(unittest.TestCase):
    def test_first_seen_symbol_seeds_latest_and_never_historical_alert(self):
        with tempfile.TemporaryDirectory() as root:
            state_file = Path(root) / "reversal_state.json"
            with patch.object(rr, "_load_ticker_1h", return_value=sample(160)):
                one = seed_new_symbols("2026-10-09", ["INTC", "INTC"],
                                       state_file=state_file)
                two = seed_new_symbols("2026-10-09", ["INTC"],
                                       state_file=state_file)
            self.assertEqual(one["seeded"], ["INTC"])
            self.assertEqual(one["alerts_created"], 0)
            self.assertEqual(two["already_tracked"], ["INTC"])
            state = rr._load_state(state_file)
            self.assertIn("INTC", state["last_seen_bar"])
            self.assertEqual(state["pending"], [])

    def test_under_150_completed_bars_is_not_seeded(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "state.json"
            with patch.object(rr, "_load_ticker_1h", return_value=sample(140)):
                status = seed_new_symbols("2026-10-09", ["WDC"],
                                          state_file=path)
            self.assertEqual(status["not_ready_150h"], ["WDC"])
            self.assertEqual(status["seeded"], [])
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
