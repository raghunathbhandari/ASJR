"""Offline validation tests; no network or Yahoo calls."""
import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path

FILE = Path(__file__).with_name("yahoo_import.py")
spec = importlib.util.spec_from_file_location("yahoo_import", FILE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def job(**changes):
    today = date.today()
    d = {"schema_version":1,"id":"admin-2026102017000","operation":"yahoo_import",
         "symbols":["INTC","NQ=F"],"interval":"5m",
         "start":(today-timedelta(days=2)).isoformat(),
         "end":today.isoformat()}
    d.update(changes)
    return d

class Validation(unittest.TestCase):
    def test_valid(self):
        symbols, interval, _, _ = module.validate(job())
        self.assertEqual(symbols,["INTC","NQ=F"])
        self.assertEqual(interval,"5m")
    def test_invalid_ticker(self):
        with self.assertRaises(ValueError): module.validate(job(symbols=["../etc/passwd"]))
    def test_too_many(self):
        with self.assertRaises(ValueError): module.validate(job(symbols=["A","B","C","D","E","F"]))
    def test_bad_interval(self):
        with self.assertRaises(ValueError): module.validate(job(interval="1s"))
    def test_excessive_range(self):
        with self.assertRaises(ValueError): module.validate(job(start=(date.today()-timedelta(days=70)).isoformat()))
    def test_extra_fields(self):
        with self.assertRaises(ValueError): module.validate(job(command="rm -rf /"))
    def test_duplicate(self):
        with self.assertRaises(ValueError): module.validate(job(symbols=["INTC","INTC"]))

if __name__=="__main__":
    unittest.main()
