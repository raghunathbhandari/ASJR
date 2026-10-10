"""Regression tests for SSH scan_now -> EXISTING Chakra five-minute pass.

All tests use temporary folders / mocks; NO IBKR, orders or Discord.
"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from RudraScanner import manual_request as ipc
from RudraScanner import scan_now as cli

DAY = "2026-10-12"


class ManualScanTests(unittest.TestCase):
    def test_no_new_connection_or_broker_in_request_store(self):
        with tempfile.TemporaryDirectory() as p:
            root = Path(p)
            state, created = ipc.request_scan(root, DAY)
            self.assertTrue(created)
            self.assertEqual(state["status"], "QUEUED")
            self.assertEqual(state["broker_connections_created"], 0)
            self.assertEqual(state["orders"], 0)
            self.assertEqual(state["scanner_discord_sends"], 0)
            self.assertFalse((root / "ASJR_Analyst" / "DataLake").exists())

    def test_duplicate_ssh_requests_share_one_pending_slot(self):
        with tempfile.TemporaryDirectory() as p:
            a, first = ipc.request_scan(p, DAY)
            b, second = ipc.request_scan(p, DAY)
            self.assertTrue(first)
            self.assertFalse(second)
            self.assertEqual(a["request_id"], b["request_id"])

    def test_different_trade_date_will_not_capture(self):
        with tempfile.TemporaryDirectory() as p:
            state, _ = ipc.request_scan(p, DAY)
            self.assertIsNone(ipc.capture_pending(p, "2026-10-13"))
            self.assertEqual(ipc.capture_pending(p, DAY), state["request_id"])

    def test_completed_cycle_acknowledges_real_saved_report(self):
        with tempfile.TemporaryDirectory() as p:
            root = Path(p)
            report = root / "ASJR_Analyst" / "DataLake" / DAY / "reports" / "scalp_radar.txt"
            report.parent.mkdir(parents=True)
            report.write_text("REAL CYCLE RESEARCH REPORT\n")
            original, _ = ipc.request_scan(root, DAY)
            token = ipc.capture_pending(root, DAY)
            reply = ipc.complete_pending(
                root, DAY, token,
                discovery={"mode": "shadow", "state": "SHADOW_SAVED",
                           "ibkr_scan_states": {"TOP_PERC_GAIN": "SUCCESS"},
                           "selected_total": 10},
                five_minute={"state": "EXPERIMENTAL_RESEARCH",
                             "report": str(report)},
                hourly={"state": "CACHED"},
            )
            self.assertEqual(reply["status"], "COMPLETE")
            self.assertEqual(reply["selected_total"], 10)
            self.assertEqual(reply["request_id"], original["request_id"])
            self.assertTrue(ipc.load_request(root)["completed_at_utc"])

    def test_missing_or_failed_features_never_claim_success(self):
        with tempfile.TemporaryDirectory() as p:
            root = Path(p)
            state, _ = ipc.request_scan(root, DAY)
            reply = ipc.complete_pending(
                root, DAY, state["request_id"],
                discovery={"mode": "shadow", "state": "PARTIAL"},
                five_minute={"state": "ERROR"},
                hourly={"state": "NOT_READY"},
            )
            self.assertEqual(reply["status"], "DATA_NOT_READY")
            self.assertEqual(reply["report_path"], "")

    def test_no_ack_if_late_new_request_replaces_prior_id(self):
        with tempfile.TemporaryDirectory() as p:
            root = Path(p)
            state, _ = ipc.request_scan(root, DAY)
            pending = ipc.load_request(root)
            pending["status"] = "COMPLETE"
            ipc._atomic(ipc.request_path(root), pending)
            updated, made = ipc.request_scan(root, DAY)
            self.assertTrue(made)
            self.assertNotEqual(state["request_id"], updated["request_id"])
            answer = ipc.complete_pending(
                root, DAY, state["request_id"],
                discovery={}, five_minute={}, hourly={},
            )
            self.assertIsNone(answer)
            self.assertEqual(ipc.load_request(root)["request_id"], updated["request_id"])
            self.assertEqual(ipc.load_request(root)["status"], "QUEUED")

    def test_no_ack_for_off_mode_even_if_saved_report_exists(self):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p)
            report=root/"ASJR_Analyst"/"DataLake"/DAY/"reports"/"scalp_radar.txt"
            report.parent.mkdir(parents=True)
            report.write_text("OLD FILE\n")
            item,_=ipc.request_scan(root,DAY)
            answer=ipc.complete_pending(
                root,DAY,item["request_id"],
                discovery={"mode":"off","state":"OFF"},
                five_minute={"state":"EXPERIMENTAL_RESEARCH","report":str(report)},
                hourly={})
            self.assertEqual(answer["status"], "DATA_NOT_READY")

    def test_saturday_session_does_not_queue(self):
        sat=datetime(2026,10,10,15,0,tzinfo=timezone.utc)
        self.assertIsNone(ipc.current_trade_date(sat))
        with tempfile.TemporaryDirectory() as p:
            with patch.object(cli,"current_trade_date",return_value=None):
                result=cli.main(["--repo",p,"--no-wait"])
            self.assertEqual(result,2)
            self.assertFalse(ipc.request_path(p).exists())

    def test_active_session_queues_without_ibkr_on_ssh(self):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p)
            config=root/"ASJR_Analyst"/"config"/"rudra_scanner_runtime.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({
                "enabled_from_et":DAY, "mode":"shadow","research":True,
                "alerts_enabled":False,"thresholds_approved":False
            }))
            with patch.object(cli,"current_trade_date",return_value=DAY):
                code=cli.main(["--repo",p,"--no-wait"])
            self.assertEqual(code,0)
            self.assertEqual(ipc.load_request(p)["status"],"QUEUED")

    def test_manual_request_is_connected_at_existing_scanner_stage(self):
        root=Path(__file__).resolve().parents[2]
        pipeline=(root/"ASJR_Analyst"/"Tests"/"test_asjr_pipeline.py").read_text()
        before=pipeline.index("manual_scan_request_id = capture_pending(")
        existing=pipeline.index("rudra_scanner_shadow = run_bot_shadow(")
        completed=pipeline.index("manual_outcome = complete_pending(")
        self.assertLess(before,existing)
        self.assertLess(existing,completed)
        self.assertIn("five_minute=rudra_scanner_features",pipeline)
        self.assertIn("hourly=rudra_scanner_hourly",pipeline)
        self.assertIn("if alert_sender is not None:",pipeline)
        self.assertIn("rudra_reversal_alerts = run_rudra_reversal_strategy(",pipeline)


if __name__ == "__main__":
    unittest.main()
