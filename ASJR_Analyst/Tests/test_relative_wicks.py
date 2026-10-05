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

    def test_ordinary_rejection_requires_matching_sweep(self):
        ordinary = dict(open=105, high=107, low=105, close=105.2, volume=1000)
        self.assertIsNone(self.event(candles(ordinary), 'UPPER'))
        ordinary['volume'] = 1500
        self.assertIsNone(self.event(candles(ordinary), 'UPPER'))
        sweep = candles(dict(open=100, high=100.2, low=98.2, close=100.1, volume=100))
        self.assertIsNotNone(self.event(sweep))

    def test_expansion_requires_stricter_body_ratio(self):
        # Accepted MSFT-like 41.7% wick / 1.3x body with strong expansion.
        frame = candles(dict(open=99.57, high=100.82, low=97.9, close=100.5, volume=34000))
        event = self.event(frame)
        self.assertIsNone(event)

    def test_small_premarket_range_rejected(self):
        # Abnormal relative range and volume still cannot bypass the H-L floor.
        frame = candles(dict(open=100, high=100.005, low=99.81, close=100.01, volume=10000))
        frame.loc[:11, 'high'] = 100.02
        frame.loc[:11, 'low'] = 99.98
        self.assertIsNone(self.event(frame))

    def test_two_sided_expansion(self):
        frame = candles(dict(open=100, high=101, low=99, close=100.1, volume=10000))
        event = self.event(frame)
        self.assertIsNotNone(event)
        self.assertTrue(event['two_sided'])
        self.assertEqual(event['setup_id'], 'two_sided_expansion_wick')
        frame.loc[12, 'volume'] = 1000
        self.assertIsNone(self.event(frame))

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
            self.assertIn('16:00',text)
            self.assertIn('LOWER SWEEP',text)
            self.assertNotIn('Next:',text)
            self.assertEqual(alerts.mark_alert_sent(state_file=state,batch_file=batch),1)
            self.assertEqual(alerts.build_wick_alerts(frame,trade_date='2026-10-02',now='2026-10-02 16:00Z',state_file=state,config_file=config),[])

    def test_friday_user_reviewed_candles(self):
        # Recorded IBKR windows for accepted/rejected chart examples.
        cases = [('INTC', '13:35', None, [[122.5, 122.6, 122.4, 122.48, 269.0], [122.44, 122.5, 122.28, 122.45, 294.0], [122.42, 122.49, 122.28, 122.28, 208.0], [122.32, 122.34, 122.0, 122.0, 475.0], [122.04, 122.2, 121.88, 122.18, 288.0], [122.18, 122.28, 121.99, 121.99, 286.0], [122.0, 122.34, 121.95, 122.27, 503.0], [122.22, 122.49, 122.1, 122.34, 320.0], [122.3, 122.58, 122.23, 122.54, 521.0], [122.55, 122.7, 122.41, 122.41, 347.0], [122.49, 122.86, 122.48, 122.82, 518.0], [122.77, 123.8, 122.75, 123.78, 2599.0], [123.82, 123.88, 123.31, 123.68, 1950.0]]), ('INTC', '14:25', 'upper_liquidity_sweep_ratio', [[122.49, 122.86, 122.48, 122.82, 518.0], [122.77, 123.8, 122.75, 123.78, 2599.0], [123.82, 123.88, 123.31, 123.68, 1950.0], [123.71, 123.71, 123.22, 123.4, 707.0], [123.34, 123.7, 123.28, 123.65, 820.0], [123.65, 123.99, 123.5, 123.85, 1130.0], [123.88, 123.99, 123.75, 123.85, 831.0], [123.86, 124.01, 123.66, 123.93, 1383.0], [123.96, 124.06, 123.51, 123.72, 1180.0], [123.69, 123.78, 123.57, 123.63, 652.0], [123.62, 124.44, 123.59, 124.37, 2024.0], [124.36, 124.45, 123.91, 123.96, 663.0], [123.98, 124.64, 123.92, 124.04, 1649.0]]), ('INTC', '14:30', 'two_sided_expansion_wick', [[122.77, 123.8, 122.75, 123.78, 2599.0], [123.82, 123.88, 123.31, 123.68, 1950.0], [123.71, 123.71, 123.22, 123.4, 707.0], [123.34, 123.7, 123.28, 123.65, 820.0], [123.65, 123.99, 123.5, 123.85, 1130.0], [123.88, 123.99, 123.75, 123.85, 831.0], [123.86, 124.01, 123.66, 123.93, 1383.0], [123.96, 124.06, 123.51, 123.72, 1180.0], [123.69, 123.78, 123.57, 123.63, 652.0], [123.62, 124.44, 123.59, 124.37, 2024.0], [124.36, 124.45, 123.91, 123.96, 663.0], [123.98, 124.64, 123.92, 124.04, 1649.0], [124.04, 125.1, 123.1, 124.18, 33764.0]]), ('MSFT', '14:40', 'lower_liquidity_sweep_ratio', [[518.37, 518.76, 517.97, 518.43, 154.0], [518.01, 518.54, 517.98, 518.43, 100.0], [518.29, 518.8, 518.05, 518.65, 94.0], [518.84, 518.9, 518.44, 518.63, 96.0], [518.45, 519.78, 518.36, 519.43, 163.0], [519.43, 519.69, 518.9, 519.0, 360.0], [518.97, 519.24, 518.64, 518.64, 52.0], [518.91, 518.94, 518.04, 518.17, 147.0], [518.07, 518.87, 518.06, 518.7, 55.0], [518.7, 520.0, 517.05, 519.77, 718.0], [519.25, 522.5, 518.85, 521.87, 19158.0], [521.87, 522.4, 517.06, 517.3, 7210.0], [517.39, 517.63, 515.96, 517.17, 4231.0]])]
        for ticker, tm, expected, rows in cases:
            with self.subTest(ticker=ticker, time=tm):
                frame = pd.DataFrame(rows, columns=['open','high','low','close','volume'])
                frame['bar_et'] = pd.date_range('2026-10-02 10:00', periods=13, freq='5min', tz=alerts.ET)
                events = [alerts._wick_event(ticker, frame, 12, side, alerts._load_wick_setups(CONFIG)) for side in ('LOWER','UPPER')]
                events = [e for e in events if e is not None]
                event = max(events, key=lambda e: (e['swept_reclaimed'], e['wick_share_pct'], e['wick'])) if events else None
                self.assertEqual(event['setup_id'] if event else None, expected)
                if event and event.get('two_sided'):
                    with tempfile.TemporaryDirectory() as tmp:
                        message = alerts.prepare_alert({'alert_data':[event]}, batch_file=Path(tmp)/'batch.json')
                        self.assertIn('TWO-SIDED WICK', message)
                        self.assertNotIn('confirmation', message)

    def test_upgrade_discards_old_backlog(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'state.json'
            state.write_text(json.dumps({'schema_version':3,'pending':[{'bad':'legacy'}]}))
            events=alerts.build_wick_alerts(candles(),trade_date='2026-10-02',now='2026-10-02 16:00Z',state_file=state)
            self.assertEqual(events,[])
            self.assertEqual(json.loads(state.read_text())['schema_version'],6)


if __name__ == '__main__':
    unittest.main()
