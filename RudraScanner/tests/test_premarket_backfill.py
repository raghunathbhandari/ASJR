"""No-broker concurrency tests for opt-in Rudra-Premarket backfill."""
import unittest
from datetime import timedelta
from threading import Lock
from time import sleep

import pandas as pd

from RudraScanner.premarket_backfill import PremarketBackfillQueue


def bars(ticker, days=5):
    rows = []
    for n in range(days):
        day = (pd.Timestamp("2026-09-01") + pd.Timedelta(days=n)).date()
        for minute in range(570, 960, 5):
            et = pd.Timestamp(day, tz="America/New_York") + pd.Timedelta(minutes=minute)
            rows.append({"ticker": ticker, "datetime": et, "volume": 100})
    return pd.DataFrame(rows)


class BackfillTests(unittest.TestCase):
    def test_dedup_and_store_once(self):
        fetched, stored = [], []
        def fetch(ticker):
            fetched.append(ticker)
            return bars(ticker)
        q = PremarketBackfillQueue(fetch, lambda name, df: stored.append(name))
        try:
            first = q.enqueue("INTC")
            self.assertIs(first, q.enqueue("intc"))
            self.assertEqual(first.result(timeout=3)["status"], "SAVED")
            self.assertEqual(fetched, ["INTC"])
            self.assertEqual(stored, ["INTC"])
        finally:
            q.close()

    def test_incomplete_history_is_not_saved(self):
        saved = []
        q = PremarketBackfillQueue(lambda t: bars(t, 4),
                                   lambda name, df: saved.append(name))
        try:
            self.assertEqual(q.enqueue("AKAM").result(timeout=3)["status"],
                             "INSUFFICIENT_HISTORY")
            self.assertEqual(saved, [])
        finally:
            q.close()

    def test_three_workers_but_one_broker_request(self):
        counters = {"now": 0, "max": 0}
        lock = Lock()
        def fetch(ticker):
            with lock:
                counters["now"] += 1
                counters["max"] = max(counters["max"], counters["now"])
            sleep(.01)
            with lock:
                counters["now"] -= 1
            return bars(ticker)
        names = []
        q = PremarketBackfillQueue(fetch, lambda ticker, df: names.append(ticker),
                                   workers=3, ibkr_concurrency=1)
        try:
            futures = [q.enqueue(t) for t in ("INTC", "AKAM", "WDC")]
            self.assertTrue(all(f.result(timeout=5)["saved"] for f in futures))
            self.assertEqual(counters["max"], 1)
            self.assertCountEqual(names, ["INTC", "AKAM", "WDC"])
        finally:
            q.close()

    def test_invalid_ticker_and_closed_queue(self):
        q = PremarketBackfillQueue(lambda t: bars(t), lambda t, b: None)
        try:
            with self.assertRaises(ValueError):
                q.enqueue("bad symbol")
        finally:
            q.close()
        with self.assertRaises(RuntimeError):
            q.enqueue("INTC")


if __name__ == "__main__":
    unittest.main()
