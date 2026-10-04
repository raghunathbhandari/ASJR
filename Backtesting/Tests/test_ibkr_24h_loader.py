"""Offline tests for routing, source selection and failure behavior."""
import asyncio
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from Backtesting.DataLoader import ibkr_24h_loader as loader


class Stock:
    def __init__(self,symbol,exchange,currency):
        self.symbol=symbol; self.exchange=exchange; self.currency=currency
        self.primaryExchange=''; self.conId=0


def bars(times,price=100):
    return [SimpleNamespace(date=pd.Timestamp(t),open=price,high=price+1,
        low=price-1,close=price,volume=100) for t in times]


class FakeIB:
    def __init__(self,empty=False,wrong_route=False):
        self.requests=[];self.qualifications=[];self.empty=empty;self.wrong_route=wrong_route
    async def qualifyContractsAsync(self,contract):
        self.qualifications.append(contract.exchange)
        contract.primaryExchange='NASDAQ';contract.conId=123
        return [contract]
    async def reqHistoricalDataAsync(self,contract,**kwargs):
        self.requests.append((contract,kwargs))
        if self.empty and contract.exchange=='OVERNIGHT':return []
        if contract.exchange=='OVERNIGHT' and not self.wrong_route:
            return bars(['2026-10-02T00:00Z','2026-10-02T07:00Z','2026-10-02T07:45Z'])
        return bars(['2026-10-02T00:00Z','2026-10-02T08:00Z','2026-10-02T13:30Z','2026-10-02T21:00Z'],price=110)


class OvernightTests(unittest.TestCase):
    def setUp(self):
        self.patch=patch.dict(sys.modules,{'ib_async':types.SimpleNamespace(Stock=Stock,IB=FakeIB)})
        self.patch.start()
    def tearDown(self):self.patch.stop()

    def test_full_download_preserves_routing_and_coverage(self):
        ib=FakeIB()
        with tempfile.TemporaryDirectory() as root:
            out=asyncio.run(loader.download_24h_data('MU','2026-10-02','2026-10-02',ib=ib,cache_root=root))
            self.assertEqual(ib.qualifications,['SMART'])
            self.assertEqual([c.exchange for c,_ in ib.requests],['OVERNIGHT','SMART'])
            for c,options in ib.requests:
                self.assertEqual(c.primaryExchange,'NASDAQ');self.assertEqual(c.conId,123)
                self.assertFalse(options['useRTH']);self.assertEqual(options['formatDate'],2)
            report=loader.coverage_report(out,'2026-10-02')
            self.assertTrue(report['uk_0800_present']);self.assertTrue(report['uk_0845_present'])
            self.assertEqual(report['session_rows'],dict(overnight=3,premarket=1,regular=1,afterhours=1))
            self.assertEqual(out.loc['2026-10-02T00:00Z','Close'],100)
            self.assertEqual(len(out),6)
            self.assertTrue((Path(root)/'5m'/'MU_5m.coverage.json').exists())

    def test_empty_overnight_preserves_existing_data_and_skips_smart(self):
        ib=FakeIB(empty=True)
        with tempfile.TemporaryDirectory() as root:
            sentinel=Path(root)/'5m'/'MU_5m.csv';sentinel.parent.mkdir();sentinel.write_text('existing-data')
            with self.assertRaises(loader.HistoricalCoverageError):
                asyncio.run(loader.download_24h_data('MU','2026-10-02','2026-10-02',ib=ib,cache_root=root))
            self.assertEqual(sentinel.read_text(),'existing-data')
            self.assertEqual([c.exchange for c,_ in ib.requests],['OVERNIGHT'])

    def test_no_overnight_session_is_not_success(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(loader.HistoricalCoverageError):
                asyncio.run(loader.download_24h_data('MU','2026-10-02T05:00Z','2026-10-02',ib=FakeIB(wrong_route=True),cache_root=root))
            self.assertFalse((Path(root)/'5m'/'MU_5m.csv').exists())

    def test_repeat_window_raises(self):
        class RepeatIB(FakeIB):
            async def reqHistoricalDataAsync(self,contract,**kwargs):return bars(['2026-10-02T07:00Z'])
        ib=RepeatIB()
        c=Stock('MU','OVERNIGHT','USD')
        with self.assertRaises(loader.HistoricalCoverageError):
            asyncio.run(loader._download_route(ib,c,pd.Timestamp('2026-10-01T00:00Z'),pd.Timestamp('2026-10-03T00:00Z'),'5m',0))

    def test_cursor_moves_backward(self):
        class WindowIB(FakeIB):
            async def reqHistoricalDataAsync(self,contract,**kwargs):
                self.requests.append((contract,kwargs))
                t='2026-10-02T07:00Z' if len(self.requests)==1 else '2026-10-01T00:00Z'
                return bars([t])
        ib=WindowIB();c=Stock('MU','OVERNIGHT','USD')
        out=asyncio.run(loader._download_route(ib,c,pd.Timestamp('2026-10-01T00:00Z'),pd.Timestamp('2026-10-03T00:00Z'),'5m',0))
        self.assertEqual(len(out),2)
        self.assertEqual(pd.Timestamp(ib.requests[1][1]['endDateTime']),pd.Timestamp('2026-10-02T06:59:59Z'))

    def test_date_only_end_includes_full_day(self):
        start,end=loader._range('2026-10-01','2026-10-02')
        self.assertEqual(end,pd.Timestamp('2026-10-02T23:59:59Z'))
        with self.assertRaises(ValueError):loader._range('2026-10-03','2026-10-02')

    def test_merge_does_not_fabricate_or_sum_duplicates(self):
        day=loader.base._normalize_ibkr_bars(bars(['2026-10-02T07:00Z','2026-10-02T08:00Z'],110))
        night=loader.base._normalize_ibkr_bars(bars(['2026-10-02T07:00Z','2026-10-02T08:00Z'],100))
        out=loader.merge_sessions(day,night)
        self.assertEqual(list(out.Close),[100,110]);self.assertEqual(list(out.Volume),[100,100])
        self.assertEqual(len(out),2)

    def test_cli_flag_preserves_legacy_mode(self):
        spec=importlib.util.spec_from_file_location('import_script',Path(__file__).resolve().parents[2]/'IBKR_import.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        with patch.object(sys,'argv',['IBKR_import.py','--24h','--tickers','MU']):
            self.assertTrue(mod.parse_args().full_day)
        with patch.object(sys,'argv',['IBKR_import.py','--all-hours']):
            args=mod.parse_args();self.assertFalse(args.full_day);self.assertTrue(args.all_hours)


if __name__=='__main__':unittest.main()
