"""Independent OHLC reference tests for ASJR Candle Patterns v0.2.

These exercise the documented math with synthetic candle fixtures.
They do NOT compile, execute, or backtest TradingView Pine.
Run: python -m unittest discover -s "Candle Patterns/tests" -v
"""
import math
import unittest
from dataclasses import dataclass

TICK = 0.25

@dataclass(frozen=True)
class C:
    o: float
    h: float
    l: float
    c: float

    def body(self):
        return abs(self.c - self.o)

    def span(self):
        return max(self.h - self.l, TICK)

    def upper(self):
        return max(0.0, self.h - max(self.o, self.c))

    def lower(self):
        return max(0.0, min(self.o, self.c) - self.l)


def bull_engulf(p, c):
    return (c.c > c.o and c.h >= p.h and c.l <= p.l
            and (c.h > p.h or c.l < p.l))


def bear_engulf(p, c):
    return (c.c < c.o and c.h >= p.h and c.l <= p.l
            and (c.h > p.h or c.l < p.l))


def hammer(c, trend_down=True, multiplier=2.0):
    ratio = c.body()/c.span()
    loc = (c.c-c.l)/c.span()
    return (trend_down and ratio <= 0.45 and
            c.lower() >= max(c.body(), TICK) * multiplier and
            c.upper() <= c.span()*0.15 and loc >= 0.65)


def star(c, trend_up=True, multiplier=2.0):
    ratio = c.body()/c.span()
    loc = (c.c-c.l)/c.span()
    return (trend_up and ratio <= 0.45 and
            c.upper() >= max(c.body(), TICK) * multiplier and
            c.lower() <= c.span()*0.15 and loc <= 0.35)


def inside_bull(mother, inside, breakout):
    return (inside.h < mother.h and inside.l > mother.l and
            breakout.c > breakout.o and breakout.c > mother.h)


def outside_bear(p, c):
    return (c.h > p.h and c.l < p.l and c.c < c.o and
            (c.c-c.l)/c.span() <= 0.30 and p.c > p.o)


def gann_sweep(c, level, tick=TICK):
    buy = c.l <= level-tick and c.c >= level+tick
    sell = c.h >= level+tick and c.c <= level-tick
    return buy, sell


def s9(anchor, index):
    root = math.sqrt(anchor) + index*0.25
    if root <= 0:
        return None
    return root*root


class TestEngulfing(unittest.TestCase):
    def test_bull_engulf_wicks_no_body_containment(self):
        prev = C(101, 104, 99, 100)
        self.assertTrue(bull_engulf(prev, C(100.5, 105, 98, 101)))
        self.assertFalse(bull_engulf(prev, C(100.5, 103, 98, 101)))

    def test_bear_engulf_wicks_no_body_containment(self):
        prev = C(100, 104, 99, 101)
        self.assertTrue(bear_engulf(prev, C(101, 105, 98, 100.5)))
        self.assertFalse(bear_engulf(prev, C(101, 105, 100, 100.5)))

    def test_both_directions_distinguished_by_current_close(self):
        prev = C(101, 104, 99, 100)
        self.assertTrue(bull_engulf(prev, C(100, 105, 98, 102)))
        self.assertTrue(bear_engulf(prev, C(102, 105, 98, 100)))
        self.assertFalse(bull_engulf(prev, C(100, 105, 98, 100)))
        self.assertFalse(bear_engulf(prev, C(100, 105, 98, 100)))

    def test_identical_range_not_engulfing(self):
        prev = C(100, 105, 98, 101)
        self.assertFalse(bull_engulf(prev, C(100, 105, 98, 102)))
        self.assertFalse(bear_engulf(prev, C(102, 105, 98, 100)))


class TestWicks(unittest.TestCase):
    def test_hammer(self):
        c=C(101.0,101.5,97.0,101.25)
        self.assertTrue(hammer(c))
        self.assertFalse(hammer(c, trend_down=False))

    def test_shooting_star(self):
        c=C(101.0,105.0,100.75,101.25)
        self.assertTrue(star(c))
        self.assertFalse(star(c, trend_up=False))


class TestStructure(unittest.TestCase):
    def test_inside_breakout(self):
        mother=C(100,105,95,102)
        inside=C(102,103,97,101)
        self.assertTrue(inside_bull(mother, inside, C(103,107,102,106)))
        self.assertFalse(inside_bull(mother, inside, C(103,104,100,104)))

    def test_outside_bear_reversal(self):
        self.assertTrue(outside_bear(C(100,103,99,102), C(104,105,97,98)))
        self.assertFalse(outside_bear(C(100,103,99,102), C(104,105,97,104)))

    def test_reclaim_and_reject(self):
        self.assertEqual(gann_sweep(C(529,531,527,530),529),(True,False))
        self.assertEqual(gann_sweep(C(530,532,527,528),529),(False,True))
        self.assertEqual(gann_sweep(C(529,530,528,529),529),(False,False))

    def test_s9_matches_gann_ideas(self):
        self.assertAlmostEqual(s9(529, 2),552.25)
        self.assertAlmostEqual(s9(529,-2),506.25)
        self.assertAlmostEqual(s9(169,8),225.0)


if __name__ == "__main__":
    unittest.main()
