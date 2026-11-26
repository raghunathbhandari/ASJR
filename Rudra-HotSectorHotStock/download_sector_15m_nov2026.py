#!/usr/bin/env python3
"""Rudra-HotSectorHotStock: phase-1 November 2026 sector-history collector.

Read-only historical IBKR requests, 15-minute bars for 11 sector ETFs plus SPY.
Uses the established ASJR downloader, which publishes each CSV+manifest to
GitHub main through an isolated temporary checkout. No orders are sent.
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime, time as clock, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/root/trading/ASJR")
PYTHON = Path("/root/trading/venv_new/bin/python")
DOWNLOADER = ROOT / "three_candle/ibkr_bridge_range_download.py"
LOG_DIR = Path("/root/trading/ASJR_research_logs/hot_sector")
START, END = date(2026, 11, 1), date(2026, 11, 25)
SECTORS = ("XLK", "XLC", "XLY", "XLF", "XLI", "XLV",
           "XLE", "XLU", "XLP", "XLB", "XLRE")
TICKERS = (*SECTORS, "SPY")  # SPY is a benchmark, not a sector.
NY = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")


def output(message: str, log_file: Path) -> None:
    print(message, flush=True)
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(message + "\n")


def trading_dates() -> list[str]:
    dates = []
    day = START
    while day <= END:
        if day.weekday() < 5:
            dates.append(day.isoformat())
        day += timedelta(days=1)
    # All NYSE weekday sessions 2–25 Nov 2026 are expected to be regular days;
    # check coverage explicitly rather than silently filling missing candles.
    return dates


def audit(repo: Path, jobs: dict[str, str], log_file: Path) -> bool:
    output("AUDIT | Fetching GitHub references only; live worktree unchanged", log_file)
    fetch = subprocess.run(
        ["git", "fetch", "-q", "origin", "main:refs/remotes/origin/main"],
        cwd=repo, capture_output=True, text=True,
    )
    if fetch.returncode:
        output("ERROR | Git fetch failed; cannot verify published CSVs: "
               + fetch.stderr.strip()[:300], log_file)
        return False

    expected = trading_dates()
    rankings: dict[str, list[tuple[str, float]]] = {d: [] for d in expected}
    problems: list[str] = []

    for ticker in TICKERS:
        job_id = jobs.get(ticker)
        if not job_id:
            problems.append(f"{ticker}: downloader did not report success")
            continue
        path = (f"three_candle/data/ibkr_bridge/{job_id}/"
                f"{ticker}_{START}_{END}_15min_UTC.csv")
        result = subprocess.run(
            ["git", "show", f"origin/main:{path}"],
            cwd=repo, capture_output=True, text=True,
        )
        if result.returncode:
            problems.append(f"{ticker}: published CSV missing")
            continue

        counts = Counter()
        opening: dict[str, tuple[float, float]] = {}
        seen: set[tuple[str, clock]] = set()
        duplicates = 0
        bad_rows = 0
        for row in csv.DictReader(io.StringIO(result.stdout)):
            try:
                stamp = datetime.fromisoformat(row["Datetime_UTC"]).astimezone(NY)
                day = stamp.date().isoformat()
                if day not in rankings:
                    continue
                if clock(9, 30) <= stamp.time() < clock(16, 0):
                    key = (day, stamp.time())
                    if key in seen:
                        duplicates += 1
                    seen.add(key)
                    counts[day] += 1
                    if stamp.time() == clock(9, 30):
                        opening[day] = (float(row["Open"]), float(row["Close"]))
            except (KeyError, TypeError, ValueError):
                bad_rows += 1

        missing = [d for d in expected
                   if counts[d] != 26 or d not in opening]
        if missing:
            problems.append(ticker + ": missing/incomplete days: "
                            + ", ".join(f"{d} ({counts[d]}/26)" for d in missing))
        if duplicates or bad_rows:
            problems.append(f"{ticker}: duplicate={duplicates}, invalid={bad_rows}")
        for d, (price_open, price_close) in opening.items():
            if counts[d] == 26 and price_open > 0 and ticker != "SPY":
                rankings[d].append(
                    (ticker, 100 * (price_close / price_open - 1))
                )
        output(f"CHECK | {ticker:4s} | complete={len(expected)-len(missing)}/"
               f"{len(expected)} days | first-bars={len(opening)}"
               f" | duplicates={duplicates}", log_file)

    output("", log_file)
    output("First completed 15m sector candle (14:45 UK / 09:45 ET)", log_file)
    output("Date       | #1 ETF  Gain      | #2 ETF  Gain      | Covered", log_file)
    for d in expected:
        ordered = sorted(rankings[d], key=lambda pair: pair[1], reverse=True)
        first = ordered[0] if ordered else ("----", float("nan"))
        second = ordered[1] if len(ordered) > 1 else ("----", float("nan"))
        output(f"{d} | {first[0]:4s} {first[1]:+8.3f}% | "
               f"{second[0]:4s} {second[1]:+8.3f}% | "
               f"{len(ordered):2d}/11", log_file)

    if problems:
        output("AUDIT | INCOMPLETE", log_file)
        for problem in problems:
            output("WARNING | " + problem, log_file)
        return False

    output("AUDIT | PASS | 11 sectors + SPY | 18 trading days | "
           "26 regular-session 15m bars/day", log_file)
    return True


def main() -> int:
    if not PYTHON.is_file() or not DOWNLOADER.is_file() or not (ROOT / ".git").exists():
        print("ERROR | Missing ASJR repo, IBKR downloader, or VPS Python.")
        print(f"Expected: {ROOT}, {DOWNLOADER}, {PYTHON}")
        return 2

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    label = datetime.now(UK).strftime("%Y%m%d_%H%M%S")
    logfile = LOG_DIR / f"sector_15m_nov2026_{label}.log"
    jobfile = LOG_DIR / f"sector_15m_nov2026_{label}.jobs.json"
    base_id = time.time_ns() // 1_000_000
    successes: dict[str, str] = {}
    failures: list[str] = []

    output("RUDRA HOT SECTOR | PHASE 1 | NOVEMBER 2026", logfile)
    output(f"UK start time: {datetime.now(UK):%Y-%m-%d %H:%M:%S %Z}", logfile)
    output(f"Dates: {START} to {END} | Interval: 15min | "
           f"ETFs: {', '.join(TICKERS)}", logfile)
    output(f"Log: {logfile}", logfile)

    for i, ticker in enumerate(TICKERS):
        job_id = f"research-{base_id+i}"
        cmd = [
            str(PYTHON), "-u", str(DOWNLOADER),
            "--job-id", job_id,
            "--ticker", ticker,
            "--start", str(START),
            "--end", str(END),
            "--timeframe", "15min",
        ]
        output(f"START | {ticker} | {job_id} | "
               f"{datetime.now(UK):%H:%M:%S} UK", logfile)
        try:
            with subprocess.Popen(
                cmd, cwd=ROOT, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
            ) as proc:
                assert proc.stdout is not None
                for line in proc.stdout:
                    output(line.rstrip("\n"), logfile)
                code = proc.wait()
            if code == 0:
                successes[ticker] = job_id
                output(f"PUSH SUCCESS | {ticker} | {job_id}", logfile)
            else:
                failures.append(ticker)
                output(f"FAILED | {ticker} | exit={code}", logfile)
        except OSError as exc:
            failures.append(ticker)
            output(f"FAILED | {ticker} | {exc}", logfile)
        time.sleep(2)

    jobfile.write_text(json.dumps({
        "period": [str(START), str(END)],
        "timeframe": "15min",
        "published_jobs": successes,
        "failed_tickers": failures,
    }, indent=2) + "\n", encoding="utf-8")
    output(f"DOWNLOADS | pushed={len(successes)}/{len(TICKERS)}"
           f" | failed={len(failures)}", logfile)
    passed = audit(ROOT, successes, logfile)
    output(f"FINAL | pushed={len(successes)}/{len(TICKERS)}"
           f" | audit={'PASS' if passed else 'INCOMPLETE'}", logfile)
    output(f"JOB MAP | {jobfile}", logfile)
    output(f"LOG | {logfile}", logfile)
    output("Phase 2 stock downloads have NOT been started.", logfile)
    return 0 if passed and not failures else 1


if __name__ == "__main__":
    sys.exit(main())
