"""Offline DDB V2 regression tests: genuine bullish 15m EMA crossover only."""
import unittest
import pandas as pd

from RudraScanner.ddb_ema_gann_5m import (
    gann_levels, signal_on_closed_bars, build_complete_15m_bars,
    config, format_buy_watch_section,
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

    def test_real_cross_confirmed_with_slope_and_sector(self):
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
        self.assertNotIn("volume_ratio", event)
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

    def test_zero_volume_does_not_block_ema_signal(self):
        stock, sector, now = self.sample(volume_ratio=0.0)
        self.assertIsNotNone(signal_on_closed_bars(
            stock, "AMD", "A", now=now, benchmark_df=sector))

    def test_missing_volume_column_does_not_block_ema_signal(self):
        stock, sector, now = self.sample()
        stock = stock.drop(columns=["Volume"])
        self.assertIsNotNone(signal_on_closed_bars(
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

    def _shifted_sample(self, offset):
        stock, sector, now = self.sample()
        delta = pd.Timedelta(offset)
        stock.index = stock.index + delta
        sector.index = sector.index + delta
        return stock, sector, now + delta

    def test_premarket_buy_signal_allowed(self):
        stock, sector, now = self._shifted_sample("-6h45min")
        event = signal_on_closed_bars(
            stock, "AMD", "A", now=now, benchmark_df=sector)
        self.assertIsNotNone(event)
        self.assertEqual(event["session"], "PREMARKET")

    def test_afterhours_buy_signal_allowed(self):
        stock, sector, now = self._shifted_sample("3h15min")
        event = signal_on_closed_bars(
            stock, "PGR", "B", now=now)
        self.assertIsNotNone(event)
        self.assertEqual(event["session"], "AFTERHOURS")

    def test_overnight_buy_signal_allowed_when_bars_exist(self):
        stock, sector, now = self._shifted_sample("8h15min")
        event = signal_on_closed_bars(
            stock, "PGR", "B", now=now)
        self.assertIsNotNone(event)
        self.assertEqual(event["session"], "OVERNIGHT")

    def test_no_fabricated_signal_without_fresh_overnight_bars(self):
        stock, sector, now = self._shifted_sample("8h15min")
        self.assertIsNone(signal_on_closed_bars(
            stock, "PGR", "B", now=now + pd.Timedelta(minutes=31)))

    def test_no_cross_across_market_gap(self):
        stock, sector, now = self.sample()
        # Shift the cross bar earlier, but keep the 5m bucket complete.
        prev = stock.index.floor("15min").unique()[-2]
        mask = stock.index.floor("15min") == prev
        shift = pd.Timedelta(hours=1)
        stock.index = stock.index.where(~mask, stock.index - shift)
        self.assertIsNone(signal_on_closed_bars(
            stock, "PGR", "B", now=now))

    def test_extended_group_a_without_smh_is_labelled(self):
        stock, _, now = self._shifted_sample("8h15min")
        event = signal_on_closed_bars(stock, "AMD", "A", now=now)
        self.assertIsNotNone(event)
        self.assertEqual(event["sector"], "SMH UNAVAILABLE (EXTENDED)")

    def test_rth_group_a_without_smh_still_rejected(self):
        stock, _, now = self.sample()
        self.assertIsNone(signal_on_closed_bars(stock, "AMD", "A", now=now))

    def test_us_midnight_transition_does_not_suppress_valid_overnight_cross(self):
        # At 00:15 ET the confirmed signal must remain eligible; the earlier
        # cross and follow-through may straddle the local calendar boundary.
        stock, _, now = self._shifted_sample("9h30min")
        event = signal_on_closed_bars(stock, "PGR", "B", now=now)
        self.assertIsNotNone(event)
        self.assertEqual(event["session"], "OVERNIGHT")

    def test_discord_alert_omits_volume_and_gann(self):
        event = {
            "ticker": "AMD", "group": "A",
            "bar_uk": "2026-11-13 16:45", "close": 526.81,
            "ema9": 524.23, "ema20": 522.00,
            "ema9_slope_pct": 0.085, "ema20_slope_pct": 0.022,
            "sector": "SMH BULLISH",
            "volume_ratio": 1.8, "gann": [[529.0, "MAIN"]],
        }
        message = "\n".join(format_buy_watch_section(event))
        self.assertIn("AMD | GROUP A | BUY WATCH (V2)", message)
        self.assertIn("2026-11-13 16:45 UK | 15min", message)
        self.assertIn("ENTRY REF (15m close): 526.81", message)
        self.assertIn("NOT AN EXECUTED ORDER", message)
        self.assertIn("EMA9: 524.23 | slope +0.085%", message)
        self.assertIn("EMA20: 522.00 | slope +0.022%", message)
        self.assertIn("Sector: SMH BULLISH", message)
        self.assertNotIn("Volume", message)
        self.assertNotIn("GANN", message)
        self.assertNotIn("529.00", message)
        self.assertIn("UNKNOWN", message)

    def test_dispatch_identifier_is_shared_by_adapter_and_scanner(self):
        from pathlib import Path
        from RudraScanner.ddb_ema_gann_5m import DDB_ALERT_MODE
        adapter = (Path(__file__).resolve().parents[2] /
                   "ASJR_Analyst" / "Tests" / "test_asjr_pipeline.py"
                   ).read_text(encoding="utf-8")
        self.assertEqual(DDB_ALERT_MODE, "ddb_ema_gann_15m_v2")
        self.assertEqual(adapter.count("if _is_ddb_alert_result(result):"), 2)
        self.assertIn("return result.get(\"alert_mode\") == DDB_ALERT_MODE", adapter)
        self.assertNotIn('result.get("alert_mode") == "ddb_ema_gann_5m"', adapter)

    def test_send_alerts_routes_real_v2_result_to_discord(self):
        # Execute the actual adapter functions in isolation, without loading
        # the unrelated legacy pipeline modules or a live IBKR connection.
        import ast
        from pathlib import Path
        from unittest.mock import patch, Mock
        from RudraScanner.ddb_ema_gann_5m import DDB_ALERT_MODE
        source = (Path(__file__).resolve().parents[2] /
                  "ASJR_Analyst" / "Tests" / "test_asjr_pipeline.py"
                  ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        wanted = {"_is_ddb_alert_result", "send_alerts"}
        nodes = [n for n in tree.body
                 if isinstance(n, ast.FunctionDef) and n.name in wanted]
        self.assertEqual({n.name for n in nodes}, wanted)
        isolated = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]),
                     "<actual_adapter>", "exec"), isolated)
        self.assertTrue(isolated["_is_ddb_alert_result"](
            {"alert_mode": DDB_ALERT_MODE}))
        self.assertFalse(isolated["_is_ddb_alert_result"](
            {"alert_mode": "ddb_ema_gann_5m"}))
        sender = Mock(return_value=True)
        with patch("RudraScanner.ddb_ema_gann_5m.prepare_alert",
                   return_value="DDB 15m BUY WATCH") as prepare, patch(
            "RudraScanner.ddb_ema_gann_5m.mark_alert_sent"
        ) as acknowledge:
            sent = isolated["send_alerts"](
                {"alert_mode": DDB_ALERT_MODE}, sender)
        self.assertEqual(sent, 1)
        sender.assert_called_once_with("DDB 15m BUY WATCH")
        prepare.assert_called_once()
        acknowledge.assert_called_once()

    def test_failed_discord_send_does_not_ack_signal(self):
        import ast
        from pathlib import Path
        from unittest.mock import patch
        from RudraScanner.ddb_ema_gann_5m import DDB_ALERT_MODE
        source = (Path(__file__).resolve().parents[2] /
                  "ASJR_Analyst" / "Tests" / "test_asjr_pipeline.py"
                  ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        wanted = {"_is_ddb_alert_result", "send_alerts"}
        nodes = [n for n in tree.body
                 if isinstance(n, ast.FunctionDef) and n.name in wanted]
        isolated = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]),
                     "<actual_adapter>", "exec"), isolated)
        with patch("RudraScanner.ddb_ema_gann_5m.prepare_alert",
                   return_value="DDB 15m BUY WATCH"), patch(
            "RudraScanner.ddb_ema_gann_5m.mark_alert_sent"
        ) as acknowledge:
            with self.assertRaisesRegex(RuntimeError, "sender failed"):
                isolated["send_alerts"](
                    {"alert_mode": DDB_ALERT_MODE}, lambda _: False)
            acknowledge.assert_not_called()

    def test_approved_universe_unchanged(self):
        settings, items = config()
        self.assertEqual(settings["version"], 2)
        self.assertEqual(settings["timeframe"], "15m")
        self.assertFalse(settings["signal_filters"]["require_rth"])
        self.assertEqual(len(items), 49)
        self.assertEqual([
            sum(group == g for _, group in items) for g in "ABC"
        ], [22, 17, 10])


if __name__ == "__main__":
    unittest.main()
