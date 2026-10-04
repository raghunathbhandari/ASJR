"""Verified US equity regular-session eligibility, including early closes.

This is calendar data, not a price-pattern exception. Add a verified calendar
profile to extend the supported dates; never assume unknown holidays are open.
Overnight bars remain available for continuous indicators.
"""
import json
from pathlib import Path
import pandas as pd

DEFAULT_CALENDAR=Path(__file__).with_name('us_equity_sessions.json')


def regular_session_mask(timestamps, calendar_path=DEFAULT_CALENDAR):
    cal=json.loads(Path(calendar_path).read_text())
    ny=pd.to_datetime(timestamps,utc=True).dt.tz_convert(cal['timezone'])
    dates=ny.dt.strftime('%Y-%m-%d')
    if not dates.between(cal['valid_from'],cal['valid_to']).all():
        raise ValueError(f"Calendar verified only for {cal['valid_from']} through {cal['valid_to']}; supply an updated calendar profile")
    minute=ny.dt.hour*60+ny.dt.minute
    close=dates.map(cal['early_close_minutes']).fillna(cal['normal_close_minutes'])
    return (ny.dt.dayofweek<5)&~dates.isin(cal['closed_dates'])&(minute>=cal['normal_open_minutes'])&(minute<close)
