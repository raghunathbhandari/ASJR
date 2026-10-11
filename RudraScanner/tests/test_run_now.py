"""Offline one-shot full Chakra runner tests; never contact IBKR."""
import unittest
from unittest.mock import patch
from RudraScanner import run_now


class TestRunNow(unittest.TestCase):
    def test_running_bot_uses_existing_queue(self):
        with patch.object(run_now, "bot_running", return_value=True), \
             patch.object(run_now, "queue_existing", return_value=0) as queued, \
             patch.object(run_now, "run_standalone") as standalone:
            self.assertEqual(run_now.main(["--premarket-test", "--no-wait"]), 0)
            queued.assert_called_once()
            standalone.assert_not_called()

    def test_stopped_bot_delegates_to_standalone(self):
        with patch.object(run_now, "bot_running", return_value=False), \
             patch.object(run_now, "run_standalone", return_value=0) as standalone:
            self.assertEqual(run_now.main([]), 0)
            standalone.assert_called_once_with(dry_run=False)

    def test_dry_run_passed_to_standalone(self):
        with patch.object(run_now, "bot_running", return_value=False), \
             patch.object(run_now, "run_standalone", return_value=0) as standalone:
            self.assertEqual(run_now.main(["--dry-run"]), 0)
            standalone.assert_called_once_with(dry_run=True)

    def test_dry_run_cannot_queue_when_bot_running(self):
        with patch.object(run_now, "bot_running", return_value=True), \
             patch.object(run_now, "run_standalone", return_value=2) as standalone, \
             patch.object(run_now, "queue_existing") as queued:
            self.assertEqual(run_now.main(["--dry-run"]), 2)
            standalone.assert_called_once_with(dry_run=True)
            queued.assert_not_called()

    def test_status_only_uses_existing_cli(self):
        with patch.object(run_now, "queue_existing", return_value=0) as queued, \
             patch.object(run_now, "run_standalone") as standalone:
            self.assertEqual(run_now.main(["--status"]), 0)
            queued.assert_called_once()
            standalone.assert_not_called()


if __name__ == "__main__":
    unittest.main()
