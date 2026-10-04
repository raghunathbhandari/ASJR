"""Request SMART daytime + OVERNIGHT history; retain real bars only.

IBKR routing reference:
https://www.interactivebrokers.com/campus/ibkr-quant-news/api-overnight-trading/
Historical requests:
https://www.interactivebrokers.com/docs/tws-api/doc/market-data-historical/historical-bars/requesting-historical-bars
The routing documentation does not guarantee a year of overnight history.
An unavailable/empty historical source raises instead of claiming success.
"""
from copy import deepcopy
import asyncio
import json
from pathlib import Path

import pandas as pd

from . import ibkr_historical_loader as base

DEFAULT_24H_CACHE_ROOT = base.DEFAULT_IBKR_CACHE_ROOT.parent / 'MarketData24h'


class HistoricalCoverageError(RuntimeError):
    pass


def _range(start, end):
    first = base._as_utc(start)
    last = base._as_utc(end)
    if isinstance(end, str) and len(end.strip()) <= 10:
        last += pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    if last <= first:
        raise ValueError('end must be after start')
    return first, last


def _overnight_mask(index):
    local = index.tz_convert('America/New_York')
    return (local.hour >= 20) | (local.hour < 4)


def merge_sessions(smart, overnight):
    """Choose one source per instant; never sum volume or invent bars."""
    night = overnight[_overnight_mask(overnight.index)]
    day = smart[~_overnight_mask(smart.index)]
    if night.empty:
        raise HistoricalCoverageError('OVERNIGHT returned no 20:00-04:00 ET candles.')
    if day.empty:
        raise HistoricalCoverageError('SMART returned no 04:00-20:00 ET candles.')
    return base._merge(day, night)


async def _download_route(ib, contract, start, end, interval, pacing_sleep):
    frames = []
    cursor = end
    previous_earliest = None
    chunk = 0
    while cursor > start:
        chunk += 1
        bars = await ib.reqHistoricalDataAsync(
            contract, endDateTime=cursor.to_pydatetime(),
            durationStr=base.IBKR_CHUNK_DURATION[interval],
            barSizeSetting=base.IBKR_BAR_SIZE[interval],
            whatToShow='TRADES', useRTH=False, formatDate=2,
            keepUpToDate=False,
        )
        frame = base._normalize_ibkr_bars(bars)
        if frame.empty:
            raise HistoricalCoverageError(
                f'{contract.symbol}@{contract.exchange}: no historical bars ending {cursor}. '
                'Check returned IBKR errors, permissions and historical availability. '
                'Full-day cache was not overwritten.'
            )
        earliest = frame.index.min()
        if previous_earliest is not None and earliest >= previous_earliest:
            raise HistoricalCoverageError(f'{contract.exchange}: historical cursor did not move backward.')
        frames.append(frame)
        print(f'{contract.symbol}@{contract.exchange} | chunk {chunk:03d} | '
              f'{earliest} -> {frame.index.max()} | rows={len(frame)}', flush=True)
        if earliest <= start:
            break
        previous_earliest = earliest
        cursor = earliest - pd.Timedelta(seconds=1)
        if pacing_sleep > 0:
            await asyncio.sleep(pacing_sleep)
    merged = base._merge(*frames)
    return merged[(merged.index >= start) & (merged.index <= end)].copy()


