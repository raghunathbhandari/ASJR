"""Bounded background ticker history queue for existing connected Chakra IBKR app.

One broker request at a time initially, though up to three queue/validation
workers are available. Never creates a new EClient, bot, or scheduler.
Opt-in: constructing the queue doesn't start a request; callers explicitly
submit symbols and provide the existing-app history fetch function.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import BoundedSemaphore, Lock
import time

import pandas as pd

from .premarket_rvol import normalize_bars, _complete_profiles, SEGMENTS

DEFAULT_WORKERS = 3
DEFAULT_IBKR_CONCURRENCY = 1
MIN_PRIOR_DAYS = 5


class PremarketBackfillQueue:
    def __init__(self, fetch_one, store_one, *, workers=DEFAULT_WORKERS,
                 ibkr_concurrency=DEFAULT_IBKR_CONCURRENCY,
                 min_interval_seconds=0.0):
        if not 1 <= ibkr_concurrency <= workers <= 3:
            raise ValueError("Expected 1 <= IBKR concurrency <= workers <= 3")
        self.fetch_one = fetch_one
        self.store_one = store_one
        self.pool = ThreadPoolExecutor(max_workers=workers,
                                       thread_name_prefix="rudra-history")
        self.semaphore = BoundedSemaphore(ibkr_concurrency)
        self.lock = Lock()
        self.futures = {}
        self.next_allowed = 0.0
        self.interval = max(0.0, float(min_interval_seconds))
        self.closed = False

    def enqueue(self, ticker):
        ticker = str(ticker).upper().strip()
        if not ticker or not ticker.replace(".", "").replace("-", "").isalnum():
            raise ValueError("Invalid ticker")
        with self.lock:
            if self.closed:
                raise RuntimeError("Backfill queue is closed")
            previous = self.futures.get(ticker)
            if previous is not None:
                return previous  # No duplicate ticker request
            future = self.pool.submit(self._fetch_and_store, ticker)
            self.futures[ticker] = future
            return future

    def _fetch_and_store(self, ticker):
        # Guard the ONLY broker-calling portion. Caller must coordinate this
        # semaphore/connection with live requests before enabling in production.
        with self.semaphore:
            with self.lock:
                delay = max(0.0, self.next_allowed - time.monotonic())
                self.next_allowed = max(self.next_allowed, time.monotonic()) + self.interval
            if delay:
                time.sleep(delay)
            bars = self.fetch_one(ticker)
        # Worker handles only validated, completed data. Fail closed.
        if bars is None or bars.empty:
            return {"ticker": ticker, "status": "NO_DATA", "saved": False}
        data = bars.copy()
        if "ticker" not in data:
            data["ticker"] = ticker
        profile = normalize_bars(data)
        if profile.empty:
            return {"ticker": ticker, "status": "INVALID_DATA", "saved": False}
        days = set()
        for (symbol, day, segment), group in profile.groupby(
                ["ticker", "session_date_et", "session"]):
            start, end = SEGMENTS[segment]
            if group["minute"].astype(int).sort_values().tolist() == list(range(start, end, 5)):
                days.add(str(day))
        if len(days) < MIN_PRIOR_DAYS:
            return {"ticker": ticker, "status": "INSUFFICIENT_HISTORY",
                    "complete_days": len(days), "saved": False}
        self.store_one(ticker, profile)
        return {"ticker": ticker, "status": "SAVED",
                "complete_days": len(days), "saved": True}

    def status(self):
        with self.lock:
            return {ticker: ("PENDING" if not future.done() else
                    "ERROR" if future.exception() else future.result()["status"])
                    for ticker, future in self.futures.items()}

    def close(self, *, wait=True):
        with self.lock:
            self.closed = True
        self.pool.shutdown(wait=wait)


def fetch_using_existing_app(app, ticker, *, duration="10 D"):
    """Fetch using current ASJR connection, NOT a new IBKR client.

    Only enable after verifying live/feed access is serialized with this
    background path and IBKR request-ID/WAP callbacks are thread safe.
    """
    from ASJR_Analyst.Utils.asjr_ibkr import get_ibkr_5m_batch
    results = get_ibkr_5m_batch(app, [ticker], duration=duration,
                                batch_size=1, wait_time=20)
    frame = (results or {}).get(ticker)
    if frame is None or frame.empty:
        return pd.DataFrame()
    output = frame.reset_index().rename(columns={
        "Date": "datetime", "Volume": "volume"
    })
    output["ticker"] = ticker
    return output


def history_ready(profile):
    """Simple completed-day readiness gate, no assumption about liquidity."""
    if profile is None or profile.empty:
        return False
    group = profile.groupby(["ticker", "session_date_et", "session"])
    dates = set()
    for (_, day, session), x in group:
        start, end = SEGMENTS[session]
        if x["minute"].astype(int).sort_values().tolist() == list(range(start, end, 5)):
            dates.add(day)
    return len(dates) >= MIN_PRIOR_DAYS
