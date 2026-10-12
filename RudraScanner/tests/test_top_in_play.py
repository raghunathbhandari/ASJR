import unittest
from datetime import datetime, timezone, timedelta
from RudraScanner.top_in_play import render

class TopInPlayTests(unittest.TestCase):
    def test_short_format(self):
        now=datetime(2026,10,12,12,0,tzinfo=timezone.utc)
        board={"day":"2026-10-12","generated_at_uk":(now-timedelta(minutes=2)).isoformat(),
               "rows":[{"ticker":"ASTS","categories":["TOP_IN_PLAY","STRONG_MOMENTUM"],
                        "data_state":"FRESH_5M","discovery_priority":4,
                        "vol_12bar":1.6,"change_5m_pct":.2,"scanner_codes":"MOST_ACTIVE"},
                       {"ticker":"AMAT","categories":["UNCLASSIFIED"],
                        "data_state":"NO_FRESH_5M"}]}
        result=render(board,now=now)
        self.assertIn("ASTS | WATCH LONG",result)
        self.assertIn("REMAINING WATCHLIST | 1",result)
        self.assertNotIn("AMAT | WATCH",result)
    def test_stale_fails_closed(self):
        now=datetime(2026,10,12,12,0,tzinfo=timezone.utc)
        board={"day":"2026-10-12","generated_at_uk":(now-timedelta(hours=1)).isoformat(),"rows":[]}
        self.assertIn("DATA STALE",render(board,now=now))
if __name__=="__main__":
    unittest.main()
