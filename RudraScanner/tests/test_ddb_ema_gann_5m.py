"""Offline pure signal tests. No IBKR, Yahoo, Discord, or orders."""
import unittest
import pandas as pd

from RudraScanner.ddb_ema_gann_5m import gann_levels, signal_on_closed_bars, config


class DDBEMAGannTests(unittest.TestCase):
    def sample(self):
        end = pd.Timestamp("2026-11-12T21:00:00Z")
        ix = pd.date_range(end=end - pd.Timedelta(minutes=5), periods=40, freq="5min", tz="UTC")
        close = [100.0] * 39 + [102.0]
        low = [100.0] * 39 + [101.5]
        opens = close.copy()
        opens[-1] = 101.2  # whole candle BODY above EMA9; not only the close
        low[-1] = 99.8  # wick below EMA9 is allowed: we test the body
        df = pd.DataFrame({"Open": opens, "High": [c + 0.5 for c in close],
                           "Low": low, "Close": close}, index=ix)
        return df, end

    def test_exact_asjr_gann_main_mid(self):
        levels = gann_levels(553.6, 500.0, 590.0)
        self.assertEqual(levels, [
            (541.0, "MID"), (553.0, "MID"), (565.0, "MID"),
            (577.0, "MAIN"), (589.0, "MID")
        ])

    def test_closed_bar_first_qualification(self):
        bars, now = self.sample()
        result = signal_on_closed_bars(bars, "AMD", "A", now=now)
        self.assertIsNotNone(result)
        self.assertEqual(result["ticker"], "AMD")
        self.assertGreater(min(result["open"], result["close"]), result["ema9"])
        self.assertLess(result["low"], result["ema9"])
        self.assertGreater(result["ema9"], result["ema20"])

    def test_close_only_above_ema9_is_rejected(self):
        bars, now = self.sample()
        bars.loc[bars.index[-1], "Open"] = 99.0
        self.assertIsNone(signal_on_closed_bars(bars, "AMD", "A", now=now))

    def test_partial_last_candle_never_alerts(self):
        bars, now = self.sample()
        self.assertIsNone(signal_on_closed_bars(bars, "AMD", "A",
                          now=now - pd.Timedelta(minutes=3)))

    def test_stale_last_candle_never_alerts(self):
        bars, now = self.sample()
        self.assertIsNone(signal_on_closed_bars(bars, "AMD", "A",
                          now=now + pd.Timedelta(minutes=25)))

    def test_universe_has_49_unique(self):
        settings, items = config()
        self.assertEqual(len(items), 49)
        self.assertEqual([sum(group == g for _, group in items)
                          for g in "ABC"], [22, 17, 10])


if __name__ == "__main__":
    unittest.main()
