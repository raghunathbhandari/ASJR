"""Regression tests for relative wick gates and persistent delivery state."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Utils import asjr_alerts as alerts

CONFIG = alerts.ROOT / 'config' / 'wick_setups.json'


def candles(last=None, scale=1):
    rows = [dict(open=100, high=100.5, low=99.5, close=100.1, volume=1000) for _ in range(12)]
    rows.append(last or dict(open=100, high=100.2, low=98.2, close=100.1, volume=2000))
    frame = pd.DataFrame(rows)
    for col in ('open', 'high', 'low', 'close'):
        frame[col] *= scale
    frame['ticker'] = 'TEST'
    frame['datetime'] = pd.date_range('2026-10-02 14:00', periods=len(frame), freq='5min', tz='UTC')
    frame['bar_et'] = frame['datetime'].dt.tz_convert(alerts.ET)
    return frame


class RelativeWicks(unittest.TestCase):
    def event(self, frame, side='LOWER'):
        return alerts._wick_event('TEST', frame, 12, side, alerts._load_wick_setups(CONFIG))

    def test_price_scale_invariance(self):
        events = [self.event(candles(scale=s)) for s in (0.1, 1, 5, 20)]
        self.assertTrue(all(e and e['swept_reclaimed'] for e in events))
        self.assertEqual(len({e['setup_id'] for e in events}), 1)

    def test_small_range_rejected_even_with_high_volume(self):
        self.assertIsNone(self.event(candles(dict(open=100, high=100.02, low=99.8, close=100.01, volume=10000))))

    def test_no_context_rejected(self):
        frame = candles().tail(1).reset_index(drop=True)
        self.assertIsNone(alerts._wick_event('TEST', frame, 0, 'LOWER', alerts._load_wick_setups(CONFIG)))

    def test_volume_or_sweep(self):
        ordinary = dict(open=105, high=107, low=105, close=105.2, volume=1000)
        self.assertIsNone(self.event(candles(ordinary), 'UPPER'))
        ordinary['volume'] = 2000
        self.assertIsNotNone(self.event(candles(ordinary), 'UPPER'))
        sweep = candles(dict(open=100, high=100.2, low=98.2, close=100.1, volume=100))
        self.assertIsNotNone(self.event(sweep))

    def test_expansion_exception(self):
        # Accepted MSFT-like 41.7% wick / 1.3x body with strong expansion.
        frame = candles(dict(open=99.57, high=100.82, low=97.9, close=100.5, volume=34000))
        event = self.event(frame)
        self.assertIsNotNone(event)
        self.assertEqual(event['setup_id'], 'expansion_rejection_ratio')

    def test_noise_sample_shapes(self):
        samples = [(19,19.2,18.97,19.01),(19.32,19.36,19.24,19.35),(91,91.15,90.69,90.72),(73.84,73.93,73.5,73.56)]
        for o,h,l,c in samples:
            frame = candles(dict(open=o,high=h,low=l,close=c,volume=3000))
            for side in ('UPPER','LOWER'):
                self.assertIsNone(self.event(frame,side))

    def test_one_side_and_retry_ack(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)/'state.json'; batch = Path(tmp)/'batch.json'
            alerts._write_json_atomic(state, alerts._new_state('2026-10-02'))
            # Deliberately permissive config tests queue's one-side guarantee.
            config = Path(tmp)/'config.json'
            config.write_text(json.dumps({'setups':[dict(id='test',side='BOTH',min_prior_bars=12)]}))
            frame = candles()
            events = alerts.build_wick_alerts(frame,trade_date='2026-10-02',now='2026-10-02 16:00Z',state_file=state,config_file=config)
            self.assertEqual(len(events),1)
            self.assertEqual(events,alerts.build_wick_alerts(frame,trade_date='2026-10-02',now='2026-10-02 16:00Z',state_file=state,config_file=config))
            text = alerts.prepare_alert({'alert_data':events},state_file=state,batch_file=batch)
            self.assertIn('BST',text)
            self.assertIn('median range',text)
            self.assertEqual(alerts.mark_alert_sent(state_file=state,batch_file=batch),1)
            self.assertEqual(alerts.build_wick_alerts(frame,trade_date='2026-10-02',now='2026-10-02 16:00Z',state_file=state,config_file=config),[])

    def test_upgrade_discards_old_backlog(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'state.json'
            state.write_text(json.dumps({'schema_version':3,'pending':[{'bad':'legacy'}]}))
            events=alerts.build_wick_alerts(candles(),trade_date='2026-10-02',now='2026-10-02 16:00Z',state_file=state)
            self.assertEqual(events,[])
            self.assertEqual(json.loads(state.read_text())['schema_version'],4)


if __name__ == '__main__':
    unittest.main()
