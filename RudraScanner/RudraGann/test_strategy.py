"""Offline checks for Rudra-Gann no-lookahead confirmations."""
import unittest
import pandas as pd
from RudraScanner.RudraGann.strategy import pattern, levels, scan

class StrategyTests(unittest.TestCase):
    def test_gann_sequence(self):
        self.assertIn(29929,levels(29800,30000))
        self.assertIn(29585,levels(29400,29600))
    def test_pattern(self):
        self.assertTrue(pattern({"Open":29934.75,"High":29944,
                                 "Low":29836.75,"Close":29839.75}))
        self.assertTrue(pattern({"Open":29532.75,"High":29548.75,
                                 "Low":29489.25,"Close":29493.25}))
        self.assertFalse(pattern({"Open":100,"High":110,"Low":90,"Close":108}))
    def test_entry_is_after_signal(self):
        df=pd.DataFrame([
            {"Open":101,"High":102,"Low":100,"Close":101,"Volume":1},
            {"Open":101,"High":101,"Low":98,"Close":99,"Volume":1},
            {"Open":99,"High":100,"Low":98,"Close":99,"Volume":1},
            {"Open":99,"High":100,"Low":94,"Close":95,"Volume":1},
            {"Open":95,"High":96,"Low":93,"Close":94,"Volume":1},
            {"Open":94,"High":95,"Low":87,"Close":88,"Volume":1}])
        df["datetime_ny"]=pd.date_range("2026-10-16 10:00",periods=len(df),freq="5min",tz="America/New_York")
        res=scan(df,zone=2,overshoot=2,lookback=4,confirm_bars=3)
        for trade in res:
            self.assertEqual(trade["entry_ix"],trade["signal_ix"]+1)
            self.assertGreater(trade["stop"],trade["entry"])
    def test_no_entry_from_tap_alone(self):
        df=pd.DataFrame([{"Open":100,"High":105,"Low":98,"Close":100,"Volume":1}]*6)
        df["datetime_ny"]=pd.date_range("2026-10-16 10:00",periods=len(df),freq="5min",tz="America/New_York")
        self.assertEqual(scan(df),[])

if __name__=="__main__":
    unittest.main()
