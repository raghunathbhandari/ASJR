#!/usr/bin/env python3
"""ASJR | Day-wise Top-10 research shortlist -> IBKR 5-minute history.

Read the current master stock CSV from GitHub main, not a stale local file.
For each COMPLETE daily shortlist, download each stock's ONE TRADING DAY of
5-minute data (regular + extended sessions), using the existing read-only
IBKR downloader. Its isolated-clone uploader pushes each CSV to GitHub.
Reuses existing daily/monthly 5-minute exports. Keeps full-day web-rank and
opening IBKR-rank distinct: web winners are look-ahead shortlists, NOT proven
14:45 UK winners across all eligible sector stocks. No orders or bot changes.
"""
import argparse
import csv
import io
import json
import re
import subprocess
import tempfile
import time
from collections import defaultdict
from datetime import date, datetime, time as tod
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/root/trading/ASJR")
PY = Path("/root/trading/venv_new/bin/python")
DOWNLOADER = ROOT / "three_candle/ibkr_bridge_range_download.py"
BASE = "Rudra-HotSectorHotStock"
MASTER = BASE + "/november_2026_daily_top10_stocks.csv"
SECTORS = BASE + "/november_2026_sector_leaders.csv"
REPORT = BASE + "/NOVEMBER_2026_IBKR_5MIN_DATA_STATUS.md"
PREFIX = "three_candle/data/ibkr_bridge/"
NY = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")
REPO_URL = "https://github.com/raghunathbhandari/ASJR/blob/main/"
EXPORT = re.compile(
    r"^three_candle/data/ibkr_bridge/research-\d{13}/"
    r"([A-Z][A-Z0-9.]*)_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})_5min_UTC\.csv$"
)
SYMBOL = re.compile(r"[A-Z][A-Z0-9.]{0,9}")

def git(cwd, *args, check=True):
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, timeout=180)
    if check and proc.returncode:
        raise RuntimeError("Git " + " ".join(args[:2]) + ": " + proc.stderr[-350:])
    return proc

def refresh():
    git(ROOT, "fetch", "-q", "origin", "main:refs/remotes/origin/main")

def from_remote(path):
    return git(ROOT, "show", "origin/main:" + path).stdout

def index_files():
    inventory = defaultdict(list)
    names = git(ROOT, "ls-tree", "-r", "--name-only", "origin/main", PREFIX).stdout
    for p in names.splitlines():
        m = EXPORT.fullmatch(p)
        if m:
            ticker, start, end = m.groups()
            inventory[ticker].append((start, end, p))
    return inventory

def archive_for(ticker, session, inventory):
    choices = [(start, end, path) for start, end, path
               in inventory.get(ticker, []) if start <= session <= end]
    # Single-day exports first, otherwise reuse a larger existing history.
    choices.sort(key=lambda x: (x[0] != x[1], x[0], x[2]))
    return choices[0][2] if choices else None

def read_master():
    masters = list(csv.DictReader(io.StringIO(from_remote(MASTER))))
    leader = {r["date_us"]: r["leader_etf"]
              for r in csv.DictReader(io.StringIO(from_remote(SECTORS)))}
    dates = defaultdict(list)
    for r in masters:
        session, ticker = r["date_us"], r["ticker"].strip().upper()
        if session not in leader:
            raise RuntimeError("Unknown trading day: " + session)
        if leader[session] != r["sector_etf"]:
            raise RuntimeError("Sector mismatch for " + session + " " + ticker)
        if not SYMBOL.fullmatch(ticker):
            raise RuntimeError("Invalid IBKR ticker: " + ticker)
        r["ticker"] = ticker
        dates[session].append(r)

    valid = {}
    for session, stocks in sorted(dates.items()):
        ranks = sorted(int(r["rank"]) for r in stocks)
        symbols = {r["ticker"] for r in stocks}
        if ranks != list(range(1, 11)) or len(symbols) != 10:
            print("SKIP |", session, "| expected 10 unique ranked tickers, got",
                  len(symbols), "symbols and ranks", ranks, flush=True)
            continue
        valid[session] = sorted(stocks, key=lambda r: int(r["rank"]))
    return valid, leader

