#!/usr/bin/env python3
"""Run the exact scanner bot hook OFFLINE with Friday's shared DataLake.

It is safe while US exchanges are closed. REPLAY needs no IBKR connection.
Defaults are read-only. --save opt-in publishes namespaced historical
replay artifacts only, never authoritative live scanner files or Discord.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from RudraScanner.bot_hook import run_bot_shadow
from RudraScanner.replay import render_replay


def main(argv=None):
    parser = argparse.ArgumentParser(description="RudraScanner bot hook offline replay")
    parser.add_argument("--date", default="2026-10-09",
                        help="existing DataLake US trade date YYYY-MM-DD")
    parser.add_argument("--ibkr-source-date", default=None,
                        help="legacy DataLake IBKR mover source YYYY-MM-DD")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--save", action="store_true",
                        help="explicitly save historical-only replay artifacts")
    args = parser.parse_args(argv)
    try:
        result = run_bot_shadow(
            None, args.date, repo_root=Path(args.repo), mode="replay",
            allow_replay=True, replay_source_date=args.ibkr_source_date,
            save_replay=args.save,
        )
    except (OSError, ValueError) as exc:
        print("REPLAY DATA ERROR:", exc, file=sys.stderr)
        return 2
    print(render_replay(result))
    if result.get("report_path"):
        print("Historical report saved:", result["report_path"])
        print("No Git staging/push. No real IBKR scan. No Discord message.")
    else:
        print("Read-only mode: add --save to create explicitly named replay CSV/report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
