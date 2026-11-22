"""Numerical reference checks for ASJR Renko and SuperTrend v1.

These tests check intended formulas; they do not compile Pine or verify
live TradingView historical data.
"""
from decimal import Decimal, ROUND_HALF_UP
import unittest


def ticks(value, tick):
    return int((Decimal(str(value)) / Decimal(str(tick))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class TraditionalRenko:
    def __init__(self, box_size=8.33, tick=0.05, cap=80):
        self.tick = Decimal(str(tick))
        self.unit = max(1, ticks(box_size, tick))
        self.last = None
        self.direction = 0
        self.cap = cap
        self.overflows = 0

    def move(self, close):
        target = ticks(close, self.tick)
        if self.last is None:
            self.last = target
            return []
        result = []
        for _ in range(self.cap):
            up = target >= self.last + self.unit * (2 if self.direction == -1 else 1)
            down = target <= self.last - self.unit * (2 if self.direction == 1 else 1)
            if not up and not down:
                break
            start = self.last + (self.unit if self.direction == -1 else 0) if up else self.last - (self.unit if self.direction == 1 else 0)
            finish = start + self.unit if up else start - self.unit
            result.append((start * self.tick, finish * self.tick, 1 if up else -1))
            self.last, self.direction = finish, 1 if up else -1
        else:
            if target >= self.last + self.unit * (2 if self.direction == -1 else 1) or target <= self.last - self.unit * (2 if self.direction == 1 else 1):
                self.overflows += 1
        return result


class BrickATR:
    def __init__(self, length=14):
        self.length = length
        self.count = 0
        self.seed = Decimal("0")
        self.atr = None
        self.previous_close = None

    def move(self, open_, close):
        high, low = max(open_, close), min(open_, close)
        prior = self.previous_close
        tr = high - low if prior is None else max(high - low, abs(high - prior), abs(low - prior))
        self.previous_close = close
        self.count += 1
        if self.count <= self.length:
            self.seed += tr
            if self.count == self.length:
                self.atr = self.seed / self.length
        else:
            self.atr = (self.atr * (self.length - 1) + tr) / self.length
        return self.atr


class TestTraditionalRenko(unittest.TestCase):
    def test_nifty_833_rounds_to_835(self):
        r = TraditionalRenko()
        self.assertEqual(r.unit, 167)
        self.assertEqual(r.unit * r.tick, Decimal("8.35"))

    def test_cent_tick_keeps_833(self):
        r = TraditionalRenko(tick=0.01)
        self.assertEqual(r.unit * r.tick, Decimal("8.33"))

    def test_initial_anchor_and_one_brick(self):
        r = TraditionalRenko()
        self.assertEqual(r.move(100), [])
        self.assertEqual(r.move(108.30), [])
        self.assertEqual(r.move(108.35), [(Decimal("100.00"), Decimal("108.35"), 1)])

    def test_reversal_requires_two_box_distance(self):
        r = TraditionalRenko()
        r.move(100)
        r.move(108.35)
        self.assertEqual(r.move(91.70), [])
        self.assertEqual(r.move(91.65), [(Decimal("100.00"), Decimal("91.65"), -1)])

    def test_many_bricks_from_one_close(self):
        r = TraditionalRenko()
        r.move(100)
        b = r.move(125.05)
        self.assertEqual(len(b), 3)
        self.assertEqual(b[-1], (Decimal("116.70"), Decimal("125.05"), 1))

    def test_close_only_does_not_infer_wicks(self):
        r = TraditionalRenko()
        r.move(100)
        self.assertEqual(r.move(100), [])

    def test_overflow_is_detected(self):
        r = TraditionalRenko(cap=2)
        r.move(100)
        self.assertEqual(len(r.move(200)), 2)
        self.assertEqual(r.overflows, 1)

    def test_atr_seeds_after_fourteen_bricks(self):
        r, a = TraditionalRenko(), BrickATR(14)
        r.move(100)
        bricks = r.move(216.90)
        self.assertEqual(len(bricks), 14)
        for j, (o, c, _) in enumerate(bricks):
            v = a.move(o, c)
            if j < 13:
                self.assertIsNone(v)
        self.assertEqual(a.atr, Decimal("8.35"))

    def test_reversal_true_range_includes_gap(self):
        r, a = TraditionalRenko(), BrickATR(1)
        r.move(100)
        up = r.move(108.35)[0]
        dn = r.move(91.65)[0]
        self.assertEqual(a.move(up[0], up[1]), Decimal("8.35"))
        self.assertEqual(a.move(dn[0], dn[1]), Decimal("16.70"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
