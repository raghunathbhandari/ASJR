"""Immediate detection, overflow delivery and failed-send regression checks."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Utils import asjr_alerts as alerts
from test_relative_wicks import candles


class ImmediateWicks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / 'state.json'
        self.batch = Path(self.tmp.name) / 'delivery.json'
        alerts._write_json_atomic(self.state, alerts._new_state('2026-10-02'))

    def event(self):
        return alerts._wick_event('TEST', candles(), 12, 'LOWER', alerts._load_wick_setups())

    def many(self, count=80):
        events = [dict(self.event(), ticker=f'T{i:03}') for i in range(count)]
        state = alerts._new_state('2026-10-02')
        state['pending'] = events
        alerts._write_json_atomic(self.state, state)
        return events

    def test_first_completed_candle_alerts_without_following_bar(self):
        kwargs = dict(trade_date='2026-10-02', state_file=self.state)
        self.assertEqual(alerts.build_wick_alerts(candles(), now='2026-10-02 15:04:59Z', **kwargs), [])
        events = alerts.build_wick_alerts(candles(), now='2026-10-02 15:05:00Z', **kwargs)
        self.assertEqual(len(events), 1)
        self.assertNotIn('next_confirmed', events[0])
        message = alerts.prepare_alert({'alert_data': events}, batch_file=self.batch)
        self.assertIn('16:00', message)
        for unwanted in ('ASJR', 'UK', 'BST', 'GMT'):
            self.assertNotIn(unwanted, message)
        self.assertNotIn('Next:', message)

    def test_all_overflow_sent_in_same_call_and_acknowledged(self):
        result = {'alert_data': self.many()}
        messages = []
        count = alerts.send_alerts(result, messages.append, self.state, self.batch)
        self.assertEqual(count, 80)
        self.assertGreater(len(messages), 1)
        self.assertTrue(all(len(m) <= 1900 for m in messages))
        for i in range(80):
            self.assertEqual(''.join(messages).count(f'T{i:03} |'), 1)
        self.assertEqual(json.loads(self.state.read_text())['pending'], [])
        self.assertEqual(alerts.prepare_alert(result, batch_file=self.batch), '')
        self.assertEqual(alerts.send_alerts(result, messages.append, self.state, self.batch), 0)

    def test_failed_overflow_preserves_unsent_events_for_retry(self):
        result = {'alert_data': self.many()}
        messages = []
        def sender(message):
            messages.append(message)
            return len(messages) == 1
        with self.assertRaises(RuntimeError):
            alerts.send_alerts(result, sender, self.state, self.batch)
        pending = json.loads(self.state.read_text())['pending']
        self.assertGreater(len(pending), 0)
        self.assertLess(len(pending), 80)
        self.assertEqual(result['alert_data'], pending)
        retried = []
        self.assertEqual(alerts.send_alerts(result, retried.append, self.state, self.batch), len(pending))
        for event in pending:
            self.assertNotIn(event['ticker'] + ' |', messages[0])
            self.assertIn(event['ticker'] + ' |', ''.join(retried))

    def test_wicks_not_blocked_by_mean_reversal(self):
        with patch.object(alerts.mean_reversal, 'prepare_alert', return_value='mean') as mean:
            text = alerts.prepare_alert({'alert_data':[self.event()], 'mean_reversal_alerts':[{}]}, batch_file=self.batch)
            self.assertIn('TEST |', text)
            mean.assert_not_called()

    def test_stale_mean_delivery_does_not_ack_wrong_strategy(self):
        events = self.many(1)
        alerts.prepare_alert({'alert_data': events}, batch_file=self.batch)
        with patch.object(alerts.mean_reversal, 'has_prepared_batch', return_value=True), patch.object(alerts.mean_reversal, 'mark_alert_sent') as mean_ack:
            self.assertEqual(alerts.mark_alert_sent(self.state, self.batch), 1)
            mean_ack.assert_not_called()

    def test_caller_install_is_idempotent_and_preserves_existing_code(self):
        path = alerts.ROOT / 'Tools' / 'enable_immediate_wicks.py'
        spec = importlib.util.spec_from_file_location('installer', path)
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        source = 'def run(app):\n    result = tp.run_asjr_manual_pipeline(\n        app=app,\n        git_submit=True,\n    )\n    SN.send_to_discord(tp.prepare_alert(result))\n'
        changed = installer.patch_source(source)
        self.assertIn('alert_sender=SN.send_to_discord', changed)
        self.assertEqual(installer.patch_source(changed), changed)
        self.assertIn('SN.send_to_discord(tp.prepare_alert(result))', changed)


if __name__ == '__main__':
    unittest.main()