def bars_for(path, session):
    """Returns coverage flag and first-15-min/after-signal stats."""
    raw = from_remote(path)
    regular = {}
    for r in csv.DictReader(io.StringIO(raw)):
        try:
            local = datetime.fromisoformat(r["Datetime_UTC"]).astimezone(NY)
            if local.date().isoformat() != session:
                continue
            if not (tod(9, 30) <= local.time() < tod(16, 0)):
                continue
            key = local.strftime("%H:%M")
            if key in regular:
                continue
            regular[key] = (float(r["Open"]), float(r["High"]),
                            float(r["Low"]), float(r["Close"]),
                            float(r["Volume"]))
        except (ValueError, TypeError, KeyError):
            continue
    needed = ("09:30", "09:35", "09:40")
    opening_ok = all(t in regular for t in needed)
    full = (len(regular) == 78 and opening_ok and
            all(f"{h:02d}:{m:02d}" in regular
                for h in range(9, 16) for m in range(0, 60, 5)
                if (h > 9 or m >= 30)))
    # Add last hour (15:00-15:55) included above. 9:30-15:55 is 78 bars.
    stat = {"status": "COMPLETE_78_RTH_5MIN" if full else "PARTIAL_RTH_BARS",
            "regular_bars": len(regular), "file": path}
    if opening_ok:
        opening = regular["09:30"][0]
        close = regular["09:40"][3]
        if opening > 0 and close > 0:
            vol = sum(regular[t][4] for t in needed)
            highs = [bar[1] for stamp, bar in regular.items() if stamp >= "09:45"]
            stat.update({"gain_pct": round(100 * (close/opening-1), 6),
                         "volume": int(vol),
                         "max_upside_pct": round(100 * (max(highs)/close-1), 6)
                         if highs else None})
    return stat

def audit(valid, inventory):
    statuses = {}
    for day, entries in sorted(valid.items()):
        for row in entries:
            ticker = row["ticker"]
            file = archive_for(ticker, day, inventory)
            if file:
                try:
                    statuses[(day, ticker)] = bars_for(file, day)
                except Exception as exc:
                    print("AUDIT ERROR |", day, ticker, str(exc)[:200])
                    statuses[(day, ticker)] = {"status": "READ_FAILED", "file": file}
            else:
                statuses[(day, ticker)] = {"status": "MISSING"}
    return statuses

def csv_output(rows, columns):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n",
                            extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()

