"""Offline 15-minute DDB tests: three complete IBKR 5-minute candles per bar."""
import unittest
import pandas as pd

from RudraScanner.ddb_ema_gann_5m import (
    gann_levels, signal_on_closed_bars, build_complete_15m_bars, config
)


class DDBEMAGannTests(unittest.TestCase):
    def sample(self):
        # 40 complete 15m bars, each formed from 3 real 5m bars.
        end = pd.Timestamp("2026-11-12T21:00:00Z")
        ix = pd.date_range(end=end - pd.Timedelta(minutes=5), periods=120,
                           freq="5min", tz="UTC")
        close = [100.0] * 120
        opens = close.copy()
        highs = [100.5] * 120
        lows = [99.5] * 120

        # The last 15m body is entirely above EMA9, despite a wick below.
        opens[-3] = 101.2
        close[-3] = 101.3
        highs[-3] = 101.5
        lows[-3] = 99.8
        opens[-2] = 101.3
        close[-2] = 101.6
        highs[-2] = 101.8
        lows[-2] = 101.0
        opens[-1] = 101.6
        close[-1] = 102.0
        highs[-1] = 102.3
        lows[-1] = 101.4
        frame = pd.DataFrame({"Open": opens, "High": highs, "Low": lows,
                              "Close": close}, index=ix)
        return frame, end

    def test_exact_asjr_gann_main_mid(self):
        self.assertEqual(gann_levels(553.6, 500.0, 590.0), [
            (541.0, "MID"), (553.0, "MID"), (565.0, "MID"),
            (577.0, "MAIN"), (589.0, "MID")
        ])

    def test_aggregation_uses_three_5m_bars(self):
        bars, now = self.sample()
        fifteen = build_complete_15m_bars(bars, now=now)
        self.assertEqual(len(fifteen), 40)
        self.assertEqual(fifteen.index[-1], pd.Timestamp("2026-11-12T20:45:00Z"))
        self.assertEqual(fifteen["Open"].iloc[-1], 101.2)
        self.assertEqual(fifteen["Close"].iloc[-1], 102.0)
        self.assertEqual(fifteen["Low"].iloc[-1], 99.8)

    def test_closed_15m_full_body(self):
        bars, now = self.sample()
        result = signal_on_closed_bars(bars, "AMD", "A", now=now)
        self.assertIsNotNone(result)
        self.assertEqual(result["timeframe"], "15min")
        self.assertEqual(result["bar_uk"], "2026-11-12 20:45")
        self.assertGreater(min(result["open"], result["close"]), result["ema9"])
        self.assertLess(result["low"], result["ema9"])
        self.assertGreater(result["ema9"], result["ema20"])

    def test_close_only_above_ema9_is_rejected(self):
        bars, now = self.sample()
        bars.loc[bars.index[-3], "Open"] = 99.0
        self.assertIsNone(signal_on_closed_bars(bars, "AMD", "A", now=now))

    def test_partial_15m_candle_never_alerts(self):
        bars, now = self.sample()
        self.assertIsNone(signal_on_closed_bars(
            bars, "AMD", "A", now=now - pd.Timedelta(minutes=5)))

    def test_missing_middle_5m_bar_rejected(self):
        bars, now = self.sample()
        bars = bars.drop(bars.index[-2])
        fifteen = build_complete_15m_bars(bars, now=now)
        self.assertEqual(len(fifteen), 39)
        self.assertIsNone(signal_on_closed_bars(bars, "AMD", "A", now=now))

    def test_stale_15m_candle_never_alerts(self):
        bars, now = self.sample()
        self.assertIsNone(signal_on_closed_bars(
            bars, "AMD", "A", now=now + pd.Timedelta(minutes=31)))

    def test_universe_has_49_unique(self):
        settings, items = config()
        self.assertEqual(settings["timeframe"], "15m")
        self.assertEqual(len(items), 49)
        self.assertEqual([sum(group == g for _, group in items)
                          for g in "ABC"], [22, 17, 10])


if __name__ == "__main__":
    unittest.main()
