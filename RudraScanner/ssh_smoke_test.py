#!/usr/bin/env python3
"""READ-ONLY RudraScanner SSH preview: no IBKR connection or live bot changes.

Run from /root/trading/ASJR with the normal virtualenv:
 /root/trading/venv_new/bin/python RudraScanner/ssh_smoke_test.py --date 2026-10-09

It validates the AI list, reviews the existing fixed list, and selects
the shared candidates within the 10+10+10 budget. IBKR scanning is NOT
performed here; no file is written. Use the separate offline unittest
command to validate the selection logic.
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from RudraScanner.discovery import read_ai_csv, SCANNER_CODES
from RudraScanner.universe import (
    load_shared_universe, selection_summary, common_tickers,
)


def load_saved_ibkr_csv(root, day):
    """Read prior saved discovery only; do not launch fresh API requests."""
    path = root / "ASJR_Analyst" / "DataLake" / day / "raw" / "ibkr_scanner_list.csv"
    if not path.exists():
        return [], "NOT_YET_SAVED"
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not set(("ticker", "scan_code", "rank", "scanned_at_utc")).issubset(
                set(reader.fieldnames or ())):
            raise ValueError(f"Invalid saved IBKR scanner CSV: {path}")
        rows = [r for r in reader if r.get("scan_code") in SCANNER_CODES]
    return rows, "SAVED_HISTORICAL_ONLY"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only shared RudraScanner/Repeversal candidates preview")
    parser.add_argument("--date", default="2026-10-09",
                        help="existing US-session DataLake folder (YYYY-MM-DD)")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)
    day = date.fromisoformat(args.date).isoformat()
    root = Path(args.repo).resolve()

    ai_file = root / "ASJR_Analyst" / "config" / "ai_scanner_list.csv"
    ai, ai_status = read_ai_csv(ai_file)
    ibkr, ibkr_status = load_saved_ibkr_csv(root, day)
    candidates, fixed_status = load_shared_universe(root, day, ai, ibkr)
    cap = selection_summary(candidates)

    print("=" * 74)
    print("RUDRA SCANNER | READ-ONLY SSH INPUT TEST")
    print("Shared DataLake date :", day)
    print("AI CSV               :", ai_file)
    print("AI status            :", ai_status["state"],
          "| eligible rows:", len(ai), "| expired:", ai_status["expired"])
    print("Fixed status         :", fixed_status["state"],
          "| enabled:", fixed_status["included"],
          "| exclusions:", ",".join(fixed_status["excluded"]) or "none")
    print("IBKR CSV             :", ibkr_status,
          "| rows:", len(ibkr), "(no scanner executed)")
    print("Selected             :", cap["selected_total"], "/ 30")
    print("Per source           :", cap["selected_by_source"])
    print("Unused per source    :", cap["unused_slots"])
    print("-" * 74)
    for source in ("FIXED", "AI", "IBKR"):
        names = [r["ticker"] for r in candidates
                 if r["selection_source"] == source]
        print(f"{source:5s} ({len(names):2d}/10) : {', '.join(names) or 'None'}")
    print("-" * 74)
    print("One shared stock list:", ", ".join(common_tickers(candidates)) or "EMPTY")
    print("Reversal NQ          : Yahoo 1H source, separate from 30 US-stock cap")
    print("Research is NOT a technical trade signal; no IBKR history fetched.")
    for issue in ai_status["warnings"][:8]:
        print("AI NOTE:", issue)
    for issue in fixed_status["warnings"][:8]:
        print("FIXED NOTE:", issue)
    if ibkr_status == "NOT_YET_SAVED":
        print("NOTE: IBKR scanner list is not generated until a connected test.")
    print("=" * 74)
    return 0 if ai_status["state"] != "ERROR" and fixed_status["state"] not in (
        "MISSING", "ERROR") else 2


if __name__ == "__main__":
    raise SystemExit(main())