def coverage_report(frame, check_date, interval="5m"):
    et = frame.index.tz_convert('America/New_York')
    mins = et.hour * 60 + et.minute
    masks = {
        'overnight': (mins >= 1200) | (mins < 240),
        'premarket': (mins >= 240) & (mins < 570),
        'regular': (mins >= 570) & (mins < 960),
        'afterhours': (mins >= 960) & (mins < 1200),
    }
    uk = frame.index.tz_convert('Europe/London')
    day_mask = uk.strftime('%Y-%m-%d') == str(check_date)[:10]
    times = uk[day_mask].strftime('%H:%M')
    gaps = []
    day_times = uk[day_mask].sort_values()
    for prior, following in zip(day_times[:-1], day_times[1:]):
        if following - prior > pd.Timedelta(interval):
            gaps.append({'after':str(prior), 'before':str(following)})
    return {
        'rows':len(frame), 'first_utc':str(frame.index.min()),
        'last_utc':str(frame.index.max()),
        'session_rows':{key:int(mask.sum()) for key,mask in masks.items()},
        'uk_check_date':str(check_date)[:10],
        'uk_check_date_rows':int(day_mask.sum()),
        'uk_0800_present':bool('08:00' in times),
        'uk_0845_present':bool('08:45' in times),
        'uk_check_date_gaps_over_bar_interval':gaps,
        'note':'Real returned bars only. Source availability does not prove every trading session is complete.',
    }


async def download_24h_data(ticker, start, end, *, ib,
                           interval='5m', pacing_sleep_seconds=1.0,
                           cache_root=DEFAULT_24H_CACHE_ROOT):
    from ib_async import Stock
    interval = base._normalize_interval(interval)
    if interval == '1d':
        raise ValueError('24H merging requires intraday bars.')
    start_ts, end_ts = _range(start, end)
    qualified = await ib.qualifyContractsAsync(Stock(ticker.upper(), 'SMART', 'USD'))
    if len(qualified) != 1:
        raise HistoricalCoverageError(f'Cannot uniquely qualify {ticker}@SMART.')
    smart = qualified[0]
    if not smart.primaryExchange:
        details = await ib.reqContractDetailsAsync(smart)
        if len(details) == 1:
            smart.primaryExchange = details[0].contract.primaryExchange
    if not smart.primaryExchange:
        raise HistoricalCoverageError(f'Primary listing exchange unavailable for {ticker}.')
    night = deepcopy(smart)
    night.exchange = 'OVERNIGHT'
    print(f'{ticker}: SMART + OVERNIGHT | listing={smart.primaryExchange} | useRTH=False', flush=True)
    # Probe/download overnight first: do not spend an hour on SMART if the
    # first overnight historical request is unsupported by this Gateway.
    overnight = await _download_route(ib, night, start_ts, end_ts, interval, pacing_sleep_seconds)
    if overnight.empty or not _overnight_mask(overnight.index).any():
        raise HistoricalCoverageError(f'{ticker}: requested period contains no overnight bars.')
    daytime = await _download_route(ib, smart, start_ts, end_ts, interval, pacing_sleep_seconds)
    result = merge_sessions(daytime, overnight)
    root = Path(cache_root)
    # Existing RTH/extended-only caches are deliberately not used as proof
    # of 24H coverage. Write a separate canonical dataset only after both
    # sources succeeded. Preserve earlier imported dates outside this range.
    old = base.read_ibkr_cache(ticker, interval, cache_root=root)
    outside = old[(old.index < start_ts) | (old.index > end_ts)]
    output = base._write_cache(ticker, interval, base._merge(outside, result), cache_root=root)
    base._write_cache(ticker, interval, daytime, cache_root=root/'sources'/'SMART')
    base._write_cache(ticker, interval, overnight, cache_root=root/'sources'/'OVERNIGHT')
    report = coverage_report(result, str(end)[:10], interval)
    report['requested_start_utc'] = str(start_ts)
    report['requested_end_utc'] = str(end_ts)
    report['routing'] = ['SMART','OVERNIGHT']
    report_path = output.with_suffix('.coverage.json')
    temp = report_path.with_suffix('.tmp')
    temp.write_text(json.dumps(report, indent=2)+'\n')
    temp.replace(report_path)
    print('SESSION COVERAGE:', json.dumps(report['session_rows']), flush=True)
    print(f"{report['uk_check_date']} UK 08:00={report['uk_0800_present']}, 08:45={report['uk_0845_present']}", flush=True)
    print(f'24H requested sources imported | CSV: {output}', flush=True)
    print(f'Coverage report: {report_path}', flush=True)
    return result
