"""Smoke tests for the frozen original strategy; not an archived 10-ticker replay."""
import unittest
import pandas as pd
from original_three_candle import is_original_pattern, historical_signals, summarize, resample_rth_15m


class OriginalThreeCandleTests(unittest.TestCase):
    def example(self):
        times = pd.date_range("2026-09-01 09:30", periods=4, freq="15min",
                              tz="America/New_York").tz_convert("Europe/London")
        bars = pd.DataFrame([
            [100.0,100.5,99.8,100.1,10],
            [100.0,100.3,99.5,100.2,12],
            [100.2,100.5,100.0,100.4,20],
            [100.4,100.9,100.35,100.7,15],
        ], index=times, columns=["Open","High","Low","Close","Volume"])
        return bars

    def test_bullish_sweep_and_1r_2r_3r(self):
        bars = self.example()
        self.assertTrue(is_original_pattern(*[bars.iloc[i] for i in (0,1,2)]))
        signals = historical_signals(bars, "TEST")
        self.assertEqual(len(signals), 1)
        self.assertEqual(tuple(signals.loc[0,[f"hit_{k}R" for k in (1,2,3)]]),
                         (1,1,1))
        total = summarize(signals).iloc[-1]
        self.assertEqual(total["setups"], 1)

    def test_no_sweep_means_no_signal(self):
        bars = self.example()
        bars.iloc[1,2] = 99.85
        self.assertFalse(is_original_pattern(*[bars.iloc[i] for i in (0,1,2)]))
        self.assertTrue(historical_signals(bars, "TEST").empty)

    def test_missing_5m_bar_is_not_fabricated(self):
        time = pd.date_range("2026-09-01 09:30", periods=6, freq="5min",
                             tz="America/New_York").tz_convert("UTC")
        bars = pd.DataFrame([[100,101,99,100.5,10]]*6, index=time,
                            columns=["Open","High","Low","Close","Volume"])
        bars = bars.drop(bars.index[1])
        r = resample_rth_15m(bars, "2026-09-01","2026-09-01")
        self.assertEqual(len(r),1)
        self.assertEqual(r.index[0].tz_convert("America/New_York").hour,9)
        self.assertEqual(r.index[0].tz_convert("America/New_York").minute,45)


if __name__ == "__main__":
    unittest.main()
