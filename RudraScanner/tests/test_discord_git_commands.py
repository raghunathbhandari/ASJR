"""Offline safety tests of Git commands mapped to the user's existing Discord bot.

No real git push/pull or network interaction. All subprocess calls mocked.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
ANALYST = ROOT / "ASJR_Analyst"
if str(ANALYST) not in sys.path:
    sys.path.insert(0, str(ANALYST))
from Utils import discord_git_commands as gitbot


def cp(out="", code=0, err=""):
    return CompletedProcess(["git"], code, out, err)


class DiscordGitTests(unittest.TestCase):
    def _invoke(self, cmd, results, author="42"):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(gitbot, "_run", side_effect=results) as fake:
                text = gitbot.handle_git_command(
                    cmd, author, repo_root=root, allowed_ids={"42"}
                )
                calls = [a.args[1:] for a in fake.call_args_list]
            return text, calls

    def test_no_allowlist_means_no_git_actions(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(gitbot.os.environ,
                            {gitbot.ALLOWED_IDS_ENV: ""}):
                with patch.object(gitbot, "_run") as fake:
                    result = gitbot.gitpull("42", repo_root=folder)
            self.assertIn("DENIED", result)
            fake.assert_not_called()

    def test_unauthorized_author_denied(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(gitbot, "_run") as fake:
                result = gitbot.gitpush(
                    "88", repo_root=folder, allowed_ids={"42"}
                )
            self.assertIn("DENIED", result)
            fake.assert_not_called()

    def test_arbitrary_shell_command_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(gitbot, "_run") as fake:
                result = gitbot.handle_git_command(
                    "!gitpull; rm -rf /", "42",
                    repo_root=folder, allowed_ids={"42"}
                )
            self.assertIn("UNKNOWN", result)
            fake.assert_not_called()

    def test_gitpull_calls_only_fixed_git_argv(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            answers = [
                cp(str(root)), cp("main"), cp("git@github.com:raghunathbhandari/ASJR.git"),
                cp("f123abc"), cp(""), cp("fast-forward"), cp("f123abd"),
            ]
            with patch.object(gitbot, "_run", side_effect=answers) as fake:
                result = gitbot.gitpull("42", repo_root=root, allowed_ids={"42"})
                ops = [x.args[1:] for x in fake.call_args_list]
            self.assertIn("PULL UPDATED", result)
            self.assertIn(("pull", "--ff-only", "origin", "main"), ops)
            self.assertNotIn(("reset", "--hard"), ops)

    def test_dirty_checkout_blocks_pull(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            answers = [
                cp(str(root)), cp("main"),
                cp("https://github.com/raghunathbhandari/ASJR.git"),
                cp("f123abc"), cp(" M ASJR_Analyst/DataLake/log.csv"),
            ]
            with patch.object(gitbot, "_run", side_effect=answers) as fake:
                result = gitbot.gitpull("42", repo_root=root, allowed_ids={"42"})
                ops = [x.args[1:] for x in fake.call_args_list]
            self.assertIn("REFUSED", result)
            self.assertNotIn(("pull", "--ff-only", "origin", "main"), ops)

    def test_gitpush_does_not_add_or_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            answers = [
                cp(str(root)), cp("main"),
                cp("https://github.com/raghunathbhandari/ASJR"),
                cp("f123abc"), cp("", 0, "Everything up-to-date"),
            ]
            with patch.object(gitbot, "_run", side_effect=answers) as fake:
                result = gitbot.gitpush("42", repo_root=root, allowed_ids={"42"})
                ops = [x.args[1:] for x in fake.call_args_list]
            self.assertIn("PUSH SUCCESS", result)
            self.assertIn(("push", "origin", "main"), ops)
            self.assertFalse(any(op[0] in ("add", "commit") for op in ops))

    def test_nonmain_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(gitbot, "_run", side_effect=[
                cp(str(root)), cp("feature")
            ]) as fake:
                result = gitbot.gitpush("42", repo_root=root, allowed_ids={"42"})
            self.assertIn("checkout must be on main", result)
            self.assertEqual(fake.call_count, 2)

    def test_wrong_remote_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(gitbot, "_run", side_effect=[
                cp(str(root)), cp("main"), cp("git@github.com:someone/evil.git")
            ]) as fake:
                result = gitbot.gitpush("42", repo_root=root, allowed_ids={"42"})
            self.assertIn("REFUSED", result)
            self.assertEqual(fake.call_count, 3)

    def test_push_failure_returns_failure_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            answers = [
                cp(str(root)), cp("main"),
                cp("git@github.com:raghunathbhandari/ASJR.git"),
                cp("f123abc"), cp("", 1, "non-fast-forward rejected"),
            ]
            with patch.object(gitbot, "_run", side_effect=answers):
                result = gitbot.gitpush("42", repo_root=root, allowed_ids={"42"})
            self.assertIn("PUSH FAILED", result)
            self.assertIn("non-fast-forward", result)

    def test_remote_validator_accepts_only_asjr(self):
        self.assertTrue(gitbot._correct_origin("git@github.com:raghunathbhandari/ASJR.git"))
        self.assertTrue(gitbot._correct_origin("https://github.com/raghunathbhandari/ASJR"))
        self.assertFalse(gitbot._correct_origin("https://github.com/other/repo.git"))
        self.assertFalse(gitbot._correct_origin("git@evil.com:raghunathbhandari/ASJR.git"))


if __name__ == "__main__":
    unittest.main()
