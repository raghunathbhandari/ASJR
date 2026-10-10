"""Scanner Discord gate cannot leak queued alerts when disabled/stale."""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[2]
ANALYST = BASE / "ASJR_Analyst"
if str(ANALYST) not in sys.path:
    sys.path.insert(0, str(ANALYST))

from Utils import asjr_alerts


def config(*, enabled, approved):
    return {
        "mode": "shadow",
        "research": True,
        "alerts_enabled": enabled,
        "thresholds_approved": approved,
    }


class ScannerQueueGateTests(unittest.TestCase):
    def test_disabled_scanner_cannot_use_old_pending_batch(self):
        day = datetime.now(asjr_alerts.ET).date().isoformat()
        with patch("RudraScanner.bot_hook.scanner_runtime",
                   return_value=config(enabled=False, approved=True)), \
             patch("RudraScanner.delivery._scanner_read",
                   return_value={"trade_date": day, "pending":[{"ticker":"INTC"}]}):
            self.assertFalse(asjr_alerts._scanner_queue_approved())

    def test_requires_both_flags_and_current_et_session(self):
        day = datetime.now(asjr_alerts.ET).date().isoformat()
        older = (datetime.now(asjr_alerts.ET).date() -
                 timedelta(days=1)).isoformat()
        with patch("RudraScanner.bot_hook.scanner_runtime",
                   return_value=config(enabled=True, approved=False)), \
             patch("RudraScanner.delivery._scanner_read",
                   return_value={"trade_date": day}):
            self.assertFalse(asjr_alerts._scanner_queue_approved())
        with patch("RudraScanner.bot_hook.scanner_runtime",
                   return_value=config(enabled=True, approved=True)), \
             patch("RudraScanner.delivery._scanner_read",
                   return_value={"trade_date": older}):
            self.assertFalse(asjr_alerts._scanner_queue_approved())
        with patch("RudraScanner.bot_hook.scanner_runtime",
                   return_value=config(enabled=True, approved=True)), \
             patch("RudraScanner.delivery._scanner_read",
                   return_value={"trade_date": day}):
            self.assertTrue(asjr_alerts._scanner_queue_approved())


if __name__ == "__main__":
    unittest.main()
