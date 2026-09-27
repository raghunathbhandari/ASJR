"""Resolve the US session date and bootstrap its local DataLake watchlist."""

import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


ET = ZoneInfo("America/New_York")


def session_date(value):
    """US stock session date, including the preceding evening's overnight bars."""
    stamp = pd.Timestamp(value)
    stamp = stamp.tz_localize(ET) if stamp.tzinfo is None else stamp.tz_convert(ET)
    day = stamp.date()
    if (stamp.hour, stamp.minute) >= (20, 0):
        day += timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def scheduled_date(now=None):
    """Return None while the US stock overnight and day sessions are closed."""
    stamp = pd.Timestamp(now if now is not None else datetime.now(ET))
    stamp = stamp.tz_localize(ET) if stamp.tzinfo is None else stamp.tz_convert(ET)
    if stamp.weekday() == 5 or (stamp.weekday() == 6 and stamp.hour < 20):
        return None
    if stamp.weekday() == 4 and stamp.hour >= 20:
        return None
    return session_date(stamp)


def ensure_fixed_watchlist(datalake, trade_date):
    """Copy the latest earlier watchlist only when this date has none.

    A manually prepared file for the date always wins. Never use a future
    watchlist to backfill a past day.
    """
    datalake = Path(datalake)
    day = date.fromisoformat(str(trade_date)[:10])
    destination = datalake / day.isoformat() / "config" / "fixed_watchlist.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination, None

    candidates = []
    for folder in datalake.iterdir():
        if not folder.is_dir():
            continue
        try:
            folder_day = date.fromisoformat(folder.name)
        except ValueError:
            continue
        source = folder / "config" / "fixed_watchlist.csv"
        if folder_day < day and source.is_file():
            candidates.append((folder_day, source))
    if not candidates:
        raise FileNotFoundError(
            f"No fixed_watchlist.csv for {day} and no earlier DataLake watchlist to copy"
        )
    _, source = max(candidates)
    shutil.copyfile(source, destination)
    return destination, source
