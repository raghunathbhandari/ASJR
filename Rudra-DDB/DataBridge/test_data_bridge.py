"""Offline Data Bridge validation checks; do not connect to Yahoo or GitHub."""
import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path

p=Path(__file__).with_name("data_bridge_worker.py")
spec=importlib.util.spec_from_file_location("data_bridge_worker",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def request(**kw):
    today=date.today()
    job={"schema_version":1,"id":"data-2026102016400","operation":"yahoo_import",
         "symbols":["MSFT","NQ=F"],"interval":"5m",
         "start":str(today-timedelta(days=3)),"end":str(today)}
    job.update(kw)
    return job

class TestValidation(unittest.TestCase):
    def test_valid(self): self.assertIsNotNone(m.validate(request(),"data-2026102016400"))
    def test_health(self):
        x={"schema_version":1,"id":"data-2026102016400","operation":"health"}
        self.assertIsNotNone(m.validate(x,x["id"]))
    def test_filename_mismatch(self): self.assertIsNone(m.validate(request(),"data-2026102016401"))
    def test_shell_payload(self): self.assertIsNone(m.validate(request(command="ls"),"data-2026102016400"))
    def test_injection_ticker(self): self.assertIsNone(m.validate(request(symbols=["../etc/passwd"]),"data-2026102016400"))
    def test_nonallowed_interval(self): self.assertIsNone(m.validate(request(interval="1s"),"data-2026102016400"))
    def test_many_symbols(self): self.assertIsNone(m.validate(request(symbols=["A","B","C","D","E","F"]),"data-2026102016400"))
    def test_duplicates(self): self.assertIsNone(m.validate(request(symbols=["MSFT","MSFT"]),"data-2026102016400"))
    def test_too_old_5m(self):
        self.assertIsNone(m.validate(request(start=str(date.today()-timedelta(days=90))),"data-2026102016400"))
    def test_bad_operation(self): self.assertIsNone(m.validate(request(operation="shell"),"data-2026102016400"))

if __name__=="__main__": unittest.main()
