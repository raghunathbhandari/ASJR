#!/usr/bin/env python3
"""
Standalone IBKR historical data import.

Purpose
-------
Download the finalized BB research universe directly from IB Gateway using
ib_async, save native 4H OHLCV history into the completely separate IBKR
research cache, then disconnect.

Run from repository root:
    cd /root/trading/ASJR
    /root/trading/venv_new/bin/python IBKR_import.py

This script is NOT part of the live Chakra/production IBKR wrapper flow.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from ib_async import IB

import Backtesting.DataLoader.ibkr_historical_loader as ibdl


DEFAULT_TICKERS = [
    "LRCX",
    "MU",
    "AMAT",
    "INTC",
    "PLTR",
    "XOM",
    "GOOG",
    "SPY",
    "META",
    "NVDA",
]

DEFAULT_START = "2016-10-03"
DEFAULT_END = "2026-10-02"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download IBKR historical OHLCV into separate research CSV cache."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4002)
    parser.add_argument("--client-id", type=int, default=31)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--interval", default="4h")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help="Space-separated ticker symbols.",
    )
    parser.add_argument(
        "--all-hours",
        action="store_true",
        help="Include extended hours. Default is regular trading hours only.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore existing cache while downloading this requested range.",
    )
    parser.add_argument(
        "--pacing-sleep",
        type=float,
        default=0.0,
        help="Pause between IBKR historical requests.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Number of tickers to download concurrently.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    print("=" * 100)
    print("IBKR HISTORICAL RESEARCH IMPORT")
    print("=" * 100)
    print(f"Tickers : {', '.join(args.tickers)}")
    print(f"Range   : {args.start} -> {args.end}")
    print(f"Interval: {args.interval}")
    print(f"Gateway : {args.host}:{args.port}")
    print(f"Client  : {args.client_id}")
    print(f"Concurrency: {args.concurrency}")
    print(f"RTH     : {not args.all_hours}")
    print(f"Cache   : {ibdl.DEFAULT_IBKR_CACHE_ROOT}")
    print("=" * 100)

    ib = IB()
    results: dict[str, int] = {}
    failures: dict[str, str] = {}

    try:
        print("\nConnecting to IB Gateway...")
        await ib.connectAsync(
            args.host,
            args.port,
            clientId=args.client_id,
            timeout=15,
        )
        print("Connected:", ib.isConnected())

        semaphore = asyncio.Semaphore(max(1, args.concurrency))

        async def download_one(number: int, ticker: str) -> None:
            ticker = ticker.upper().strip()

            async with semaphore:
                print("\n" + "#" * 100)
                print(
                    f"[{number}/{len(args.tickers)}] {ticker} | "
                    f"{args.interval} | {args.start} -> {args.end}"
                )
                print("#" * 100)

                try:
                    df = await ibdl.download_data_ibkr_prepare_csv_cache(
                        ticker=ticker,
                        start=args.start,
                        end=args.end,
                        interval=args.interval,
                        use_rth=not args.all_hours,
                        refresh=args.refresh,
                        pacing_sleep_seconds=args.pacing_sleep,
                        ib=ib,
                        disconnect_when_done=False,
                    )

                    results[ticker] = len(df)

                    if df.empty:
                        print(f"{ticker}: completed but no rows returned.")
                    else:
                        print(
                            f"{ticker}: COMPLETE | rows={len(df)} | "
                            f"{df.index.min()} -> {df.index.max()}"
                        )

                except Exception as exc:
                    failures[ticker] = f"{type(exc).__name__}: {exc}"
                    print(f"{ticker}: FAILED | {failures[ticker]}", file=sys.stderr)

        await asyncio.gather(
            *[
                download_one(number, ticker)
                for number, ticker in enumerate(args.tickers, start=1)
            ]
        )

    finally:
        if ib.isConnected():
            ib.disconnect()
        print("\nIB Gateway API disconnected.")

    print("\n" + "=" * 100)
    print("IMPORT SUMMARY")
    print("=" * 100)

    for ticker in args.tickers:
        ticker = ticker.upper().strip()
        if ticker in failures:
            print(f"{ticker:6s} | FAILED | {failures[ticker]}")
        else:
            print(f"{ticker:6s} | OK     | rows={results.get(ticker, 0)}")

    print("=" * 100)
    print(f"CSV root: {ibdl.DEFAULT_IBKR_CACHE_ROOT}")

    if failures:
        print(
            f"Finished with {len(failures)} failed ticker(s). "
            "Successful CSV files were kept."
        )
        return 1

    print("ALL TICKERS COMPLETED SUCCESSFULLY.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
