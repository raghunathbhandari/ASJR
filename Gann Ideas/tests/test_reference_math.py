"""ASJR Gann Ideas: independent reference math tests.

These verify lecture arithmetic and date conventions, NOT execution or compilation
of TradingView Pine Script. Run: python -m unittest discover -s "Gann Ideas/tests"
"""
import calendar
import math
import unittest
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

def s9(price, degrees, side=1):
    """Square-root 180-denominator convention, exact float before tick rounding."""
    root = math.sqrt(price)
    shifted = root + side * degrees / 180.0
    if shifted <= 0:
        raise ValueError("Projected square root must be positive")
    return shifted ** 2

def factor8(high, low, step):
    assert 0 <= step <= 8
    return low + (high - low) * step / 8.0

def calendar_month_at(dt, months):
    """Calculate anniversary from the ORIGINAL anchor to prevent month drift."""
    index = dt.year * 12 + (dt.month - 1) + months
    yy, mm0 = divmod(index, 12)
    mm = mm0 + 1
    return dt.replace(year=yy, month=mm, day=min(dt.day, calendar.monthrange(yy, mm)[1]))

def next_elapsed(anchor, period, unit, now):
    steps = {"mi": timedelta(minutes=period), "hh": timedelta(hours=period), "day": timedelta(days=period)}
    delta = steps[unit]
    if now < anchor:
        return anchor
    k = (now - anchor) // delta + 1
    return anchor + k * delta

class TestSquareNine(unittest.TestCase):
    def test_169_to_225_full_turn(self):
        self.assertEqual(s9(169, 360), 225)

    def test_root_quarter_steps(self):
        known = [169, 175.5625, 182.25, 189.0625, 196, 203.0625,
                 210.25, 217.5625, 225]
        for i, target in enumerate(known):
            self.assertAlmostEqual(s9(169, i * 45), target, places=6)

    def test_anchor_529(self):
        self.assertAlmostEqual(s9(529, 90), 552.25, places=6)
        self.assertAlmostEqual(s9(529, 90, -1), 506.25, places=6)
        self.assertAlmostEqual(s9(529, 180), 576)
        self.assertAlmostEqual(s9(529, 360, -1), 441)

    def test_invalid_lower_branch(self):
        with self.assertRaises(ValueError):
            s9(1, 360, -1)

class TestFactorEight(unittest.TestCase):
    def test_photo_percentages_implied_zero_to_264(self):
        self.assertEqual(factor8(264, 0, 4), 132)
        self.assertEqual(factor8(264, 0, 5), 165)
        self.assertEqual(factor8(264, 0, 6), 198)
        self.assertAlmostEqual(264 * 2/3, 176)
        self.assertNotEqual(2/3, 5/8)

class TestCycles(unittest.TestCase):
    def test_elapsed_12_minutes(self):
        t = datetime(2026, 11, 15, 9, 30, tzinfo=UTC)
        self.assertEqual(next_elapsed(t, 12, "mi", t), t + timedelta(minutes=12))

    def test_elapsed_90_hours(self):
        t = datetime(2026, 11, 15, tzinfo=UTC)
        self.assertEqual(next_elapsed(t, 90, "hh", t), t + timedelta(hours=90))

    def test_month_end_clamping(self):
        anchor = datetime(2024, 1, 31, 9, 30, tzinfo=UTC)
        self.assertEqual(calendar_month_at(anchor, 1), datetime(2024, 2, 29, 9, 30, tzinfo=UTC))
        self.assertEqual(calendar_month_at(anchor, 2), datetime(2024, 3, 31, 9, 30, tzinfo=UTC))

    def test_feb29_year_offset(self):
        anchor = datetime(2024, 2, 29, tzinfo=UTC)
        self.assertEqual(calendar_month_at(anchor, 12), datetime(2025, 2, 28, tzinfo=UTC))
        self.assertEqual(calendar_month_at(anchor, 48), datetime(2028, 2, 29, tzinfo=UTC))

if __name__ == "__main__":
    unittest.main()