def publish_status(statuses, leader):
    # Begin from the LATEST version after the historical downloader's pushes.
    origin = git(ROOT, "remote", "get-url", "origin").stdout.strip()
    if "github.com" not in origin:
        raise RuntimeError("Unexpected GitHub origin; refusing publish")
    with tempfile.TemporaryDirectory(prefix="asjr_day10_") as tmp:
        folder = Path(tmp) / "repo"
        git(Path(tmp), "clone", "-q", "--depth", "1", "--branch",
            "main", origin, str(folder))
        git(folder, "config", "user.name", "ASJR Sector Research")
        git(folder, "config", "user.email", "asjr-sector-research@localhost")
        for attempt in range(3):
            git(folder, "fetch", "-q", "origin", "main")
            git(folder, "checkout", "-f", "-B", "ibkr-daywise-report", "FETCH_HEAD")
            target = folder / MASTER
            with target.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                columns = list(reader.fieldnames)
                rows = list(reader)
            if "ibkr_data_status" not in columns:
                columns.append("ibkr_data_status")
            for row in rows:
                key = (row["date_us"], row["ticker"].strip().upper())
                stat = statuses.get(key)
                if not stat:
                    continue
                row["ibkr_data_status"] = stat["status"]
                if stat.get("file"):
                    row["ibkr_stock_5min_csv"] = stat["file"]
                if "gain_pct" in stat:
                    row["ibkr_first_15min_gain_pct"] = str(stat["gain_pct"])
                    row["ibkr_first_15min_shares"] = str(stat["volume"])
                    if stat.get("max_upside_pct") is not None:
                        row["ibkr_max_upside_after_1445_pct"] = str(stat["max_upside_pct"])
                # Keep original WEB_FULL_DAY ranking/research_status untouched.
            target.write_text(csv_output(rows, columns), encoding="utf-8")

            groups = defaultdict(list)
            for row in rows:
                groups[row["date_us"]].append(row)
            lines = [
                "# November 2026 — IBKR stock 5-minute download & coverage status",
                "",
                "**Source:** IBKR Gateway 4002, historical 5-minute OHLCV; "
                "files are UTC. Signal = 09:45 ET / 14:45 UK in Nov 2026.",
                "",
                "**Critical:** Web top 10 is based on **full-day closing gainers** "
                "(look-ahead); downloaded bars permit an opening-rank analysis "
                "**within this shortlist only**, not proof of all-sector top 10.",
                "IBKR source file paths in the master CSV are authoritative.",
                "",
                "| Date | Sector | Complete 5m | Partial/missing | 09:45 top 3 WITHIN web list | Highest 15m volume of 3 |",
                "|---|---|---:|---:|---|---|",
            ]
            for day, sector in sorted(leader.items()):
                group = groups.get(day, [])
                good = [r for r in group if r.get("ibkr_data_status") == "COMPLETE_78_RTH_5MIN"]
                opening = [r for r in good if r.get("ibkr_first_15min_gain_pct")]
                opening.sort(key=lambda r: -float(r["ibkr_first_15min_gain_pct"]))
                three = opening[:3] if len(opening) >= 3 else []
                winner = (max(three, key=lambda r: int(r["ibkr_first_15min_shares"]))["ticker"]
                          if len(three) == 3 else "PENDING")
                names = ", ".join(r["ticker"] for r in three) if three else "PENDING"
                lines.append(f"| {day} | {sector} | {len(good)}/{len(group) if group else 10} "
                             f"| {len(group)-len(good) if group else 10} | {names} | {winner} |")
            lines.extend(["",
                "[Master stock data + exact CSV file paths](november_2026_daily_top10_stocks.csv).",
                "Data-ready does not imply a clean unbiased backtest or "
                "confirmed point-in-time ETF membership.",
                ""])
            report_file = folder / REPORT
            report_file.write_text("\n".join(lines), encoding="utf-8")
            git(folder, "add", "--", MASTER, REPORT)
            commit = git(folder, "commit", "-m",
                         "Update November daily top10 IBKR 5m source paths and RTH audit",
                         check=False)
            if commit.returncode:
                if "nothing to commit" in (commit.stdout+commit.stderr):
                    print("MASTER REPORT | already up to date")
                    return
                raise RuntimeError("Report commit failed: " + commit.stderr[-300:])
            push = git(folder, "push", "origin", "HEAD:refs/heads/main",
                       check=False)
            if push.returncode == 0:
                print("MASTER REPORT PUSHED |", REPORT, flush=True)
                return
            time.sleep(attempt+1)
    raise RuntimeError("Could not publish summary after 3 attempts")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="one session YYYY-MM-DD (default all listed)")
    parser.add_argument("--limit", type=int, default=10,
                        help="maximum NEW stock-days to download per run; 0=all")
    parser.add_argument("--dry-run", action="store_true",
                        help="show missing/available stock-days; do not download/push")
    parser.add_argument("--retry-incomplete", action="store_true",
                        help="retry stock-days with published but partial RTH files")
    args = parser.parse_args()
    if args.limit < 0: parser.error("--limit must be >= 0")
    if not ROOT.is_dir() or not PY.is_file() or not DOWNLOADER.is_file():
        parser.error("VPS paths for repository/Python/IBKR downloader not found")
    if args.date:
        date.fromisoformat(args.date)
    refresh()
    all_days, leader = read_master()
    if args.date and args.date not in all_days:
        parser.error("No complete 10-stock shortlist for "+args.date)
    selected = ({args.date: all_days[args.date]} if args.date else all_days)
    inventory = index_files()
    status = audit(selected, inventory)

    queue = []
    complete = partial = 0
    for day, entries in sorted(selected.items()):
        for row in entries:
            key = (day, row["ticker"])
            s = status[key]
            if s["status"] == "COMPLETE_78_RTH_5MIN":
                complete += 1
                print("REUSE |", day, row["ticker"], s["file"], flush=True)
            elif s["status"] in ("PARTIAL_RTH_BARS", "READ_FAILED"):
                partial += 1
                print("PARTIAL |", day, row["ticker"], s.get("regular_bars", "?"),
                      "bars |", s.get("file"), flush=True)
                if args.retry_incomplete: queue.append(key)
            else:
                queue.append(key)
    todo = queue if args.limit == 0 else queue[:args.limit]
    print(f"PLAN | shortlisted days={len(selected)} | stock-days={len(status)} | "
          f"complete={complete} | existing_partial={partial} | new_missing={len(queue)} "
          f"| this_run={len(todo)} | 5min one session per ticker", flush=True)

    if args.dry_run:
        for day, ticker in todo: print("WOULD DOWNLOAD |", day, ticker)
        return 0

    started = time.time_ns()//1_000_000
    success = failed = 0
    for i, (day,ticker) in enumerate(todo):
        job = "research-"+str(started+i)
        cmd = [str(PY), "-u", str(DOWNLOADER),
               "--job-id", job, "--ticker", ticker,
               "--start", day, "--end", day, "--timeframe", "5min"]
        print("DOWNLOAD |", day, ticker, job, "|",
              datetime.now(UK).strftime("%H:%M:%S UK"), flush=True)
        try:
            call = subprocess.run(cmd, cwd=ROOT, text=True,
                                  capture_output=True, timeout=150)
            output = (call.stdout or "") + (call.stderr or "")
            if call.returncode == 0:
                success += 1
                print("PUSH SUCCESS |", day, ticker, output.strip()[-450:],
                      flush=True)
            else:
                failed += 1
                print("DOWNLOAD FAILED |", day, ticker, "exit=",
                      call.returncode, output.strip()[-450:], flush=True)
        except Exception as exc:
            failed += 1
            print("DOWNLOAD ERROR |", day, ticker, str(exc)[:250], flush=True)
        time.sleep(2)

    # Re-audit published exports and synchronise links to the existing
    # consolidated master CSV, without altering source ranking methods.
    refresh()
    final = audit(selected, index_files())
    publish_status(final, leader)
    total_good = sum(s["status"]=="COMPLETE_78_RTH_5MIN"
                     for s in final.values())
    print(f"FINAL | published={success}/{len(todo)} | failed={failed} | "
          f"complete regular-session stock-days={total_good}/{len(final)}",
          flush=True)
    print("Reminder: web full-day winners != actual opening sector top 10.")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
