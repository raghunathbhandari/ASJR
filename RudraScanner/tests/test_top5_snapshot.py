"""Saved SMB Top 5 is precomputed by the Chakra category-board writer."""
import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from RudraScanner.category_board import save_board

class SnapshotTests(unittest.TestCase):
    def test_precompute_from_all_four_scan_codes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            day = datetime.now(timezone.utc).date().isoformat()
            raw = root / "ASJR_Analyst" / "DataLake" / day / "raw"
            raw.mkdir(parents=True)
            with (raw / "ibkr_scanner_list.csv").open("w", newline="") as fp:
                writer = csv.DictWriter(fp, fieldnames=["ticker", "scan_code", "rank", "scanned_at_utc"])
                writer.writeheader()
                stamp = datetime.now(timezone.utc).isoformat()
                for symbol, code in [("ASTS", "TOP_PERC_GAIN"), ("ASTS", "HOT_BY_VOLUME"),
                                     ("INTC", "MOST_ACTIVE"), ("WDC", "TOP_PERC_LOSE")]:
                    writer.writerow(dict(ticker=symbol, scan_code=code, rank=1, scanned_at_utc=stamp))
            board = {"day": day, "generated_at_uk": datetime.now(timezone.utc).isoformat(), "rows": []}
            save_board(root, day, board)
            saved = root / "ASJR_Analyst" / "DataLake" / day / "processed" / "rudra_smb_top5.txt"
            self.assertTrue(saved.is_file())
            result = saved.read_text()
            self.assertIn("ASTS", result)
            self.assertIn("INTC", result)
            self.assertIn("WDC", result)
            self.assertIn("SCANNER DISCOVERY | NOT TRADE SIGNALS", result)

if __name__ == "__main__":
    unittest.main()
