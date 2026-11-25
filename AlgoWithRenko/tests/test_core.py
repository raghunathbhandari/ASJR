"""Small offline checks for the research engine."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backtest import Bar, indicators, renko_events, run_backtest, summarize

UTC = timezone.utc

def samples(closes):
    base = datetime(2026, 1, 5, tzinfo=UTC)
    out = []
    for index, price in enumerate(closes):
        t = base + timedelta(minutes=15 * index)
        v = [(t + timedelta(minutes=5 * j), price, price + 1, price - 1, price) for j in range(3)]
        out.append(Bar(t, price, price + 1, price - 1, price, v))
    return out

class EngineTests(unittest.TestCase):
    def test_two_brick_reversal_and_confirmed_second(self):
        bars = samples([100, 120, 140, 100, 80, 60])
        events, count = renko_events(bars, 20)
        self.assertEqual(count, 5)
        self.assertEqual([(x['c'], x['reverse']) for x in events[3]], [(100, True)])
        self.assertEqual(events[4][0]['run'], 2)
        self.assertEqual(events[4][0]['d'], -1)

    def test_indicator_warmup(self):
        rsi, adx = indicators(samples([100] * 35))
        self.assertIsNone(rsi[13])
        self.assertIsNotNone(rsi[14])
        self.assertIsNone(adx[26])
        self.assertIsNotNone(adx[27])

    def test_monthly_summary_drawdown(self):
        rows = [{'entry_time': '2026-09-11T12:00:00+00:00', 'points': -26},
                {'entry_time': '2026-09-20T12:00:00+00:00', 'points': 12.5},
                {'entry_time': '2026-10-01T12:00:00+00:00', 'points': 100}]
        s = summarize(rows, '2026-09')
        self.assertEqual(s['trades'], 2)
        self.assertEqual(s['net_mes_points'], -13.5)
        self.assertEqual(s['max_closed_trade_drawdown_pts'], 26)

    def test_no_entries_when_unconfirmed(self):
        bars = samples([100, 120, 100, 120, 100, 120, 100])
        trades, _ = run_backtest(bars, brick=20, stop=20, entry_brick=2,
                                  chop_screen=True, filter_mode='none')
        self.assertEqual(trades, [])

if __name__ == '__main__':
    unittest.main()
