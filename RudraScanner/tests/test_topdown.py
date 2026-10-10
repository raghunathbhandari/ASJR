"""Top-down market and sector confirmation is fail-closed."""
import unittest

import pandas as pd
from RudraScanner.topdown import classify_topdown, ticker_etf_from_sources


def daily(spy, qqq, smh, *, day="2026-10-09"):
    return pd.DataFrame([
        {"ticker": "SPY", "date": day, "today_pct": spy},
        {"ticker": "QQQ", "date": day, "today_pct": qqq},
        {"ticker": "SMH", "date": day, "today_pct": smh},
    ])


class TopDownTests(unittest.TestCase):
    def test_long_confirmed_index_sector(self):
        bias, names, meta = classify_topdown(
            daily(1.0, 1.2, 1.8), trade_date="2026-10-09",
            ticker_etfs={"INTC": "SMH", "X": "XLK"})
        self.assertEqual(bias, "LONG")
        self.assertEqual(names["INTC"], "LONG")
        self.assertEqual(names["X"], "WAIT")

    def test_short_confirmed_weak_sector(self):
        bias, names, _ = classify_topdown(
            daily(-1, -1.4, -2), trade_date="2026-10-09",
            ticker_etfs={"INTC": "SMH"})
        self.assertEqual(bias, "SHORT")
        self.assertEqual(names["INTC"], "SHORT")

    def test_mixed_and_stale_fails_closed(self):
        for s in (daily(1, -1, 2), daily(1, 1, 2, day="2026-10-08")):
            bias, tickers, meta = classify_topdown(
                s, trade_date="2026-10-09", ticker_etfs={"INTC": "SMH"})
            self.assertEqual(bias, "WAIT")
            self.assertEqual(tickers["INTC"], "WAIT")

    def test_missing_nan_market_data_cannot_be_assumed_positive(self):
        bias, names, meta = classify_topdown(
            daily(float("nan"), float("nan"), -2),
            trade_date="2026-10-09", ticker_etfs={"INTC": "SMH"})
        self.assertEqual(bias, "WAIT")
        self.assertEqual(meta["reason"], "MISSING_FRESH_SPY_QQQ_PCT")

    def test_no_guess_on_ambiguous_sector_classification(self):
        result = ticker_etf_from_sources(
            [{"ticker": "INTC", "fixed_sector": "Semiconductors"},
             {"ticker": "MIX", "fixed_sector": "Energy / Software"},
             {"ticker": "PLTR", "fixed_sector": ""}],
            ai_rows=[{"ticker": "PLTR", "sector_etf": "XLK"}])
        self.assertEqual(result["INTC"], "SMH")
        self.assertEqual(result["PLTR"], "XLK")
        self.assertNotIn("MIX", result)


if __name__ == "__main__":
    unittest.main()
