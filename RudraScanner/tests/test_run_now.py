"""Run-now safety checks. No broker/network access."""
import unittest
from unittest.mock import patch
from RudraScanner import run_now


class TestRunNow(unittest.TestCase):
    def test_standalone_refuses_until_launcher_audited(self):
        with patch.object(run_now.subprocess, "call") as call:
            self.assertEqual(run_now.main(["--mode", "standalone"]), 2)
            call.assert_not_called()

    def test_status_delegated_without_broker(self):
        with patch.object(run_now.subprocess, "call", return_value=0) as call:
            self.assertEqual(run_now.main(["--status"]), 0)
            command = call.call_args.args[0]
            self.assertIn("scan_now.py", command[1])
            self.assertIn("--status", command)

    def test_full_cycle_request_diagnostic_mode(self):
        with patch.object(run_now.subprocess, "call", return_value=0) as call:
            self.assertEqual(run_now.main(["--premarket-test", "--no-wait"]), 0)
            command = call.call_args.args[0]
            self.assertIn("--premarket-test", command)
            self.assertIn("--no-wait", command)


if __name__ == "__main__":
    unittest.main()
