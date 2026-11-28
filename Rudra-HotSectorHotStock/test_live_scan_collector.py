import importlib
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch
import sys
import json
import csv
import io

m = importlib.import_module("Rudra-HotSectorHotStock.live_scan_collector")


class Tests(unittest.TestCase):
    def test_scope_and_calendar(self):
        self.assertEqual(len(m.CODES), 8)
        self.assertEqual(len(m.SECTORS), 12)
        dt = lambda s: datetime.fromisoformat(s)
        self.assertIsNone(m.session_slot(dt("2026-11-30T14:34:59+00:00")))
        slot, close = m.session_slot(dt("2026-11-30T14:35:00+00:00"))
        self.assertEqual(slot.strftime("%H:%M"), "09:35")
        self.assertEqual(close.hour, 16)
        self.assertIsNone(m.session_slot(dt("2026-12-25T15:00:00+00:00")))
        self.assertEqual(m.session_slot(dt("2026-12-24T18:00:00+00:00"))[1].hour, 13)
        self.assertIsNone(m.session_slot(dt("2026-12-24T18:05:00+00:00")))
        self.assertEqual(m.session_slot(dt("2027-03-15T13:35:00+00:00"))[0].hour, 9)

    def test_capture_rank_and_error(self):
        calls = []
        app = SimpleNamespace(scannerData=lambda *a: calls.append(a), error=lambda *a: calls.append(a))
        cap = m.Capture(app)
        cap.request(123, "MOST_ACTIVE")
        contract = SimpleNamespace(symbol="AMD", conId=1, exchange="SMART")
        app.scannerData(123, 4, SimpleNamespace(contract=contract), "", "", "", "")
        app.error(123, 165, "No other data")
        app.scannerDataEnd(123)
        req = cap.finish(123)
        self.assertEqual(req["rows"][5]["ticker"], "AMD")
        self.assertEqual(m.state(req), "SUCCESS_WITH_WARNINGS")
        app.scannerData(123, 0, SimpleNamespace(contract=contract), "", "", "", "")
        self.assertEqual(calls, [])
        app.error(99, 321, "other")
        self.assertEqual(len(calls), 1)

    def test_collect_exact_sector_bar_and_all_native_scans(self):
        fixed = datetime.fromisoformat("2026-11-30T14:36:00+00:00")
        slot, close = m.session_slot(fixed)
        app = SimpleNamespace(next_id=0)
        def alloc(a):
            a.next_id += 1
            return a.next_id
        def params():
            app.scannerParameters("<Root>" + "".join("<scanCode>"+c+"</scanCode>" for c in m.CODES) + "</Root>")
        def scan(rid, sub, options, filters):
            self.assertEqual(sub.numberOfRows, 50)
            self.assertEqual(filters, [])
            contract = SimpleNamespace(symbol="TEST", conId=123, exchange="SMART")
            app.scannerData(rid, 2, SimpleNamespace(contract=contract), "", "", "", "")
            app.scannerDataEnd(rid)
        def historical(rid, contract, end, duration, size, what, rth, fmt, update, opts):
            self.assertEqual((size, rth, fmt), ("5 mins", 1, 2))
            t = int(slot.timestamp()) - 300
            app.historicalData(rid, SimpleNamespace(date=str(t), open=100, high=103, low=99, close=102, volume=25))
            # A still-forming bar must not enter the archive.
            app.historicalData(rid, SimpleNamespace(date=str(t+300), open=102, high=105, low=100, close=104, volume=30))
            app.historicalDataEnd(rid, "", "")
        app.reqScannerParameters = params
        app.reqScannerSubscription = scan
        app.reqHistoricalData = historical
        app.cancelScannerSubscription = lambda rid: None
        app.cancelHistoricalData = lambda rid: None
        analyst = ModuleType("ASJR_Analyst")
        utils = ModuleType("ASJR_Analyst.Utils")
        utils.asjr_ibkr = SimpleNamespace(_next_req_id=alloc, stock_contract=lambda s:s)
        api = ModuleType("ibapi")
        scanner = ModuleType("ibapi.scanner")
        scanner.ScannerSubscription = SimpleNamespace
        with patch.dict(sys.modules, {"ASJR_Analyst":analyst, "ASJR_Analyst.Utils":utils,
                                      "ibapi":api, "ibapi.scanner":scanner}), patch.object(m, "now", return_value=fixed):
            files, n, b, e = m.collect(app, slot, close)
        self.assertEqual((n,b,e), (8,12,0))
        self.assertEqual({r["scan_code"] for r in csv.DictReader(io.StringIO(files["ibkr_scan_results.csv"]))}, set(m.CODES))
        rows = list(csv.DictReader(io.StringIO(files["sector_5m.csv"])))
        self.assertTrue(all(r["close"] == "102.0" for r in rows))
        self.assertEqual(len({r["ticker"] for r in rows}), 12)
        self.assertIn("scanner_parameters.xml", files)
        self.assertEqual(files["errors.log"], "")

    def test_bundle_immutable(self):
        with tempfile.TemporaryDirectory() as td:
            spool = Path(td)
            rel = Path("2026-11-30/0935_ET")
            self.assertTrue(m.bundle(spool, rel, {"errors.log":"first"}))
            self.assertFalse(m.bundle(spool, rel, {"errors.log":"second"}))
            self.assertEqual((spool/"rounds"/rel/"errors.log").read_text(), "first")

    def test_publish_local_remote(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root/"repo"; repo.mkdir()
            remote = root/"remote.git"; remote.mkdir()
            spool = root/"spool"; spool.mkdir()
            m.git(remote, "init", "--bare")
            m.git(repo, "init", "-b", "main")
            (repo/"keep.txt").write_text("keep")
            m.git(repo, "add", "keep.txt")
            m.git(repo, "-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-m", "base")
            m.git(repo, "remote", "add", "origin", str(remote))
            m.git(repo, "push", "origin", "main")
            rel = Path("2026-11-30/0935_ET")
            m.bundle(spool, rel, {"errors.log":"first"})
            self.assertTrue(m.publish(repo, spool, budget=40).startswith("PUSHED"))
            self.assertEqual(m.git(remote, "show", "main:"+str(m.ARCHIVE/rel/"errors.log")), "first")
            self.assertEqual(m.git(remote, "show", "main:keep.txt"), "keep")
            self.assertEqual(m.publish(repo, spool), "NO_PENDING")
            self.assertFalse((repo/m.ARCHIVE).exists())


if __name__ == "__main__":
    unittest.main()
