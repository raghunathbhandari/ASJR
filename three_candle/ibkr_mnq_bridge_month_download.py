#!/usr/bin/env python3
"""IBKR read-only monthly 5m MNQ export through the restricted Research Bridge."""
import argparse
import json
import subprocess
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from ib_insync import IB, Future, util

ROOT = Path("/root/trading/ASJR")
OUT = Path("three_candle/data/ibkr_futures_bridge")
UK = ZoneInfo("Europe/London")
# Explicit contract selection by month. No implicit back-adjustment.
CONTRACT_BY_MONTH = {
    "2025-11": "202512", "2025-12": "202603",
    "2026-01": "202603", "2026-02": "202603",
    "2026-03": "202606", "2026-04": "202606",
    "2026-05": "202606", "2026-06": "202609",
    "2026-07": "202609", "2026-08": "202609",
}
# Roll-month choices above are explicit approximations and must be separately
# reviewed for continuous-series construction. Raw files remain per-contract.

def run_git(where, *args):
    cp = subprocess.run(["git", *args], cwd=where, capture_output=True,
                        text=True, timeout=120)
    if cp.returncode:
        raise RuntimeError("Git step failed: " + " ".join(args[:2]))
    return cp.stdout.strip()

def publish(job_id, df, report, filename):
    origin = run_git(ROOT, "remote", "get-url", "origin")
    if "github.com" not in origin:
        raise RuntimeError("Unexpected origin")
    with tempfile.TemporaryDirectory(prefix="asjr_mnq_export_") as temp:
        checkout = Path(temp) / "repo"
        run_git(Path(temp), "clone", "--quiet", "--depth", "1", "--branch",
                "main", origin, str(checkout))
        run_git(checkout, "config", "user.name", "ASJR Futures Research Bridge")
        run_git(checkout, "config", "user.email", "asjr-futures-bridge@localhost")
        for retry in range(4):
            run_git(checkout, "fetch", "origin", "main")
            run_git(checkout, "checkout", "--force", "-B", "mnq-export", "FETCH_HEAD")
            dest = checkout / OUT / job_id
            if dest.exists():
                raise RuntimeError("Refusing to overwrite existing job data")
            dest.mkdir(parents=True)
            df.to_csv(dest / filename, index=False)
            (dest / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
            run_git(checkout, "add", "--", str(OUT / job_id))
            run_git(checkout, "commit", "-m", "MNQ historical export " + job_id)
            pushed = subprocess.run(["git", "push", "origin", "HEAD:refs/heads/main"],
                                    cwd=checkout, capture_output=True, timeout=120)
            if pushed.returncode == 0:
                return str(OUT / job_id / filename)
            time.sleep(retry + 1)
    raise RuntimeError("Failed to publish MNQ download")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job-id", required=True)
    ap.add_argument("--month", choices=sorted(CONTRACT_BY_MONTH), required=True)
    args = ap.parse_args()
    year, month = map(int, args.month.split("-"))
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    expiry = CONTRACT_BY_MONTH[args.month]
    ib = IB()
    rows, errors = [], []
    try:
        ib.connect("127.0.0.1", 4002, clientId=891, timeout=20, readonly=True)
        matches = ib.qualifyContracts(Future(symbol="MNQ",
                           lastTradeDateOrContractMonth=expiry,
                           exchange="CME", currency="USD"))
        if len(matches) != 1:
            raise RuntimeError("MNQ contract not uniquely qualified")
        contract = matches[0]
        for n in range((end - start).days):
            day = start + timedelta(days=n)
            until = datetime.combine(day + timedelta(days=1), datetime.min.time(),
                                      tzinfo=timezone.utc)
            try:
                bars = ib.reqHistoricalData(contract,
                       endDateTime=until.strftime("%Y%m%d %H:%M:%S UTC"),
                       durationStr="2 D", barSizeSetting="5 mins",
                       whatToShow="TRADES", useRTH=False, formatDate=2,
                       keepUpToDate=False, timeout=50)
                for bar in bars:
                    ts = pd.Timestamp(bar.date)
                    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
                    if ts.date() != day:
                        continue
                    rows.append({"Datetime_UTC": ts.isoformat(),
                       "Datetime_UK": ts.tz_convert(UK).isoformat(),
                       "Open": bar.open, "High": bar.high, "Low": bar.low,
                       "Close": bar.close, "Volume": bar.volume})
            except Exception as e:
                errors.append({"day": str(day), "error": type(e).__name__})
            ib.sleep(1.2)
    finally:
        if ib.isConnected():
            ib.disconnect()
    if not rows:
        raise RuntimeError("No data; nothing published")
    df = pd.DataFrame(rows).drop_duplicates("Datetime_UTC").sort_values("Datetime_UTC")
    invalid = ((df["High"] < df[["Open", "Close", "Low"]].max(axis=1))
             | (df["Low"] > df[["Open", "Close", "High"]].min(axis=1)))
    report = {"source": "IBKR", "symbol": "MNQ", "expiry": expiry,
              "conId": contract.conId, "month": args.month, "bar_size": "5 mins",
              "useRTH": False, "timezone": "UTC", "rows": len(df),
              "first": df.iloc[0]["Datetime_UTC"], "last": df.iloc[-1]["Datetime_UTC"],
              "invalid_ohlc": int(invalid.sum()), "errors": errors,
              "verified_complete": False,
              "note": "Raw dated contract, not continuous or back-adjusted"}
    file = publish(args.job_id, df, report,
                   f"MNQ{expiry}_IBKR_5m_{args.month}_UTC.csv")
    print(json.dumps({"status": "SUCCESS", "rows": len(df),
                      "file": file, "errors": errors}))

if __name__ == "__main__":
    main()
