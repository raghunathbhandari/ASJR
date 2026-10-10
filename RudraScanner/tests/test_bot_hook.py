"""Safe offline tests for gated live bot call and historical replay."""

import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from RudraScanner.bot_hook import run_bot_shadow
from RudraScanner.replay import historical_ibkr_candidates, REPLAY_CODE


def write_table(path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def fixture(root, day="2026-10-09"):
    base = Path(root) / "ASJR_Analyst"
    dated = base / "DataLake" / day
    write_table(dated / "config" / "fixed_watchlist.csv",
                ["ticker", "enabled", "notes"],
                [{"ticker": "INTC", "enabled": "1", "notes": "Permanent monitor"},
                 {"ticker": "ONDS", "enabled": "1", "notes": ""}])
    write_table(base / "config" / "ai_scanner_list.csv",
                ["ticker", "sector_etf", "bias", "catalyst",
                 "source_url", "published_at_utc", "researched_at_utc",
                 "expires_at_utc", "quality_status", "priority", "enabled",
                 "reason"],
                [{"ticker": "AI01", "bias": "WATCH", "enabled": "true",
                  "quality_status": "UNVERIFIED", "priority": "1"}])
    names = ["INTC", "AI01", "ONDS"] + [f"T{i:02d}" for i in range(25)]
    write_table(dated / "raw" / "ibkr_gapup.csv", ["ticker"],
                [{"ticker": t} for t in names])
    dates = []
    d = date(2026, 10, 9)
    while len(dates) < 20:
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d -= timedelta(days=1)
    daily = []
    for t in names:
        for day_text in dates:
            volume = 2_000_000
            close = 30 if t == "INTC" else (40 if t == "AI01" else 100)
            if t == "T00":
                volume = 200_000
            daily.append({"ticker": t, "date": day_text,
                          "close": close, "volume": volume})
    write_table(dated / "raw" / "daily_30d.csv",
                ["ticker", "date", "close", "volume"], daily)
    return dated


class BotIntegrationTests(unittest.TestCase):
    def test_default_off_cannot_contact_ibkr_or_write(self):
        with tempfile.TemporaryDirectory() as root:
            result = run_bot_shadow(None, "2026-10-09", repo_root=root,
                                    mode="off")
            self.assertEqual(result["state"], "OFF")
            self.assertFalse((Path(root) / "ASJR_Analyst").exists())

    def test_live_bot_cannot_accidentally_run_historical_replay(self):
        with tempfile.TemporaryDirectory() as root:
            result = run_bot_shadow(None, "2026-10-09", repo_root=root,
                                    mode="replay")
            self.assertEqual(result["state"], "REPLAY_NOT_ALLOWED_IN_LIVE_BOT")
            self.assertFalse((Path(root) / "ASJR_Analyst").exists())

    def test_legacy_source_replay_is_quality_screened_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as root:
            fixture(root)
            raw, meta = historical_ibkr_candidates(root, "2026-10-09")
            self.assertEqual(raw[0]["scan_code"], REPLAY_CODE)
            self.assertTrue(all(r["ticker"] not in ("ONDS", "T00") for r in raw))
            self.assertEqual(meta["source"], "LEGACY_GAPUP_REPLAY_NOT_LIVE")
            result = run_bot_shadow(None, "2026-10-09", repo_root=root,
                                    mode="replay", allow_replay=True)
            self.assertEqual(result["state"], "HISTORICAL_NOT_LIVE")
            self.assertEqual(result["selection"]["selected_by_source"],
                             {"FIXED": 1, "AI": 1, "IBKR": 10})
            self.assertEqual(result["selection"]["selected_total"], 12)
            self.assertEqual(result["signals"], [])
            selected = {r["ticker"]: r for r in result["candidates"]}
            self.assertEqual(selected["INTC"]["selection_source"], "FIXED")
            self.assertEqual(selected["AI01"]["selection_source"], "AI")
            self.assertTrue(all(t not in selected for t in ("ONDS", "T00")))
            self.assertFalse((Path(root) / "ASJR_Analyst" / "DataLake"
                              / "2026-10-09" / "raw" /
                              "ibkr_scanner_replay_list.csv").exists())

    def test_explicit_replay_save_is_namespaced_and_not_live(self):
        with tempfile.TemporaryDirectory() as root:
            dated = fixture(root)
            result = run_bot_shadow(
                None, "2026-10-09", repo_root=root, mode="replay",
                allow_replay=True, save_replay=True,
            )
            self.assertTrue(Path(result["report_path"]).exists())
            self.assertTrue((dated / "raw" /
                             "ibkr_scanner_replay_list.csv").exists())
            self.assertTrue((dated / "processed" /
                             "rudra_scanner_replay_candidates.csv").exists())
            self.assertFalse((dated / "raw" /
                              "ibkr_scanner_list.csv").exists())
            self.assertFalse((dated / "reports" /
                              "scalp_radar.txt").exists())
            text = Path(result["report_path"]).read_text()
            self.assertIn("NOT LIVE", text)
            self.assertIn("IBKR (10/10)", text)
            self.assertIn("Signals: NOT IMPLEMENTED", text)

    def test_shadow_invokes_existing_app_through_feature_gate(self):
        from unittest.mock import patch

        fake_app = object()
        fake_result = {
            "candidates": [{"ticker": "INTC", "selection_source": "FIXED"}],
            "ai": {"state": "PARTIAL"},
            "fixed": {"state": "OK"},
            "ibkr": {
                code: {"state": "EMPTY"} for code in (
                    "TOP_PERC_GAIN", "TOP_PERC_LOSE",
                    "HOT_BY_VOLUME", "MOST_ACTIVE"
                )
            },
        }
        with patch("RudraScanner.bot_hook.save_discovery",
                   return_value=fake_result) as saved:
            outcome = run_bot_shadow(fake_app, "2026-10-09",
                                     repo_root="/tmp/test",
                                     mode="shadow")
        self.assertEqual(outcome["state"], "SHADOW_SAVED")
        self.assertEqual(outcome["selected_total"], 1)
        self.assertEqual(outcome["alert_delivery"], "DISABLED")
        self.assertFalse(outcome["legacy_universe_changed"])
        self.assertIs(saved.call_args.args[0], fake_app)

    def test_replay_rejects_future_ibkr_lookahead(self):
        with tempfile.TemporaryDirectory() as root:
            fixture(root)
            with self.assertRaises(ValueError):
                run_bot_shadow(None, "2026-10-08", repo_root=root,
                               mode="replay", allow_replay=True,
                               replay_source_date="2026-10-09")


if __name__ == "__main__":
    unittest.main()
