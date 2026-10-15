#!/usr/bin/env python3
"""On-demand Qullamaggie-style 1-month/3-month momentum leaders.

Reads the most recent saved ASJR DataLake universe; fetches 6 months of
adjusted daily closes using Yahoo Finance. No IBKR connection, trading
orders, Chakra run, data mutation, Discord alerts or source-file changes.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LAKE = ROOT / "ASJR_Analyst" / "DataLake"
EXCLUDE = {"BEAT", "ONDS"}
UK = ZoneInfo("Europe/London")


def tickers_from_datalake(day=None):
    folders = sorted(
        (p for p in LAKE.iterdir()
         if p.is_dir() and len(p.name) == 10 and p.name[4] == "-")
    ) if LAKE.is_dir() else []
    if day:
        folders = [p for p in folders if p.name == day]
    for folder in reversed(folders):
        found = set()
        for source, column in (
            (folder / "raw" / "ibkr_gapup.csv", "ticker"),
            (folder / "config" / "fixed_watchlist.csv", "ticker"),
            (folder / "processed" / "ticker_summary.csv", "Ticker"),
        ):
            if not source.is_file():
                continue
            try:
                frame = pd.read_csv(source, low_memory=False)
                matching = next((c for c in frame if c.lower() == column.lower()), None)
                if matching:
                    found.update(
                        str(x).strip().upper()
                        for x in frame[matching].dropna()
                    )
            except (OSError, ValueError, pd.errors.EmptyDataError):
                continue
        found = {s for s in found if s not in EXCLUDE
                 and s.replace(".", "").replace("-", "").isalnum()
                 and 1 <= len(s) <= 6}
        if found:
            return folder.name, sorted(found)
    return None, []


def download_daily(names):
    import yfinance as yf
    results = []
    for start in range(0, len(names), 35):
        batch = names[start:start + 35]
        try:
            data = yf.download(
                batch, period="6mo", interval="1d",
                group_by="ticker", auto_adjust=True,
                progress=False, threads=False
            )
        except Exception as exc:
            print("DOWNLOAD WARNING | batch %d | %s" %
                  (start // 35 + 1, type(exc).__name__))
            continue
        for ticker in batch:
            try:
                frame = data[ticker] if isinstance(data.columns, pd.MultiIndex) else data
                if not {"Close", "Volume"}.issubset(frame.columns):
                    continue
                part = frame[["Close", "Volume"]].dropna(subset=["Close"]).copy()
                part["Close"] = pd.to_numeric(part["Close"], errors="coerce")
                part["Volume"] = pd.to_numeric(part["Volume"], errors="coerce")
                part = part.dropna(subset=["Close"])
                if len(part) < 65:
                    continue
                results.append((ticker, part))
            except (KeyError, TypeError, ValueError):
                continue
    return results


def rankings(data, min_price=10, min_volume=1000000):
    rows = []
    for ticker, frame in data:
        close = frame["Close"]
        current = float(close.iloc[-1])
        average = float(frame["Volume"].tail(20).mean())
        if current < min_price or average < min_volume:
            continue
        one = 100 * (current / float(close.iloc[-22]) - 1)
        three = 100 * (current / float(close.iloc[-64]) - 1)
        high_63 = float(close.tail(63).max())
        from_high = 100 * (current / high_63 - 1) if high_63 else float("nan")
        rows.append({
            "ticker": ticker, "price": current, "month": one,
            "quarter": three, "from_high": from_high,
            "avg_volume": int(average), "last_day": str(frame.index[-1].date()),
        })
    return pd.DataFrame(rows)


def show_leaders(label, frame, metric, limit):
    print("\n%s | TOP %d" % (label, limit))
    print("RANK  SYMBOL    PRICE   1M%    3M%   3M-HIGH%  AVG VOL20")
    for n, (_, row) in enumerate(
        frame.sort_values(metric, ascending=False).head(limit).iterrows(), 1
    ):
        print("%-5d %-7s %7.2f %+6.1f %+6.1f %+9.1f %10s" %
              (n, row["ticker"], row["price"], row["month"],
               row["quarter"], row["from_high"],
               format(int(row["avg_volume"]), ",")))


def main():
    parser = argparse.ArgumentParser(
        description="On-demand Qullamaggie-style momentum discovery, daily Yahoo closes"
    )
    parser.add_argument("--date", help="DataLake universe date YYYY-MM-DD")
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--min-price", type=float, default=10)
    parser.add_argument("--min-volume", type=int, default=1000000)
    args = parser.parse_args()
    if not 1 <= args.top <= 50 or args.min_price <= 0 or args.min_volume < 0:
        parser.error("--top 1..50, --min-price >0, --min-volume >=0")
    day, names = tickers_from_datalake(args.date)
    if not names:
        print("MOMENTUM | NO SAVED DATALAKE UNIVERSE")
        return 2
    print("RUDRA MOMENTUM | %s UK | UNIVERSE %s | %d tickers" %
          (datetime.now(UK).strftime("%Y-%m-%d %H:%M"), day, len(names)))
    print("SOURCE | ASJR saved tickers + Yahoo adjusted daily closes; not IBKR scanner")
    result = rankings(download_daily(names), args.min_price, args.min_volume)
    if result.empty:
        print("NO ELIGIBLE DATA | check Yahoo access, history, price/volume filters")
        return 2
    print("ELIGIBLE | %d | exclude penny/illiquid stocks, BEAT and ONDS" % len(result))
    print("PERIODS | 1M=21 sessions | 3M=63 sessions | closes may lag live market")
    print("This is discovery, NOT an entry signal or fundamentals screen.")
    show_leaders("1-MONTH MOMENTUM", result, "month", args.top)
    show_leaders("3-MONTH MOMENTUM", result, "quarter", args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
