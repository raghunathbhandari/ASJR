"""Monday scanner sidecar safety: legacy data reuse and as-of ETF context."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from RudraScanner.live_round import (
    collect_live_bars, intraday_direction, run_live_scanner_round,
)
from RudraScanner.bot_hook import scanner_runtime, run_bot_shadow


def sample_market():
    prices = {"SPY": (100, 101), "QQQ": (100, 101.5),
              "SMH": (100, 102), "INTC": (100, 103)}
    prev = pd.Timestamp("2026-10-09T19:55:00Z")
    current = pd.Timestamp("2026-10-12T13:30:00Z")
    out = []
    for ticker, (close_prior, close_now) in prices.items():
        out.append({"Ticker":ticker, "Date":prev, "Open":close_prior,
                    "High":close_prior+1, "Low":close_prior-1,
                    "Close":close_prior, "Volume":1000, "WAP":close_prior})
        for i in range(20):
            value = close_now + i * .02
            out.append({"Ticker":ticker,
                        "Date": current + pd.Timedelta(minutes=5*i),
                        "Open":value, "High":value+.3,
                        "Low":value-.3, "Close":value, "Volume":2000,
                        "WAP":value})
    return pd.DataFrame(out)


def candlestick_features(frame):
    from RudraScanner.features import build_scanner_features
    features, _ = build_scanner_features(
        frame, now=pd.Timestamp("2026-10-12T18:00:00Z"))
    return features


class LiveRoundTests(unittest.TestCase):
    def test_reuses_existing_legacy_5m_without_second_request(self):
        raw = sample_market()
        def no_api(*args, **kwargs):
            raise AssertionError("Already cached symbol caused a duplicate IBKR request")
        candles, status = collect_live_bars(
            object(), [{"ticker":"INTC","fixed_sector":"Semiconductors"}],
            raw, fetch=no_api)
        self.assertEqual(status["requested"], [])
        self.assertEqual(set(status["symbols"]), {"INTC","SPY","QQQ","SMH"})
        self.assertEqual(candles["Ticker"].nunique(), 4)

    def test_missing_only_new_stock_and_etfs_requested_once(self):
        raw = sample_market()
        raw = raw[raw["Ticker"] == "INTC"].copy()
        called = []
        def fake_fetch(app, names, **kwargs):
            called.extend(names)
            extra = sample_market()
            names = set(names)
            frames = {}
            for symbol in names:
                data = extra[extra["Ticker"] == symbol]
                frames[symbol] = data.drop(columns=["Ticker"]).set_index("Date").rename_axis("Date")
            return frames
        candles, status = collect_live_bars(
            object(), [{"ticker":"INTC","fixed_sector":"Semiconductors"}],
            raw, fetch=fake_fetch)
        self.assertEqual(set(called), {"SPY","QQQ","SMH"})
        self.assertEqual(candles["Ticker"].nunique(), 4)
        self.assertEqual(len(status["requested"]), 3)

    def test_index_and_sector_need_fresh_matching_bars(self):
        features = candlestick_features(sample_market())
        index, sectors, state = intraday_direction(
            features, "2026-10-12", ticker_etfs={"INTC":"SMH"})
        self.assertEqual(index, "LONG")
        self.assertEqual(sectors["INTC"], "LONG")
        self.assertGreater(state["index_pct"]["SPY"], 0.2)
        # If QQQ's latest five-minute bar is absent, index must WAIT.
        absent = features[~(
            (features["ticker"] == "QQQ") &
            (features["session_date_et"] == "2026-10-12") &
            (features["minutes_into_rth"] == 95)
        )].copy()
        index, sectors, status = intraday_direction(
            absent, "2026-10-12", ticker_etfs={"INTC":"SMH"})
        self.assertEqual(index, "WAIT")

    def test_all_context_unavailable_fails_closed(self):
        features = candlestick_features(sample_market())
        features = features[features["ticker"] == "INTC"]
        index, biases, state = intraday_direction(
            features, "2026-10-12", ticker_etfs={"INTC":"SMH"})
        self.assertEqual(index, "WAIT")
        self.assertEqual(biases["INTC"], "WAIT")

    def test_shadow_writes_report_without_changing_legacy_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            repo=Path(folder)
            (repo/"ASJR_Analyst"/"config").mkdir(parents=True)
            raw=sample_market()
            before=raw.copy(deep=True)
            result=run_live_scanner_round(
                object(), repo, "2026-10-12",
                [{"ticker":"INTC","fixed_sector":"Semiconductors"}],
                raw, fetch=lambda *a,**k: (_ for _ in ()).throw(
                    AssertionError("unexpected broker request")),
                now=pd.Timestamp("2026-10-12T18:00:00Z"))
            self.assertEqual(result["state"],"EXPERIMENTAL_RESEARCH")
            self.assertEqual(result["alert_delivery"],"DISABLED")
            self.assertTrue(Path(result["report"]).is_file())
            self.assertIn("TOP DOWN | LONG", Path(result["report"]).read_text())
            pd.testing.assert_frame_equal(before,raw)

    def test_runtime_starts_monday_off_on_friday(self):
        with tempfile.TemporaryDirectory() as folder:
            config=Path(folder)/"ASJR_Analyst"/"config"/"rudra_scanner_runtime.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({
                "enabled_from_et":"2026-10-12","mode":"shadow",
                "research":True,"alerts_enabled":False,
                "thresholds_approved":False
            }))
            friday=scanner_runtime(folder,"2026-10-09")
            monday=scanner_runtime(folder,"2026-10-12")
            self.assertEqual(friday["mode"],"off")
            self.assertEqual(monday["mode"],"shadow")
            self.assertTrue(monday["research"])
            self.assertFalse(monday["alerts_enabled"])

    def test_shadow_returns_candidates_for_5m_sidecar(self):
        class FakeApp:
            def historicalData(self, req, bar):
                return None
        response = {
            "candidates":[{"ticker":"INTC","sources":["FIXED"],
                           "fixed_sector":"Semiconductors"}],
            "ai":{"state":"PARTIAL"},"fixed":{"state":"OK"},
            "ibkr":{x:{"state":"EMPTY"} for x in (
                "TOP_PERC_GAIN","TOP_PERC_LOSE","HOT_BY_VOLUME","MOST_ACTIVE")},
        }
        with patch("RudraScanner.bot_hook.save_discovery",
                   return_value=response):
            answer=run_bot_shadow(
                FakeApp(),"2026-10-12",repo_root="/tmp/test",
                mode="shadow")
        self.assertEqual(answer["state"],"SHADOW_SAVED")
        self.assertEqual([r["ticker"] for r in answer["candidates"]],["INTC"])
        self.assertFalse(answer["legacy_universe_changed"])


if __name__ == "__main__":
    unittest.main()
