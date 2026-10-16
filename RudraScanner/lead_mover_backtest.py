#!/usr/bin/env python3
"""Research-only daily-bar event study of conditions BEFORE big stock advances.

No IBKR calls, orders, DataLake mutations, scheduled jobs or Discord sends.
Universe is today's surviving ASJR symbols plus today's seven-code cache when
available; this causes survivorship/selection bias and cannot validate the
historical IBKR scanner's actual past rankings.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from RudraScanner.momentum_movers import tickers_from_datalake, EXCLUDE
from RudraScanner.ibkr_seven_scanner import load_saved_tickers

ET = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")
N_HOLD = 20
TARGET = 0.10
STOP = 0.05
N_TEST = 126
KEYS = ("BASELINE", "TREND", "HIGH_13W", "TIGHT_BASE", "BREAKOUT")


def download_history(tickers):
    """Yahoo daily adjusted OHLCV; omit the current ET date (unfinished/uncertain)."""
    import yfinance as yf

    for offset in range(0, len(tickers), 35):
        group = tickers[offset:offset + 35]
        try:
            table = yf.download(
                group, period="2y", interval="1d", auto_adjust=True,
                group_by="ticker", progress=False, threads=True, timeout=8
            )
        except Exception as exc:
            print("YAHOO WARNING | batch %d | %s" %
                  (offset // 35 + 1, type(exc).__name__))
            continue
        for ticker in group:
            try:
                frame = table[ticker] if isinstance(table.columns, pd.MultiIndex) else table
                frame = frame[["Open", "High", "Low", "Close", "Volume"]].copy()
                for column in frame.columns:
                    frame[column] = pd.to_numeric(frame[column], errors="coerce")
                frame = frame.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
                frame = frame.loc[frame.index.date < datetime.now(ET).date()]
                frame = frame.loc[(frame[["Open", "High", "Low", "Close"]] > 0).all(axis=1)]
                if len(frame) >= 252:
                    yield ticker, frame
            except (ValueError, KeyError, TypeError, AttributeError):
                continue


def signals(frame):
    """All predictors use information through signal-day close, never future bars."""
    close = frame["Close"]
    vol = frame["Volume"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    high63 = close.rolling(63, min_periods=63).max()
    momentum21 = close / close.shift(21) - 1
    momentum63 = close / close.shift(63) - 1
    vol20 = vol.rolling(20, min_periods=20).mean()
    eligible = (close >= 10) & (vol20 >= 1_000_000)

    trend = (momentum21 >= .10) & (momentum63 >= .20) & (
        close >= ema20) & (ema20 > ema50)
    leader = trend & (close >= high63 * .90)
    high13 = (close >= high63 * .97) & (momentum63 >= .20) & (ema20 > ema50)
    range10 = frame["High"].rolling(10).max() / frame["Low"].rolling(10).min() - 1
    quiet = vol.rolling(5).mean() < .8 * vol20
    tight = leader & (range10 <= .12) & quiet
    prior20 = frame["High"].shift(1).rolling(20).max()
    breakout = (close > prior20) & (vol >= vol20 * 1.5) & (
        momentum63 >= .20) & (ema20 > ema50)

    checks = {
        "BASELINE": eligible,
        "TREND": eligible & leader,
        "HIGH_13W": eligible & high13,
        "TIGHT_BASE": eligible & tight,
        "BREAKOUT": eligible & breakout,
    }
    return {name: series.fillna(False).astype(bool) for name, series in checks.items()}


def trade_result(frame, signal_idx, target=TARGET, stop=STOP, holding=N_HOLD):
    """Enter next session OPEN; stop-first if both levels touched on same day."""
    first = signal_idx + 1
    if first + holding - 1 >= len(frame):
        raise ValueError("Forward window incomplete")
    entry = float(frame["Open"].iloc[first])
    tp, sl = entry * (1 + target), entry * (1 - stop)
    for j in range(first, first + holding):
        row = frame.iloc[j]
        op, hi, lo = float(row["Open"]), float(row["High"]), float(row["Low"])
        if op <= sl:
            return (op / entry - 1) * 100, False
        if op >= tp:
            return (op / entry - 1) * 100, True
        if lo <= sl:
            return -stop * 100, False
        if hi >= tp:
            return target * 100, True
    return (float(frame["Close"].iloc[first + holding - 1]) / entry - 1) * 100, False


def study_symbol(ticker, frame):
    flags = signals(frame)
    test_start = len(frame) - N_TEST
    records = []
    for name, valid in flags.items():
        last_signal = -N_HOLD
        for idx in range(76, len(frame) - N_HOLD):
            if idx - last_signal < N_HOLD:
                continue
            # In-sample outcomes must finish before test period begins.
            if idx < test_start and idx + N_HOLD >= test_start:
                continue
            if name == "BASELINE" and (idx - 76) % N_HOLD:
                continue
            if not valid.iloc[idx]:
                continue
            ret, hit = trade_result(frame, idx)
            records.append((name, "TEST" if idx >= test_start else "TRAIN",
                            ticker, ret, hit))
            last_signal = idx
    current = [name for name in KEYS[1:] if bool(flags[name].iloc[-1])]
    return records, current


def summarize(records, label):
    subset = [r for r in records if r[1] == label]
    print("\n%s | +10%% TARGET / -5%% STOP / 20 DAYS" % label)
    print("SETUP        N  HIT%   AVG P/L%")
    for name in KEYS:
        data = [row for row in subset if row[0] == name]
        if data:
            hits = 100 * sum(row[4] for row in data) / len(data)
            avg = sum(row[3] for row in data) / len(data)
            print("%-12s %3d %5.1f %9.2f" % (name, len(data), hits, avg))
        else:
            print("%-12s   0   N/A       N/A" % name)


def main():
    day, names = tickers_from_datalake()
    if not names:
        print("MOVER STUDY | NO SAVED ASJR UNIVERSE")
        return 2
    extras = load_saved_tickers(date=day)
    names = sorted((set(names) | set(extras)) - EXCLUDE)
    print("RUDRA | MOVER STUDY | %s UK" % datetime.now(UK).strftime("%Y-%m-%d %H:%M"))
    print("UNIVERSE | %d | ASJR %s + fresh seven-code cache %d" %
          (len(names), day, len(extras)))
    print("YAHOO | 2Y adjusted daily bars | current ET day excluded")
    print("ENTRY | next-day OPEN | costs excluded | same-day double hit = STOP")
    records = []
    current = {key: [] for key in KEYS[1:]}
    count = 0
    latest = None
    for ticker, frame in download_history(names):
        count += 1
        r, signals_today = study_symbol(ticker, frame)
        records.extend(r)
        latest = max(latest, frame.index[-1]) if latest is not None else frame.index[-1]
        for key in signals_today:
            current[key].append(ticker)
    if not count:
        print("NO USABLE HISTORY | Yahoo fetch or history insufficient")
        return 2
    print("USABLE | %d | LATEST COMPLETED DAILY %s" %
          (count, latest.date()))
    print("TRAIN first history | TEST last %d sessions per ticker" % N_TEST)
    summarize(records, "TRAIN")
    summarize(records, "TEST")
    print("\nRESEARCH CANDIDATES | last completed daily bars")
    for name in KEYS[1:]:
        print("%s | %s" % (name, ", ".join(current[name][:12]) or "-"))
    print("CAUTION | Today's surviving universe; NOT historical IBKR code backtest")
    print("No causal proof, no fundamentals/catalyst filter, overlapping tickers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
