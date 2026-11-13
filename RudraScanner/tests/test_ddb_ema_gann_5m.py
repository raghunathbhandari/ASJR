"""Offline DDB V2 regression tests: genuine bullish 15m EMA crossover only."""
import unittest
import pandas as pd

from RudraScanner.ddb_ema_gann_5m import (
    gann_levels, signal_on_closed_bars, build_complete_15m_bars, config,
)


class DDBEMAGannV2Tests(unittest.TestCase):
    def sample(self, *, volume_ratio=2.0, benchmark_up=True):
        """3 RTH days, previous 15m EMA cross, final 15m confirmation."""
        stamps = (
            pd.date_range("2026-11-10 14:30", periods=26, freq="15min", tz="UTC")
            .append(pd.date_range(
                "2026-11-11 14:30", periods=26, freq="15min", tz="UTC"))
            .append(pd.date_range(
                "2026-11-12 14:30", periods=22, freq="15min", tz="UTC"))
        )
        prices = [100.0] * 55 + [95.0] * 12 + [
            95.0 + i * 0.7 for i in range(7)]
        self.assertEqual(len(prices), 74)
        benchmark_prices = [
            100.0 + (i * (0.1 if benchmark_up else -0.1))
            for i in range(74)
        ]

        def make_5m(values, volume_at_end):
            records = []
            for i, (stamp, close) in enumerate(zip(stamps, values)):
                for offset in (0, 5, 10):
                    t = stamp + pd.Timedelta(minutes=offset)
                    vol = (volume_at_end if i == 73 else 100.0) / 3.0
                    records.append((
                        t, close - 0.05, close + 0.10,
                        close - 0.10, close, vol,
                    ))
            return pd.DataFrame(
                records, columns=[
                    "Date", "Open", "High", "Low", "Close", "Volume"
                ]).set_index("Date")

        now = stamps[-1] + pd.Timedelta(minutes=15)
        stock = make_5m(prices, volume_ratio * 100)
        sector = make_5m(benchmark_prices, 200)
        return stock, sector, now

    def test_exact_asjr_gann_main_mid_unchanged(self):
        self.assertEqual(gann_levels(553.6, 500.0, 590.0), [
            (541.0, "MID"), (553.0, "MID"), (565.0, "MID"),
            (577.0, "MAIN"), (589.0, "MID")
        ])

    def test_real_cross_confirmed_with_slope_volume_sector(self):
        stock, sector, now = self.sample()
        event = signal_on_closed_bars(
            stock, "AMD", "A", now=now, benchmark_df=sector)
        self.assertIsNotNone(event)
        self.assertEqual(event["version"], "V2")
        self.assertEqual(event["trigger"], "REAL CROSS + FOLLOW-THROUGH")
        self.assertEqual(event["timeframe"], "15min")
        self.assertEqual(event["bar_uk"], "2026-11-12 19:45")
        self.assertGreater(event["ema9_slope_pct"], 0.05)
        self.assertGreater(event["ema20_slope_pct"], 0.01)
        self.assertGreaterEqual(event["volume_ratio"], 1.25)
        self.assertEqual(event["sector"], "SMH BULLISH")

    def test_complete_three_5m_bars_only(self):
        stock, _, now = self.sample()
        bars = build_complete_15m_bars(stock, now=now)
        self.assertEqual(len(bars), 74)
        self.assertAlmostEqual(bars["Volume"].iloc[-1], 200.0, places=5)
        self.assertEqual(bars.index[-1], pd.Timestamp(
            "2026-11-12T19:45:00Z"))

    def test_missing_group_a_benchmark_fails_closed(self):
        stock, _, now = self.sample()
        self.assertIsNone(signal_on_closed_bars(stock, "AMD", "A", now=now))

    def test_weak_group_a_sector_rejected(self):
        stock, sector, now = self.sample(benchmark_up=False)
        self.assertIsNone(signal_on_closed_bars(
            stock, "AMD", "A", now=now, benchmark_df=sector))

    def test_b_c_can_diverge_from_semi_sector(self):
        stock, _, now = self.sample()
        self.assertIsNotNone(signal_on_closed_bars(
            stock, "PGR", "B", now=now))

    def test_low_volume_rejected(self):
        stock, sector, now = self.sample(volume_ratio=1.0)
        self.assertIsNone(signal_on_closed_bars(
            stock, "AMD", "A", now=now, benchmark_df=sector))

    def test_insufficient_fast_slope_rejected(self):
        stock, sector, now = self.sample()
        self.assertIsNone(signal_on_closed_bars(
            stock, "AMD", "A", now=now, benchmark_df=sector,
            filters={"ema9_min_slope_pct": 99.0}))

    def test_old_fake_cross_rejected(self):
        stock, sector, now = self.sample()
        # Artificially eliminate earlier crossover by flattening prior
        # closes: a single late breakout is NOT a confirmed crossover.
        bars = build_complete_15m_bars(stock, now=now)
        for t in bars.index[:-1]:
            idx = stock.index.floor("15min") == t
            stock.loc[idx, ["Open", "High", "Low", "Close"]] = [
                99.95, 100.10, 99.90, 100.00
            ]
        self.assertIsNone(signal_on_closed_bars(
            stock, "AMD", "A", now=now, benchmark_df=sector))

    def test_missing_last_5m_bar_never_alerts(self):
        stock, sector, now = self.sample()
        stock = stock.drop(stock.index[-1])
        self.assertIsNone(signal_on_closed_bars(
            stock, "AMD", "A", now=now, benchmark_df=sector))

    def test_stale_candle_never_alerts(self):
        stock, sector, now = self.sample()
        self.assertIsNone(signal_on_closed_bars(
            stock, "AMD", "A", now=now + pd.Timedelta(minutes=31),
            benchmark_df=sector))

    def test_closed_signal_not_extended_hours(self):
        stock, sector, now = self.sample()
        stock.index = stock.index - pd.Timedelta(hours=8)
        sector.index = sector.index - pd.Timedelta(hours=8)
        now -= pd.Timedelta(hours=8)
        self.assertIsNone(signal_on_closed_bars(
            stock, "AMD", "A", now=now, benchmark_df=sector))

    def test_approved_universe_unchanged(self):
        settings, items = config()
        self.assertEqual(settings["version"], 2)
        self.assertEqual(settings["timeframe"], "15m")
        self.assertEqual(len(items), 49)
        self.assertEqual([
            sum(group == g for _, group in items) for g in "ABC"
        ], [22, 17, 10])


if __name__ == "__main__":
    unittest.main()
