#!/usr/bin/env python3
"""Monday 12-Oct preflight; NO broker calls, orders, or Discord messages."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

if __package__ in ("", None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from RudraScanner.bot_hook import scanner_runtime
from RudraScanner.discovery import read_ai_csv, SCANNER_CODES
from RudraScanner.universe import read_fixed_watchlist

MONDAY = "2026-10-12"


def preflight(repo_root, day=MONDAY):
    root=Path(repo_root)
    conf=scanner_runtime(root, day)
    ai_source=root/"ASJR_Analyst"/"config"/"ai_scanner_list.csv"
    # Check readiness as of the actual US market open, not Saturday.
    at_open=datetime(2026,10,12,13,30,tzinfo=timezone.utc)
    ai,ai_state=read_ai_csv(ai_source,now=at_open)
    fixed,fixed_state=read_fixed_watchlist(root,day)
    script=root/"ASJR_Analyst"/"Tests"/"test_asjr_pipeline.py"
    work=(script.read_text(encoding="utf-8") if script.is_file() else "")
    alerts=root/"ASJR_Analyst"/"Utils"/"asjr_alerts.py"
    alert_code=alerts.read_text(encoding="utf-8") if alerts.is_file() else ""
    health={
        "trade_date":day,
        "scheduled_mode":conf["mode"],
        "research_enabled":conf["research"],
        "live_scanner_alerts_enabled":conf["alerts_enabled"],
        "approved_thresholds":conf["thresholds_approved"],
        "scanner_codes":list(SCANNER_CODES),
        "fixed_today":len(fixed),
        "fixed_state":fixed_state["state"],
        "ai_valid_at_monday_open":len(ai),
        "ai_state_at_monday_open":ai_state["state"],
        "ai_expired_at_open":ai_state["expired"],
        "same_chakra_pipeline_hook":"run_live_scanner_round(" in work,
        "legacy_wicks_still_present":"alerts.build_wick_alerts(" in work,
        "locked_reversal_still_present":"run_rudra_reversal_strategy(" in work,
        "discord_queue_bridge":("prepare_queued_alert(" in alert_code and
                               "mark_queued_sent(" in alert_code),
        "broker_requests":0, "orders":0, "discord_sends":0,
    }
    health["ready_to_shadow"]=(conf["mode"]=="shadow" and
       health["same_chakra_pipeline_hook"] and
       health["legacy_wicks_still_present"] and
       health["locked_reversal_still_present"] and
       health["discord_queue_bridge"])
    if len(ai)<10:
        health["warning"]="AI CSV does not contain 10 live-valid candidates at Monday US open; refresh verified research before active 30/30."
    if fixed_state["state"]=="MISSING":
        health["warning_fixed"]="Monday fixed watchlist must be bootstrapped by the existing ASJR day loader."
    return health


def main():
    root=Path(__file__).resolve().parents[1]
    check=preflight(root)
    print("RUDRA SCANNER | MONDAY LIVE PREFLIGHT | READ-ONLY")
    print(json.dumps(check,indent=2,default=str))
    print("NO BOT RESTART, IBKR ORDERS, SCANS OR DISCORD SENDS.")
    return 0 if check["ready_to_shadow"] else 2


if __name__=="__main__":
    raise SystemExit(main())
