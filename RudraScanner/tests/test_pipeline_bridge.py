"""Regression guards for the current Chakra Wicks/Reversal/Scanner bridge.

Do NOT initiate any broker, Discord or VPS call.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
ASJR=ROOT/"ASJR_Analyst"
if str(ASJR) not in sys.path:
    sys.path.insert(0,str(ASJR))

import Utils.asjr_alerts as alerts


class ChakraBridgeTests(unittest.TestCase):
    def test_scanner_discord_is_last_after_locked_reversal(self):
        result={"alert_data":[],"rudra_reversal_alerts":[]}
        with patch.object(alerts.rudra_reversal,"prepare_alert",
                          return_value="REVERSAL FIRST"):
            with patch("RudraScanner.delivery.prepare_queued_alert",
                       side_effect=AssertionError("scanner should not steal Reversal")):
                message=alerts.prepare_alert(result)
        self.assertEqual(message,"REVERSAL FIRST")

    def test_scanner_queue_uses_existing_prepare_alert_fallback(self):
        result={"alert_data":[],"rudra_reversal_alerts":[]}
        with patch.object(alerts.rudra_reversal,"prepare_alert",return_value=""):
            with patch("RudraScanner.delivery.prepare_queued_alert",
                       return_value="RUDRA RADAR DISCORD") as mock:
                message=alerts.prepare_alert(result)
        self.assertEqual(message,"RUDRA RADAR DISCORD")
        self.assertEqual(mock.call_count,1)

    def test_external_mark_sent_falls_through_to_scanner_ack(self):
        with patch.object(alerts,"_read_json",return_value={}):
            with patch.object(alerts.rudra_reversal,
                              "has_prepared_batch",return_value=False):
                with patch("RudraScanner.delivery.mark_queued_sent",
                           return_value=1) as ack:
                    count=alerts.mark_alert_sent()
        self.assertEqual(count,1)
        self.assertEqual(ack.call_count,1)

    def test_scanner_priority_is_after_legacy_immediate_delivery(self):
        src=(ASJR/"Tests"/"test_asjr_pipeline.py").read_text(encoding="utf-8")
        at_discord=src.index("if alert_sender is not None:")
        at_discovery=src.index("rudra_scanner_shadow = run_bot_shadow(")
        at_scan=src.index("rudra_scanner_features = run_live_scanner_round(")
        at_legacy=src.index("alert_data = alerts.build_wick_alerts(")
        self.assertLess(at_legacy,at_discord)
        self.assertLess(at_discord,at_discovery)
        self.assertLess(at_discovery,at_scan)
        self.assertIn("uni = universe.build_universe(",src)
        self.assertIn("run_rudra_reversal_strategy(\n                trade_date=trade_date,",src)


if __name__=="__main__":
    unittest.main()
