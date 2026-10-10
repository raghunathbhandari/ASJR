"""Idempotent scanner message delivery requires two explicit gates."""
import tempfile
import unittest
from pathlib import Path

from RudraScanner.delivery import (deliver_scanner_alerts, event_key,
    format_alert, queue_scanner_events, prepare_queued_alert,
    mark_queued_sent)


def event(name="INTC", time="2026-10-09T16:00:00+00:00"):
    return {
        "ticker": name, "pattern": "SECOND CHANCE",
        "direction": "LONG", "bar_start_utc": time,
        "bar_time_uk": "2026-10-09 17:00 BST",
        "price": 100.0, "ema9": 99.8, "vwap": 99.6,
        "status": "EXPERIMENTAL_RESEARCH",
    }


class DeliveryTests(unittest.TestCase):
    def test_double_gate_never_sends_without_approval(self):
        calls = []
        send = lambda message: calls.append(message) or True
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "state.json"
            for enabled, approved in ((False, False), (True, False), (False, True)):
                result = deliver_scanner_alerts(
                    [event()], send, state_file=p, trade_date="2026-10-09",
                    enabled=enabled, thresholds_approved=approved,
                )
                self.assertEqual(result["state"], "DISABLED")
            self.assertEqual(calls, [])
            self.assertFalse(p.exists())

    def test_success_is_deduped_after_ack(self):
        outputs = []
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "state.json"
            args = {"state_file": path, "trade_date": "2026-10-09",
                    "enabled": True, "thresholds_approved": True}
            first = deliver_scanner_alerts(
                [event(), event()], lambda msg: outputs.append(msg) or True,
                **args)
            self.assertEqual(first["sent"], 1)
            self.assertEqual(len(outputs), 1)
            second = deliver_scanner_alerts(
                [event()], lambda msg: outputs.append(msg) or True, **args)
            self.assertEqual(second["state"], "NO_NEW_EVENTS")
            self.assertEqual(len(outputs), 1)
            self.assertIn("UK TIME", outputs[0])

    def test_failed_send_is_not_acknowledged(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "state.json"
            with self.assertRaises(RuntimeError):
                deliver_scanner_alerts(
                    [event()], lambda msg: False,
                    state_file=path, trade_date="2026-10-09",
                    enabled=True, thresholds_approved=True)
            self.assertFalse(path.exists())
            response = deliver_scanner_alerts(
                [event()], lambda msg: True, state_file=path,
                trade_date="2026-10-09",
                enabled=True, thresholds_approved=True)
            self.assertEqual(response["sent"], 1)

    def test_existing_bot_prepares_scanner_only_after_queue_and_ack(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root) / "scanner_state.json"
            batch = Path(root) / "scanner_batch.json"
            self.assertEqual(
                queue_scanner_events([event()], state_file=state,
                                     trade_date="2026-10-09")["queued_new"], 1)
            self.assertEqual(
                queue_scanner_events([event()], state_file=state,
                                     trade_date="2026-10-09")["queued_new"], 0)
            message = prepare_queued_alert(state_file=state,
                                           batch_file=batch)
            self.assertIn("INTC", message)
            self.assertIn("EXPERIMENTAL", message)
            # Preparing a Discord message must never count as sent.
            self.assertEqual(len(__import__("json").loads(state.read_text())["pending"]),1)
            self.assertEqual(mark_queued_sent(state_file=state, batch_file=batch),1)
            self.assertEqual(prepare_queued_alert(state_file=state,
                                                  batch_file=batch),"")
            self.assertFalse(batch.exists())

    def test_scanner_queue_preserves_failure_until_marked(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root) / "state.json"
            batch = Path(root) / "batch.json"
            queue_scanner_events([event("INTC"),event("WDC")],
                                 state_file=state, trade_date="2026-10-09")
            before = prepare_queued_alert(state_file=state,batch_file=batch)
            second = prepare_queued_alert(state_file=state,batch_file=batch)
            self.assertEqual(before, second)
            self.assertGreater(len(__import__("json").loads(state.read_text())["pending"]),0)

    def test_unapproved_status_not_sent(self):
        with tempfile.TemporaryDirectory() as root:
            invalid = dict(event())
            invalid["status"] = "DATA_NOT_READY"
            result = deliver_scanner_alerts(
                [invalid], lambda msg: True,
                state_file=Path(root)/"state.json",
                trade_date="2026-10-09",
                enabled=True, thresholds_approved=True)
            self.assertEqual(result["sent"], 0)


if __name__ == "__main__":
    unittest.main()
