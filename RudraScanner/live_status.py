#!/usr/bin/env python3
"""Read-only VPS status page for Monday RudraScanner, no IBKR or Discord."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from RudraScanner.bot_hook import scanner_runtime


def get_status(repo_root, trade_date):
    root = Path(repo_root)
    day = root / "ASJR_Analyst" / "DataLake" / str(trade_date)
    def read(relative):
        f = day / relative
        if not f.is_file():
            return None
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"state": "INVALID_JSON", "path": str(f)}
    return {
        "trade_date_et": str(trade_date),
        "runtime": scanner_runtime(root, trade_date),
        "discovery": read("raw/scanner_status.json"),
        "research": read("reports/rudra_scanner_live_status.json"),
        "hourly": read("raw/rudra_scanner_hourly_status.json"),
        "radar_report": str(day / "reports" / "scalp_radar.txt"),
        "radar_saved": (day / "reports" / "scalp_radar.txt").exists(),
        "source": "SAVED_COMMON_DATALAKE_ONLY",
        "live_status_confirmed": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Read Monday RudraScanner saved status")
    p.add_argument("--date", default="2026-10-12")
    p.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    args = p.parse_args(argv)
    date.fromisoformat(args.date)
    state = get_status(args.repo, args.date)
    print("RUDRA SCANNER | SAVED VPS REPORT |", args.date)
    conf = state["runtime"]
    print("SCHEDULED MODE:", conf["mode"],
          "| RESEARCH:", conf["research"],
          "| SCANNER DISCORD:", conf["alerts_enabled"],
          "| PATTERN THRESHOLDS APPROVED:", conf["thresholds_approved"])
    discovery = state["discovery"] or {}
    print("DISCOVERY:", "NOT SAVED YET" if not discovery else
          discovery.get("selection", {}),
          "| IBKR:", {k: v.get("state") for k, v in
                      discovery.get("ibkr", {}).items()})
    research = state["research"] or {}
    print("FIVE-MINUTE:", "NOT SAVED YET" if not research else
          research.get("state", "DATA NOT READY"))
    print("INDEX/SECTOR:", (research.get("context") or {}).get("state", "WAIT"))
    print("WAP:", (research.get("feature_status") or {}).get(
        "wap_state", "NOT VERIFIED"))
    print("RVOL20:", (research.get("feature_status") or {}).get(
        "rvol_state", "NOT VERIFIED"))
    print("RESEARCH EVENTS:", len(research.get("events", [])))
    hourly = state["hourly"] or {}
    print("ONE-HOUR:", hourly.get("state", "NOT SAVED YET"),
          "| >=150 bars:", len(hourly.get("usable_150bars", [])))
    print("RADAR:", state["radar_report"] if state["radar_saved"]
          else "NOT SAVED YET")
    print("REPORT IS ONLY AS FRESH AS SAVED FILES; NOT A LIVE CONNECTION CHECK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
