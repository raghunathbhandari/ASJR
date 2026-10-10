"""Deterministic symmetric LONG and SHORT tests for all five research setups."""
import unittest
import pandas as pd

from RudraScanner.patterns import PatternSettings, _technical_patterns


CONF = PatternSettings(enabled_for_research=True)


def standard():
    rows = []
    for i in range(20):
        price = 100.0
        rows.append({
            "open": price - .05, "high": price + .3,
            "low": price - .3, "close": price,
            "ema9": 99.8, "vwap": 99.7, "volume": 1000,
            "relative_volume_12bar": 1.0, "ema9_slope5_pct": .30,
            "vwap_ready": True,
        })
    rows[-1]["relative_volume_12bar"] = 2.0
    return pd.DataFrame(rows)


def mirrored_short(long_frame):
    """Price mirror reverses every directional comparison consistently."""
    out = long_frame.copy()
    out["open"] = 200.0 - long_frame["open"]
    out["high"] = 200.0 - long_frame["low"]
    out["low"] = 200.0 - long_frame["high"]
    for key in ("close", "ema9", "vwap"):
        out[key] = 200.0 - long_frame[key]
    out["ema9_slope5_pct"] = -long_frame["ema9_slope5_pct"]
    return out


class SymmetricPatternTests(unittest.TestCase):
    def assert_both(self, dataframe, pattern):
        a = _technical_patterns(dataframe, "LONG", CONF)
        b = _technical_patterns(mirrored_short(dataframe), "SHORT", CONF)
        self.assertIn(pattern, a, f"LONG {pattern}: {a}")
        self.assertIn(pattern, b, f"SHORT {pattern}: {b}")

    def test_hitchhiker_continuation_break_both_sides(self):
        df = standard()
        df.loc[16, ["close", "high"]] = [100.0, 100.3]
        df.loc[17, ["close", "high"]] = [100.05, 100.3]
        df.loc[18, ["close", "high"]] = [100.1, 100.3]
        df.loc[19, ["open", "close", "high", "low", "ema9", "vwap"]] = [
            100.4, 101.0, 101.2, 100.3, 100.6, 100.4
        ]
        self.assert_both(df, "HITCHHIKER")

    def test_backside_reclaims_ema_toward_vwap_both_sides(self):
        df = standard()
        df.loc[18, ["close", "high", "ema9"]] = [100, 100.5, 101]
        df.loc[19, ["open", "close", "high", "low", "ema9", "vwap"]] = [
            100.8, 101.5, 101.7, 100.5, 101, 102
        ]
        self.assert_both(df, "BACK$IDE")

    def test_rubberband_snapback_from_extension_both_sides(self):
        df = standard()
        df.loc[18, ["open", "close", "high", "low", "ema9"]] = [97.2, 97, 97.5, 96.8, 100]
        df.loc[19, ["open", "close", "high", "low", "ema9", "vwap"]] = [
            98.0, 100.2, 100.4, 97.7, 99.8, 100.1
        ]
        self.assert_both(df, "RUBBERBAND")

    def test_second_chance_retest_both_sides(self):
        df = standard()
        df.loc[17, ["open", "close", "high", "low"]] = [
            100.6, 101.0, 101.4, 100.5
        ]
        df.loc[18, ["open", "close", "high", "low"]] = [
            100.9, 100.7, 101.0, 100.45
        ]
        df.loc[19, ["open", "close", "high", "low", "ema9", "vwap"]] = [
            100.9, 101.8, 102.0, 100.7, 101.1, 101.0
        ]
        self.assert_both(df, "SECOND CHANCE")

    def test_fashionably_late_ema_vwap_cross_both_sides(self):
        df = standard()
        df.loc[18, ["open", "close", "high", "ema9", "vwap"]] = [100.1, 100.5, 100.8, 100.2, 100.8]
        df.loc[19, ["open", "close", "high", "low", "ema9", "vwap"]] = [
            100.7, 101.5, 101.7, 100.4, 101.1, 100.9
        ]
        self.assert_both(df, "FASHIONABLY LATE")


if __name__ == "__main__":
    unittest.main()
