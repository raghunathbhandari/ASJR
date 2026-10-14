"""WAP callback regression tests: use the existing IBKR app, not a new client."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

import pandas as pd

from RudraScanner.wap_capture import install_wap_capture, attach_wap


class MutatingApp:
    def __init__(self):
        self.data = {}

    def historicalData(self, req_id, bar):
        self.data.setdefault(req_id, []).append(
            (bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume))
        # Simulate a legacy EWrapper modifying the callback object.
        bar.wap = 0


def bar(stamp, wap):
    return SimpleNamespace(
        date=str(stamp), open=101.0, high=103.0, low=99.0,
        close=102.0, volume=10, wap=wap)


class TestWapCapture(unittest.TestCase):
    def test_collects_before_original_callback_mutates_bar(self):
        app = MutatingApp()
        self.assertTrue(install_wap_capture(app))
        self.assertFalse(install_wap_capture(app))
        req_id = 502
        app._rudra_wap_sidecar[req_id] = []
        t = pd.Timestamp("2026-10-14 08:00:00", tz="UTC")
        app.historicalData(req_id, bar(int(t.timestamp()), 100.5))
        self.assertEqual(len(app.data[req_id]), 1)
        parsed = pd.DataFrame({"Close": [102.0]}, index=[t])
        result = attach_wap(app, req_id, parsed, app.data[req_id])
        self.assertEqual(result["WAP"].iloc[0], 100.5)
        self.assertNotIn(req_id, app._rudra_wap_sidecar)

    def test_filtered_extra_callback_does_not_erase_valid_wap(self):
        app = MutatingApp()
        install_wap_capture(app)
        req_id = 503
        app._rudra_wap_sidecar[req_id] = []
        t = pd.Timestamp("2026-10-14 08:00:00", tz="UTC")
        app.historicalData(req_id, bar(int(t.timestamp()), 100.5))
        app.historicalData(req_id, bar("INVALID", 100.4))
        parsed = pd.DataFrame({"Close": [102.0]}, index=[t])
        result = attach_wap(app, req_id, parsed, app.data[req_id])
        self.assertEqual(result["WAP"].iloc[0], 100.5)

    def test_missing_wap_remains_missing(self):
        app = MutatingApp()
        install_wap_capture(app)
        req_id = 504
        app._rudra_wap_sidecar[req_id] = []
        t = pd.Timestamp("2026-10-14 08:00:00", tz="UTC")
        app.historicalData(req_id, bar(int(t.timestamp()), 0))
        parsed = pd.DataFrame({"Close": [102.0]}, index=[t])
        result = attach_wap(app, req_id, parsed, app.data[req_id])
        self.assertTrue(pd.isna(result["WAP"].iloc[0]))


if __name__ == "__main__":
    unittest.main()
