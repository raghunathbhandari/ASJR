#!/usr/bin/env python3
"""Read-only end-to-end DataLake 5M feature/research test.

Without captured WAP the tool MUST report exact VWAP as unavailable.
No fake/HLC3 substitute, no alerts, no IBKR calls or bot restart.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ in ("", None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from RudraScanner.engine import evaluate_scanner, format_report, persist_features
from RudraScanner.volume_history import apply_rolling_rvol20


def main(argv=None):
    p = argparse.ArgumentParser(description="Test RudraScanner features from saved shared DataLake")
    p.add_argument("--date", default="2026-10-09")
    p.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--save", action="store_true",
                   help="write namespaced research output to common DataLake")
    args = p.parse_args(argv)
    file = (Path(args.repo) / "ASJR_Analyst" / "DataLake"
            / args.date / "raw" / "intraday_5m.csv")
    if not file.is_file():
        print(f"DATA NOT READY | no 5M DataLake file: {file}")
        return 2
    frame = pd.read_csv(file)
    try:
        features, report = evaluate_scanner(frame)
    except (ValueError, TypeError, KeyError) as exc:
        print(f"DATA QUALITY ERROR | {exc}")
        return 2
    print(format_report(args.date, report))
    if args.save:
        paths = persist_features(args.repo, args.date, features, report)
        print("SAVED RESEARCH ONLY:", paths)
        print("No Git commit/push or Discord sends; WICKS/Reversal unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
