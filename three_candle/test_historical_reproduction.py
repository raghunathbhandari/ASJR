"""Run with: ASJR_5M_DIR=/path/to/MarketData/5m python -m unittest discover -s three_candle -p 'test_historical_reproduction.py'"""
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from three_candle import (find_historical_signals, historical_target_touches,
                          load_historical_5m)


class HistoricalReproduction(unittest.TestCase):
    EXPECTED = {
        "AMAT": (5, 5, 4, 3),
        "GOOG": (8, 8, 7, 3),
        "INTC": (11, 11, 9, 8),
        "LRCX": (10, 10, 10, 10),
        "META": (12, 12, 12, 12),
        "MU": (7, 7, 7, 7),
        "NVDA": (9, 9, 9, 7),
        "PLTR": (11, 11, 11, 10),
        "SPY": (4, 4, 0, 0),
        "XOM": (6, 6, 6, 4),
    }

    def test_september_2026_archived_counts(self):
        directory = os.environ.get("ASJR_5M_DIR")
        if not directory:
            self.skipTest("Set ASJR_5M_DIR to archived rudra-data-results IBKR 5m directory")
        actual = {}
        for ticker in self.EXPECTED:
            data = load_historical_5m(
                str(Path(directory) / f"{ticker}_5m.csv"),
                "2026-09-01", "2026-09-30"
            )
            signals = list(find_historical_signals(data))
            actual[ticker] = (len(signals), *historical_target_touches(signals, data))
        self.assertEqual(actual, self.EXPECTED)
        self.assertEqual(tuple(map(sum, zip(*actual.values()))), (83, 83, 75, 64))


if __name__ == "__main__":
    unittest.main()
