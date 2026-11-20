"""Real Git integration tests with only local, disposable remotes (no VPS/network)."""
import fcntl
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from ASJR_Analyst.Utils import asjr_git as daily, discord_git_commands as commands
from RudraScanner import git_safe_sync as safe, research_bridge_worker as bridge


def g(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                          check=True).stdout.strip()


class LocalRemote(unittest.TestCase):
    job = "research-1795160000001"
    day = "2026-11-10"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.server = self.root / "origin.git"
        self.writer = self.root / "writer"
        self.live = self.root / "live"
        g(self.root, "init", "-q", "--bare", "-b", "main", str(self.server))
        g(self.root, "clone", "-q", str(self.server), str(self.writer))
        self.req = f"{bridge.REQ_DIR}/{self.job}.json"
        self.res = f"{bridge.RESULT_DIR}/{self.job}.json"
        obj = {"id": self.job, "operation": "health_check", "batch": None, "schema_version": 1}
        self.change(self.req, json.dumps(obj))
        self.change(".gitignore", "ignored-runtime\n")
        self.change("RudraScanner/scan_now.py", "# fixture only\n")
        self.push()
        g(self.root, "clone", "-q", self.server.as_uri(), str(self.live))
        self.base = g(self.live, "rev-parse", "HEAD")
        self.oid = g(self.live, "rev-parse", "HEAD:" + self.req)
        self.day_dir = self.live / "ASJR_Analyst" / "DataLake" / self.day
        self.day_dir.mkdir(parents=True)
        self.output = self.day_dir / "output.csv"
        self.output.write_text("ticker,volume\nTEST,3\n")
        (self.live / "ignored-runtime").write_text("operator data\n")
        (self.live / ".git/FETCH_HEAD").write_text("another process owns this file\n")
        self.enter(patch.object(bridge, "REPO", self.live))
        self.enter(patch.object(bridge, "origin_ok", side_effect=lambda u: u == self.server.as_uri()))
        self.enter(patch.object(daily.time, "sleep"))

    def enter(self, ctx):
        val = ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        return val

    def change(self, path, text, *, force_add=False):
        dest = self.writer / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        g(self.writer, "add", *(["-f"] if force_add else []), "--", path)

    def push(self):
        g(self.writer, "-c", "user.name=Test", "-c", "user.email=test@localhost",
          "commit", "-qm", "Fixture update")
        g(self.writer, "push", "-q", "origin", "HEAD:refs/heads/main")
        return g(self.writer, "rev-parse", "HEAD")

    def head(self):
        return g(self.server, "rev-parse", "refs/heads/main")

    def assert_live_untouched(self):
        self.assertEqual(g(self.live, "rev-parse", "HEAD"), self.base)
        self.assertEqual((self.live / ".git/FETCH_HEAD").read_text(), "another process owns this file\n")
        self.assertEqual((self.live / "ignored-runtime").read_text(), "operator data\n")
        self.assertTrue(self.output.is_file())
        self.assertEqual(g(self.live, "diff", "--cached", "--name-only"), "")

    def submit(self):
        return daily.submit_datalake(self.day, self.day_dir, [self.output])

    def test_bridge_round_trip_and_second_tick_noop(self):
        with patch.object(bridge, "run_job", wraps=bridge.run_job) as jobs:
            self.assertEqual(bridge.tick(), 0)
            commit = self.head()
            self.assertNotEqual(commit, self.base)
            report = json.loads(g(self.server, "show", "main:" + self.res))
            self.assertEqual((report["status"], report["request_main"], report["checkout_head"]),
                             ("SUCCESS", self.base, self.base))
            self.assertEqual(report["worker_sync_version"], bridge.SYNC_VERSION)
            self.assertEqual(bridge.tick(), 0)
            self.assertEqual(self.head(), commit)
            jobs.assert_called_once()
        self.assertEqual(g(self.server, "diff", "--name-only", self.base, commit), self.res)
        self.assert_live_untouched()

    def test_push_failure_retries_saved_report_not_job(self):
        with patch.object(bridge, "run_job", wraps=bridge.run_job) as jobs:
            with patch.object(bridge, "publish", return_value=(False, "UNCONFIRMED")):
                self.assertEqual(bridge.tick(), 2)
            pending = self.live / ".git/asjr-research-bridge" / (self.job + ".json")
            saved = json.loads(pending.read_text())["report"]
            self.assertEqual(bridge.tick(), 0)
            self.assertEqual(json.loads(g(self.server, "show", "main:" + self.res)), saved)
            jobs.assert_called_once()
            self.assertFalse(pending.exists())
        self.assert_live_untouched()

    def test_concurrent_worker_wins_no_second_result_commit(self):
        real, heads = bridge.git, []
        def race(*args, **kw):
            if args[0] == "push" and not heads:
                self.change(self.res, '{"id":"first-durable-result"}\n')
                heads.append(self.push())
            return real(*args, **kw)
        with patch.object(bridge, "git", side_effect=race):
            self.assertEqual(bridge.publish(self.job, {"id":"loser"}, self.oid),
                             (True, "ALREADY_PUBLISHED"))
        self.assertEqual(self.head(), heads[0])
        self.assertEqual(json.loads(g(self.server, "show", "main:" + self.res))["id"],
                         "first-durable-result")
        self.assert_live_untouched()

    def test_unrelated_concurrent_commit_preserved_as_parent(self):
        real, heads = bridge.git, []
        def race(*args, **kw):
            if args[0] == "push" and not heads:
                self.change("operator.txt", "do not discard")
                heads.append(self.push())
            return real(*args, **kw)
        with patch.object(bridge, "git", side_effect=race):
            self.assertEqual(bridge.tick(), 0)
        self.assertEqual(g(self.server, "rev-parse", "main^"), heads[0])
        self.assertEqual(g(self.server, "show", "main:operator.txt"), "do not discard")

    def test_failed_result_tree_read_never_executes_jobs(self):
        actual=bridge.tree_rows
        def failed(folder, sha, *paths):
            if bridge.RESULT_DIR + "/" in paths:
                raise RuntimeError("unreadable result tree")
            return actual(folder, sha, *paths)
        with patch.object(bridge, "tree_rows", side_effect=failed), patch.object(bridge, "run_job") as jobs:
            with self.assertRaisesRegex(RuntimeError, "unreadable"):
                bridge.tick()
            jobs.assert_not_called()
        self.assertEqual(self.head(), self.base)

    def test_once_and_service_use_same_lock(self):
        lockpath = self.live / ".git/asjr-research-bridge/worker.lock"
        lockpath.parent.mkdir()
        with lockpath.open("a") as lock, patch.object(bridge, "run_job") as jobs:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(bridge.tick(), 0)
            jobs.assert_not_called()
        self.assert_live_untouched()

    def test_replaced_request_never_receives_old_result(self):
        self.change(self.req, "null\n")
        new = self.push()
        self.assertEqual(bridge.publish(self.job, {"id":self.job}, self.oid),
                         (False, "REQUEST_CHANGED"))
        self.assertEqual(self.head(), new)

    def test_daily_publishes_then_noop_only_day_changed(self):
        result = self.submit()
        self.assertEqual(result["status"], "PUSHED")
        self.assertEqual(result["commit_sha"], self.head())
        self.assertEqual(g(self.server, "diff", "--name-only", self.base, self.head()),
                         self.output.relative_to(self.live).as_posix())
        self.assertEqual(self.submit()["status"], "NO_CHANGES")
        self.assert_live_untouched()

    def race_daily(self, path):
        real, heads = daily._git, []
        def race(folder, *args, **kw):
            if args[0] == "push" and not heads:
                self.change(path, "operator wins\n")
                heads.append(self.push())
            return real(folder, *args, **kw)
        with patch.object(daily, "_git", side_effect=race):
            result = self.submit()
        return result, heads[0]

    def test_daily_retries_unrelated_writer(self):
        result, parent = self.race_daily("other.txt")
        self.assertEqual(result["status"], "PUSHED")
        self.assertEqual(g(self.server, "rev-parse", "main^"), parent)
        self.assert_live_untouched()

    def test_daily_same_day_conflict_keeps_both_copies(self):
        path = self.output.relative_to(self.live).as_posix()
        result, parent = self.race_daily(path)
        self.assertEqual(result["status"], "PENDING")
        self.assertEqual(self.head(), parent)
        self.assertEqual(g(self.server, "show", "main:" + path), "operator wins")
        self.assertIn("TEST,3", self.output.read_text())

    def test_daily_detects_writer_during_snapshot_copy(self):
        original = daily.shutil.copytree
        remote_path = self.output.relative_to(self.live).as_posix()
        def overlap(src, dest, *args, **kw):
            if src == self.day_dir:
                self.change(remote_path, "new remote data\n")
                self.push()
            return original(src, dest, *args, **kw)
        with patch.object(daily.shutil, "copytree", side_effect=overlap):
            self.assertEqual(self.submit()["status"], "PENDING")
        self.assertEqual(g(self.server, "show", "main:" + remote_path), "new remote data")
        self.assert_live_untouched()

    def test_clone_failure_and_timeout_are_pending_without_credential_leak(self):
        real = daily._git
        token = "test-only-secret"
        for err in (daily._git_error("clone", subprocess.CompletedProcess(
                [], 128, "", "authentication failed for https://"+token+"@github.com")),
                subprocess.TimeoutExpired(["git","clone",token], 5)):
            def fail(folder, *args, **kw):
                if args[0]=="clone":
                    raise err
                return real(folder, *args, **kw)
            with patch.object(daily, "_git", side_effect=fail):
                result = self.submit()
            self.assertEqual(result["status"], "PENDING")
            self.assertNotIn(token, str(result))

    def test_daily_rejects_symlink_instead_of_uploading_local_state(self):
        (self.day_dir / "external.csv").symlink_to(self.live / "ignored-runtime")
        self.assertEqual(self.submit()["status"], "PENDING")
        self.assertEqual(self.head(), self.base)

    def test_safe_sync_updates_detached_worktree_not_live(self):
        research=self.root / "research"
        with patch.object(safe,"LIVE",self.live),patch.object(safe,"RESEARCH",research):
            self.assertEqual(safe.main(), 0)
            self.change("new.md","another branch update")
            tip=self.push()
            self.assertEqual(safe.main(), 0)
            self.assertEqual(g(research, "rev-parse","HEAD"), tip)
            (research / "operator.raw").write_text("preserve me")
            self.assertEqual(safe.main(), 2)
        self.assert_live_untouched()

    def test_live_ff_pull_ignores_foreign_fetch_head_but_preserves_ignored_file(self):
        with patch.object(commands, "_correct_origin", return_value=True):
            self.change("new.md","allowed")
            tip=self.push()
            self.assertIn("PULL UPDATED", commands.gitpull("1",repo_root=self.live,allowed_ids={"1"}))
            self.assertEqual(g(self.live,"rev-parse","HEAD"), tip)
            self.change("ignored-runtime","incoming tracked data\n",force_add=True)
            self.push()
            self.assertIn("FAILED", commands.gitpull("1",repo_root=self.live,allowed_ids={"1"}))
        self.assertEqual(g(self.live,"rev-parse","HEAD"), tip)
        self.assertEqual((self.live / "ignored-runtime").read_text(),"operator data\n")
        self.assertEqual((self.live / ".git/FETCH_HEAD").read_text(),"another process owns this file\n")

    def test_reject_policy_is_not_a_race(self):
        result=subprocess.CompletedProcess([],1,
            "!\tHEAD:refs/heads/main\t[remote rejected] (protected branch hook declined)\n","")
        self.assertFalse(bridge.race_rejection(result))
        result.stderr = ("remote: cannot lock ref 'refs/heads/main': is at " +
                         "a"*40 + " but expected " + "b"*40)
        self.assertTrue(bridge.race_rejection(result))


if __name__ == "__main__":
    unittest.main()
