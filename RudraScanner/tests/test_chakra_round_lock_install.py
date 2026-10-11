"""Offline installer safety. Never touches /root/trading VPS launcher."""
import ast
import unittest
from RudraScanner.install_chakra_round_lock import apply_to_source


class LauncherLockInstallTests(unittest.TestCase):
    def test_patch_one_function_and_idempotent(self):
        source = (
            "import sys\n\n"
            "# def ibkr_trading_sudarsan_chakra(app):\n"
            "def ibkr_trading_sudarsan_chakra(app):\n"
            "    return app\n"
        )
        updated, state = apply_to_source(source)
        self.assertEqual(state, "READY")
        self.assertIn("@_asjr_guard_full_chakra_round", updated)
        ast.parse(updated)
        duplicate, state2 = apply_to_source(updated)
        self.assertEqual(state2, "ALREADY_INSTALLED")
        self.assertEqual(duplicate, updated)

    def test_missing_function_refused(self):
        with self.assertRaises(ValueError):
            apply_to_source("print('no launcher')\n")


if __name__ == "__main__":
    unittest.main()
