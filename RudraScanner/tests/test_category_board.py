"""Offline V1 category board contract: absent data never becomes a signal."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from RudraScanner.category_board import build_board, format_board, save_board
from RudraScanner.storage import read_saved_report


class CategoryBoardTests(unittest.TestCase):
    def test_discovery_visible_without_bars(self):
        tickers = [
            {"ticker":"INTC","sources":["FIXED"],"scan_codes":[]},
            {"ticker":"MSFT","sources":["AI","IBKR"],"scan_codes":["TOP_PERC_GAIN"],
             "ai_freshness":"FRESH"}
        ]
        board = build_board(tickers, pd.DataFrame(), day="2026-10-12",
                            now=pd.Timestamp("2026-10-12T14:00:00Z"))
        self.assertEqual(len(board["rows"]), 2)
        self.assertEqual(board["counts"]["TOP_IN_PLAY"], 1)
        self.assertEqual(board["counts"]["UNCLASSIFIED"], 1)
        self.assertTrue(all(r["price"] is None for r in board["rows"]))
        self.assertIn("NO VERIFIED TICKERS", format_board(board))

    def test_saved_report_includes_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            day = "2026-10-12"
            folder = Path(tmp)/"ASJR_Analyst"/"DataLake"/day/"reports"
            folder.mkdir(parents=True)
            (folder/"scalp_radar.txt").write_text("SCANNER BASE\n")
            board = build_board([{"ticker":"INTC","sources":["FIXED"]}],
                                pd.DataFrame(), day=day,
                                now=pd.Timestamp("2026-10-12T14:00:00Z"))
            save_board(tmp,day,board)
            output = read_saved_report(tmp,day)
            self.assertIn("SCANNER BASE",output)
            self.assertIn("CATEGORIZED V1",output)

    def test_stale_bar_not_misrepresented_as_current(self):
        features = pd.DataFrame([{
            "ticker":"INTC","datetime":pd.Timestamp("2026-10-09T14:00:00Z"),
            "close":100,"ema9":99,"volume":200,
            "ema9_slope5_pct":2,"relative_volume_12bar":.3
        }])
        board = build_board([{"ticker":"INTC","sources":["FIXED"]}],
                            features,day="2026-10-12",
                            now=pd.Timestamp("2026-10-12T14:00:00Z"))
        row = board["rows"][0]
        self.assertEqual(row["data_state"],"NO_FRESH_5M")
        self.assertIsNone(row["price"])
        self.assertNotIn("LOW_RVOL_WATCH",row["categories"])


if __name__ == "__main__":
    unittest.main()
