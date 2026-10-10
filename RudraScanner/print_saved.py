#!/usr/bin/env python3
"""Read the saved radar result without fetching, trading or sending alerts.

Example:
  /root/trading/venv_new/bin/python /root/trading/ASJR/RudraScanner/print_saved.py --date 2026-10-09
"""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from RudraScanner.storage import read_saved_report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print a saved RudraScanner report")
    parser.add_argument("--date", required=True, help="US trading session YYYY-MM-DD")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)
    from datetime import date
    date.fromisoformat(args.date)
    print(read_saved_report(args.repo, args.date))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
