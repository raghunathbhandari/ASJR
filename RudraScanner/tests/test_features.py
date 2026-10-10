"""Offline exact WAP/VWAP, RVOL guards, five-pattern gating, WAP callback tests."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from RudraScanner.features import build_scanner_features
from RudraScanner.engine import evaluate_scanner, format_report, persist_features
from RudraScanner.patterns import (
    PatternSettings, PATTERNS, detect_five_patterns,
)
from RudraScanner.wap_capture import attach_wap, install_wap_capture


def candles(n=20, with_wap=True):
    start = pd.Timestamp("2026-10-09T13:30:00Z")  # 09:30 US EDT
    rows = []
    for i in range(n):
        price = 100 + i * 0.1
        row = {"Ticker": "INTC", "Date": start + pd.Timedelta(minutes=5*i),
               "Open": price, "High": price + 1,
               "Low": price - 1, "Close": price, "Volume": 1000}
        if with_wap:
            row["WAP"] = price
        rows.append(row)
    return pd.DataFrame(rows)


class FeatureIntegrationTests(unittest.TestCase):
    def test_exact_wap_rth_reset(self):
        raw = candles()
        values, status = build_scanner_features(
            raw, now=pd.Timestamp("2026-10-09T16:00:00Z"))
        self.assertEqual(len(values), 20)
        self.assertEqual(status["wap_state"], "AVAILABLE")
        self.assertEqual(status["vwap_ready_rows"], 20)
        self.assertAlmostEqual(float(values.iloc[0]["vwap"]), 100.0)
        self.assertAlmostEqual(float(values.iloc[-1]["vwap"]), 100.95)
        self.assertTrue(values["ema9_ready"].iloc[-1])
        self.assertEqual(status["rvol_state"],
                         "INSUFFICIENT_20_FULL_RTH_SESSIONS")
        self.assertFalse(values["rvol20_ready"].any())

    def test_missing_wap_reports_not_ready_never_approximates(self):
        values, status = build_scanner_features(
            candles(with_wap=False),
            now=pd.Timestamp("2026-10-09T16:00:00Z"))
        self.assertEqual(status["vwap_ready_rows"], 0)
        self.assertEqual(status["wap_state"], "WAP_MISSING_OR_INCOMPLETE_RTH")
        self.assertTrue(values["vwap"].isna().all())
        self.assertTrue(values["ema9_ready"].iloc[-1])

    def test_first_bar_missing_does_not_make_false_exact_vwap(self):
        raw = candles().iloc[1:].copy()
        values, status = build_scanner_features(
            raw, now=pd.Timestamp("2026-10-09T16:00:00Z"))
        self.assertEqual(status["vwap_ready_rows"], 0)

    def test_rth_vwap_resets_but_ema_is_continuous(self):
        friday = candles()
        monday = candles(10)
        monday["Date"] = monday["Date"] + pd.Timedelta(days=3)
        monday["Open"] += 2
        monday["High"] += 2
        monday["Low"] += 2
        monday["Close"] += 2
        monday["WAP"] += 2
        values, status = build_scanner_features(
            pd.concat([friday, monday], ignore_index=True),
            now=pd.Timestamp("2026-10-12T15:00:00Z"))
        last_friday = values[values["session_date_et"] == "2026-10-09"].iloc[-1]
        first_monday = values[values["session_date_et"] == "2026-10-12"].iloc[0]
        self.assertAlmostEqual(float(first_monday["vwap"]), 102.0)
        self.assertNotAlmostEqual(float(first_monday["ema9"]), 102.0)
        self.assertTrue(first_monday["ema9_ready"])
        self.assertNotAlmostEqual(float(last_friday["vwap"]), float(first_monday["vwap"]))

    def test_safe_engine_report_and_namespaced_persist(self):
        raw = candles(with_wap=False)
        data, report = evaluate_scanner(
            raw, now=pd.Timestamp("2026-10-09T16:00:00Z"))
        self.assertEqual(report["state"], "INDICATORS_ONLY")
        self.assertEqual(report["events"], [])
        self.assertIn("WAP_MISSING", format_report("2026-10-09", report))
        with tempfile.TemporaryDirectory() as temp:
            paths = persist_features(temp, "2026-10-09", data, report)
            self.assertTrue(Path(paths["feature_csv"]).exists())
            self.assertTrue(Path(paths["research_report"]).exists())
            raw_path = Path(temp) / "ASJR_Analyst" / "DataLake" / "2026-10-09" / "raw"
            self.assertFalse((raw_path / "intraday_5m.csv").exists())

    def test_patterns_research_gate_wait_without_index_sector_confirmation(self):
        raw = candles()
        features, status = build_scanner_features(
            raw, now=pd.Timestamp("2026-10-09T16:00:00Z"))
        off, off_status = detect_five_patterns(features)
        self.assertEqual(off, [])
        self.assertEqual(off_status["state"], "DISABLED")
        on, on_status = detect_five_patterns(
            features, settings=PatternSettings(enabled_for_research=True))
        self.assertEqual(on, [])
        self.assertEqual(on_status["blocked_context"], 1)
        self.assertEqual(len(PATTERNS), 5)

    def test_fashionably_late_symmetric_cross_on_completed_candles(self):
        rows = []
        for i in range(18):
            price = 101 + i * 0.1
            rows.append({
                "ticker": "TEST", "datetime": pd.Timestamp("2026-10-09T13:30Z")
                    + pd.Timedelta(minutes=i*5),
                "bar_time_uk": "2026-10-09 14:30 BST",
                "session": "RTH", "session_date_et": "2026-10-09",
                "minutes_into_rth": i*5, "open": price-0.1,
                "close": price, "high": price+0.25, "low": price-0.3,
                "volume": 2000, "ema9": price-0.05 if i<17 else price-0.1,
                "vwap": price+0.2 if i<17 else price-0.2,
                "vwap_ready": True, "ema9_ready": True,
                "rvol20": None, "rvol20_ready": False,
                "relative_volume_12bar": 1.8,
                "ema9_slope5_pct": 0.5,
            })
        signals, state = detect_five_patterns(
            pd.DataFrame(rows), index_bias="LONG",
            sector_bias_by_ticker={"TEST": "LONG"},
            settings=PatternSettings(enabled_for_research=True))
        self.assertTrue(any(x["pattern"] == "FASHIONABLY LATE" for x in signals))
        self.assertTrue(all(x["status"] == "EXPERIMENTAL_RESEARCH" for x in signals))


class WapTapTests(unittest.TestCase):
    def test_additive_wap_callback_and_old_parser_compatibility(self):
        class FakeApp:
            def __init__(self):
                self.data = {42: []}
            def historicalData(self, req, bar):
                self.data[req].append([
                    str(bar.date), bar.open, bar.high, bar.low,
                    bar.close, bar.volume,
                ])
        fake = FakeApp()
        self.assertTrue(install_wap_capture(fake))
        self.assertFalse(install_wap_capture(fake))
        fake._rudra_wap_sidecar[42] = []
        fake.historicalData(42, SimpleNamespace(
            date="1791552600", open=100, high=101, low=99,
            close=100, volume=1000, wap=100.25))
        self.assertEqual(len(fake.data[42][0]), 6)
        self.assertEqual(fake._rudra_wap_sidecar[42], [("1791552600", 100.25)])
        parsed = pd.DataFrame(
            {"Close": [100]},
            index=pd.DatetimeIndex([pd.to_datetime(
                1791552600, unit="s", utc=True).tz_convert("America/New_York")])
        )
        decorated = attach_wap(fake, 42, parsed, fake.data[42])
        self.assertAlmostEqual(float(decorated.iloc[0]["WAP"]), 100.25)
        self.assertNotIn(42, fake._rudra_wap_sidecar)

    def test_wap_attaches_by_time_when_callbacks_are_out_of_order(self):
        class Fake:
            _rudra_wap_sidecar = {
                5: [("1791552900", 101.5), ("1791552600", 100.25)]
            }
        timestamps = pd.to_datetime([1791552600, 1791552900], unit="s", utc=True)
        parsed = pd.DataFrame({"Close": [100, 101]}, index=timestamps)
        attached = attach_wap(
            Fake(), 5, parsed, [
                ["1791552900", 0, 0, 0, 0, 0],
                ["1791552600", 0, 0, 0, 0, 0],
            ])
        self.assertEqual(attached["WAP"].tolist(), [100.25, 101.5])


if __name__ == "__main__":
    unittest.main()
