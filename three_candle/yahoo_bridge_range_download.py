#!/usr/bin/env python3
"""Yahoo historical price exporter for an allowlisted research bridge job.

Creates only unique per-job CSV/manifest paths in an isolated Git clone.
Never modifies existing datasets or the live VPS worktree.
"""
import argparse
import json
import re
import subprocess
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path("/root/trading/ASJR")
DEST = Path("three_candle/data/yahoo_bridge")
FRAMES = {"1min": "1m", "5min": "5m", "15min": "15m",
          "30min": "30m", "1h": "1h", "1d": "1d"}


def git(cwd, *args):
    result = subprocess.run(["git", *args], cwd=str(cwd), text=True,
                            capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Git operation failed: {' '.join(args[:2])}")
    return result.stdout.strip()


def publish(job_id, frame, manifest, filename):
    rel_dir = DEST / job_id
    with tempfile.TemporaryDirectory(prefix="asjr_yahoo_range_") as temp:
        checkout = Path(temp) / "checkout"
        origin = git(ROOT, "remote", "get-url", "origin")
        if "github.com" not in origin:
            raise RuntimeError("Unexpected Git remote")
        git(Path(temp), "clone", "--quiet", "--depth", "1", "--single-branch",
            "--branch", "main", origin, str(checkout))
        git(checkout, "config", "user.name", "ASJR Yahoo Research Bridge")
        git(checkout, "config", "user.email", "asjr-yahoo-bridge@localhost")
        for attempt in range(3):
            git(checkout, "fetch", "origin", "main")
            git(checkout, "checkout", "--force", "-B", "yahoo-export", "FETCH_HEAD")
            target = checkout / rel_dir
            if target.exists():
                raise RuntimeError("Job directory already exists; refusing overwrite")
            target.mkdir(parents=True)
            frame.to_csv(target / filename, index=False)
            (target / "manifest.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            git(checkout, "add", "--", str(rel_dir))
            git(checkout, "commit", "-m", f"Yahoo research export {job_id}")
            pushed = subprocess.run(
                ["git", "push", "origin", "HEAD:refs/heads/main"],
                cwd=str(checkout), capture_output=True, timeout=120)
            if pushed.returncode == 0:
                return str(rel_dir / filename)
            time.sleep(attempt + 1)
    raise RuntimeError("Yahoo publish failed after 3 attempts")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--timeframe", choices=sorted(FRAMES), required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"research-[0-9]{13}", args.job_id):
        parser.error("Invalid job ID")
    if not re.fullmatch(r"[A-Z][A-Z0-9.=-]{0,14}", args.ticker):
        parser.error("Invalid ticker")
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    days = (end - start).days + 1
    if days < 1 or days > 31 or (args.timeframe == "1min" and days > 7):
        parser.error("Range must be 1–31 days (1min: max 7 days)")
    if end > datetime.now(timezone.utc).date():
        parser.error("Future end date is not allowed")
    if args.timeframe != "1d" and (datetime.now(timezone.utc).date() - start).days > 59:
        parser.error("Yahoo intraday data must be within last 59 days")

    # yfinance end is exclusive. Explicit UTC output and no synthetic candles.
    inclusive_end = end + timedelta(days=1)
    downloaded = yf.download(
        args.ticker, start=start.isoformat(), end=inclusive_end.isoformat(),
        interval=FRAMES[args.timeframe], prepost=True,
        auto_adjust=False, progress=False, threads=False,
        multi_level_index=False,
    )
    if downloaded is None or downloaded.empty:
        raise RuntimeError("Yahoo returned no candles; nothing published")
    if isinstance(downloaded.columns, pd.MultiIndex):
        downloaded.columns = downloaded.columns.get_level_values(0)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if not set(required).issubset(downloaded.columns):
        raise RuntimeError("Missing OHLCV columns")
    frame = downloaded[required].copy()
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise RuntimeError("Missing datetime index")
    if frame.index.tz is None:
        raise RuntimeError("Timestamp timezone missing; refusing ambiguous export")
    frame.index = frame.index.tz_convert("UTC")
    frame = frame.loc[~frame.index.duplicated(keep="last")].sort_index()
    # Inclusive requested calendar dates in UTC. Do not fill missing bars.
    first = pd.Timestamp(start.isoformat(), tz="UTC")
    last = pd.Timestamp(inclusive_end.isoformat(), tz="UTC")
    frame = frame.loc[(frame.index >= first) & (frame.index < last)]
    frame = frame.dropna(subset=["Open", "High", "Low", "Close"])
    if frame.empty:
        raise RuntimeError("No valid candles in requested UTC interval")
    frame.index.name = "Datetime_UTC"
    frame = frame.reset_index()
    frame["Datetime_UTC"] = frame["Datetime_UTC"].map(lambda x: x.isoformat())
    filename = f"{args.ticker.replace('=', '_')}_{start}_{end}_{args.timeframe}_UTC.csv"
    manifest = {
        "source": "Yahoo Finance yfinance", "ticker": args.ticker,
        "start": str(start), "end": str(end), "timeframe": args.timeframe,
        "rows": int(len(frame)), "first_utc": frame["Datetime_UTC"].iloc[0],
        "last_utc": frame["Datetime_UTC"].iloc[-1],
        "zero_volume_rows": int((frame["Volume"] == 0).sum()),
        "timezone": "UTC", "verified_complete": False,
        "notes": "Yahoo intraday availability is limited; do not infer full session coverage.",
    }
    output = publish(args.job_id, frame, manifest, filename)
    print(json.dumps({"status": "SUCCESS", "ticker": args.ticker,
                      "rows": len(frame), "file": output}))


if __name__ == "__main__":
    main()
