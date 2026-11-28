import importlib
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

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
