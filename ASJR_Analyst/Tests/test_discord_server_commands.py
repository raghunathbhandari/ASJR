"""Offline authorization and command parsing tests (no VPS execution)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ASJR_Analyst.Utils import discord_server_commands as c


USER = "123456789"
CHANNEL = "567"
GUILD = "890"


class TestDiscordServerCommands(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        # !runSCommand tests already owns the production flock. Offline
        # authorization tests must never contend with its live lock.
        self.lock_patch = patch.object(c, "LOCK_PATH", self.root / "test_scommand.lock")
        self.lock_patch.start()
        self.addCleanup(self.lock_patch.stop)
        (self.root / "ASJR_Analyst" / "DataLake").mkdir(parents=True)
        self.kw = {
            "is_admin": True, "guild_id": GUILD, "channel_id": CHANNEL,
            "repo_root": self.root, "allowed_ids": {USER},
            "allowed_channels": {CHANNEL},
        }

    def tearDown(self):
        self.temp.cleanup()

    def run_command(self, text, user=USER, **updates):
        kw = dict(self.kw)
        kw.update(updates)
        return c.run_scommand(text, user, **kw)

    @patch.object(c, "_run")
    def test_requires_explicit_user_id(self, shell):
        self.assertIn("DENIED", self.run_command("!runSCommand version", "999"))
        shell.assert_not_called()

    @patch.object(c, "_run")
    def test_requires_administrator_permission(self, shell):
        self.assertIn("DENIED", self.run_command(
            "!runSCommand version", is_admin=False))
        shell.assert_not_called()

    @patch.object(c, "_run")
    def test_fails_closed_in_dm(self, shell):
        self.assertIn("DENIED", self.run_command(
            "!runSCommand version", guild_id=None))
        shell.assert_not_called()

    @patch.object(c, "_run")
    def test_channel_lock(self, shell):
        self.assertIn("DENIED", self.run_command(
            "!runSCommand version", channel_id="unapproved"))
        shell.assert_not_called()

    @patch.object(c, "_run")
    def test_shell_injection_and_arbitrary_script_denied(self, shell):
        for payload in (
            "!runSCommand bash -c id",
            "!runSCommand sudo",
            "!runSCommand version; rm -rf /",
            "!runSCommand tests && rm -rf /",
            "!runSCommand logs ../../etc/passwd",
            "!runSCommand rvol --repo /tmp",
            "!runSCommand python -c print(1)",
        ):
            with self.subTest(payload=payload):
                self.assertIn("DENIED", self.run_command(payload))
        shell.assert_not_called()

    @patch.object(c, "_run", return_value=(0, "clean"))
    def test_allowed_git_status_fixed_argv(self, shell):
        result = self.run_command("!runSCommand git")
        self.assertIn("exit=0", result)
        argv = shell.call_args.args[0]
        self.assertEqual(argv, ["git", "status", "--short", "--untracked-files=no"])

    @patch.object(c, "_run", return_value=(0, "OK"))
    def test_only_fixed_rvol_script(self, shell):
        self.assertIn("exit=0", self.run_command("!runSCommand rvol"))
        argv = shell.call_args.args[0]
        self.assertEqual(argv[-2:], ["RudraScanner/scan_now.py", "--rvol-status"])

    @patch.object(c, "_run", return_value=(0, ""))
    def test_tmux_status(self, shell):
        self.assertIn("RUNNING", self.run_command("!runSCommand bot"))
        self.assertEqual(shell.call_args.args[0],
                         ["tmux", "has-session", "-t", "trading_bot"])

    def test_logs_redact_secrets_and_reject_overlarge_count(self):
        day = self.root / "ASJR_Analyst" / "DataLake" / "2026-10-14"
        reports = day / "reports"
        reports.mkdir(parents=True)
        (reports / "asjr_pipeline_20261014_120000_BST.log").write_text(
            "RUDRA-PREMARKET | WAP ready\n"
            "DISCORD_TOKEN=do-not-disclose\n"
            "ERROR | timeout\n", encoding="utf-8")
        r = self.run_command("!runSCommand logs all 10")
        self.assertIn("WAP ready", r)
        self.assertNotIn("do-not-disclose", r)
        self.assertIn("[redacted sensitive line]", r)
        self.assertIn("DENIED", self.run_command("!runSCommand logs all 999"))

    def test_list_only_permitted_subfolder(self):
        self.assertIn("USAGE", self.run_command(
            "!runSCommand files private"))
        state = self.root / "ASJR_Analyst" / "state"
        state.mkdir()
        (state / "state.json").write_text("{}")
        self.assertIn("state.json", self.run_command(
            "!runSCommand files state"))

    def test_empty_id_allowlist_denied(self):
        self.assertIn("DENIED", self.run_command(
            "!runSCommand help", allowed_ids=set()))

    def test_generic_command_help(self):
        self.assertIn("Read-only", self.run_command("!runSCommand help"))


if __name__ == "__main__":
    unittest.main()
