#!/usr/bin/env python3
"""Read-only IBKR stock history export into a unique GitHub job directory.

No orders. No changes to the live ASJR checkout or existing dataset paths.
"""
import argparse
import json
import re
import subprocess
import tempfile
import time
from datetime import date, datetime, time as daytime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from ib_insync import IB, Stock

ROOT = Path("/root/trading/ASJR")
DEST = Path("three_candle/data/ibkr_bridge")
FRAMES = {"1min": "1 min", "5min": "5 mins", "15min": "15 mins",
          "30min": "30 mins", "1h": "1 hour", "1d": "1 day"}
NY = ZoneInfo("America/New_York")


def git(cwd, *args):
    result = subprocess.run(["git", *args], cwd=str(cwd), text=True,
                            capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Git operation failed: {' '.join(args[:2])}")
    return result.stdout.strip()


def publish(job_id, csv, metadata, csv_name):
    rel_dir = DEST / job_id
    with tempfile.TemporaryDirectory(prefix="asjr_ibkr_range_") as temp:
        checkout = Path(temp) / "checkout"
        origin = git(ROOT, "remote", "get-url", "origin")
        if "github.com" not in origin:
            raise RuntimeError("Unexpected Git remote")
        git(Path(temp), "clone", "--quiet", "--depth", "1", "--single-branch",
            "--branch", "main", origin, str(checkout))
        git(checkout, "config", "user.name", "ASJR IBKR Research Bridge")
        git(checkout, "config", "user.email", "asjr-ibkr-bridge@localhost")
        for attempt in range(3):
            git(checkout, "fetch", "origin", "main")
            git(checkout, "checkout", "--force", "-B", "ibkr-export", "FETCH_HEAD")
            target = checkout / rel_dir
            if target.exists():
                raise RuntimeError("Job directory already exists; refusing overwrite")
            target.mkdir(parents=True)
            csv.to_csv(target / csv_name, index=False)
            (target / "manifest.json").write_text(
                json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            git(checkout, "add", "--", str(rel_dir))
            git(checkout, "commit", "-m", f"IBKR research export {job_id}")
            pushed = subprocess.run(
                ["git", "push", "origin", "HEAD:refs/heads/main"],
                cwd=str(checkout), capture_output=True, timeout=120)
            if pushed.returncode == 0:
                return str(rel_dir / csv_name)
            time.sleep(attempt + 1)
    raise RuntimeError("IBKR publish failed after 3 attempts")


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
    if not re.fullmatch(r"[A-Z][A-Z0-9.]{0,9}", args.ticker):
        parser.error("Invalid stock ticker")
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    days = (end - start).days + 1
    if days < 1 or days > 31 or (args.timeframe == "1min" and days > 7):
        parser.error("Range must be 1–31 days (1min: max 7 days)")
    if end > datetime.now(timezone.utc).date():
        parser.error("Future end date is not allowed")
    ib = IB()
    records, errors = [], []
    try:
        ib.connect("127.0.0.1", 4002, clientId=79432,
                   readonly=True, timeout=10)
        contract = Stock(args.ticker, "SMART", "USD")
        qualified = ib.qualifyContracts(contract)
        if not qualified:
            raise RuntimeError("Stock contract not found")
        for offset in range(days):
            day = start + timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            following = datetime.combine(day + timedelta(days=1),
                                         daytime(0), NY)
            end_utc = following.astimezone(timezone.utc)
            try:
                bars = ib.reqHistoricalData(
                    contract, endDateTime=end_utc.strftime("%Y%m%d %H:%M:%S UTC"),
                    durationStr="1 D", barSizeSetting=FRAMES[args.timeframe],
                    whatToShow="TRADES", useRTH=False, formatDate=2,
                    keepUpToDate=False, timeout=35)
                for bar in bars:
                    if args.timeframe == "1d":
                        bar_day = pd.Timestamp(bar.date).date()
                        if bar_day != day:
                            continue
                        ts = pd.Timestamp(datetime.combine(bar_day, daytime(0), NY)).tz_convert("UTC")
                    else:
                        ts = pd.Timestamp(bar.date)
                        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
                        if ts.tz_convert(NY).date() != day:
                            continue
                    records.append({
                        "Datetime_UTC": ts.isoformat(), "Open": bar.open,
                        "High": bar.high, "Low": bar.low, "Close": bar.close,
                        "Volume": bar.volume,
                    })
            except Exception as exc:
                errors.append({"date": day.isoformat(), "error": type(exc).__name__})
            ib.sleep(0.4)
    finally:
        if ib.isConnected():
            ib.disconnect()
    if not records:
        raise RuntimeError("No historical bars returned; no files published")
    frame = pd.DataFrame(records).drop_duplicates("Datetime_UTC").sort_values("Datetime_UTC")
    csv_name = f"{args.ticker}_{start}_{end}_{args.timeframe}_UTC.csv"
    metadata = {"source": "IBKR Gateway", "port": 4002, "ticker": args.ticker,
                "start": str(start), "end": str(end), "timeframe": args.timeframe,
                "rows": len(frame), "errors": errors, "timezone": "UTC",
                "verified_complete": False}
    path = publish(args.job_id, frame, metadata, csv_name)
    print(json.dumps({"status": "SUCCESS", "ticker": args.ticker,
                      "rows": len(frame), "file": path, "errors": errors}))


if __name__ == "__main__":
    main()
