"""Read-only Monday deployment preflight and allowed default flags."""
import tempfile
import unittest
from pathlib import Path
import json

from RudraScanner.live_preflight import preflight


class PreflightTests(unittest.TestCase):
    def test_monday_shadow_waits_for_canonical_hooks(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            cfg=root/"ASJR_Analyst"/"config"/"rudra_scanner_runtime.json"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(json.dumps({
                "enabled_from_et":"2026-10-12", "mode":"shadow",
                "research":True,"alerts_enabled":False,
                "thresholds_approved":False}))
            result=preflight(root)
            self.assertEqual(result["scheduled_mode"],"shadow")
            self.assertFalse(result["ready_to_shadow"])
            self.assertEqual(result["broker_requests"],0)
            self.assertEqual(result["discord_sends"],0)
            self.assertEqual(result["ai_valid_at_monday_open"],0)
            self.assertIn("warning",result)

    def test_monday_readiness_requires_legacy_and_scanner_bridge(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            paths={
                "config/rudra_scanner_runtime.json": json.dumps({
                    "enabled_from_et":"2026-10-12","mode":"shadow",
                    "research":True,"alerts_enabled":False,
                    "thresholds_approved":False}),
                "Tests/test_asjr_pipeline.py":
                    "run_live_scanner_round(\nalerts.build_wick_alerts(\n"
                    "run_rudra_reversal_strategy(\n",
                "Utils/asjr_alerts.py":
                    "prepare_queued_alert(\nmark_queued_sent(\n",
            }
            for p,contents in paths.items():
                full=root/"ASJR_Analyst"/p
                full.parent.mkdir(parents=True,exist_ok=True)
                full.write_text(contents)
            result=preflight(root)
            self.assertTrue(result["ready_to_shadow"])
            self.assertEqual(result["scheduled_mode"],"shadow")
            self.assertFalse(result["live_scanner_alerts_enabled"])


if __name__=="__main__":
    unittest.main()
