"""Read-only diagnostic, one normal Chakra cycle; never sends Discord."""
from __future__ import annotations
import json
import os
from pathlib import Path
import pandas as pd
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def report_path(root, day):
    return (Path(root) / "ASJR_Analyst" / "DataLake" / str(day)
            / "reports" / "rudra_premarket_test.json")


def save_diagnostic(rvol, status, root, day, *, events=None, signal_quality=None):
    """Persist current RVOL5 readiness and reject unverified MA/VWAP signals."""
    path = report_path(root, day)
    rows = []
    if rvol is not None and not rvol.empty:
        for ticker, group in rvol.groupby("ticker"):
            last = group.sort_values("timestamp_et").iloc[-1]
            minute = int(last["minute"])
            rows.append({
                "ticker": str(ticker),
                "bar_et": str(last["timestamp_et"]),
                "session": str(last["session"]),
                "rvol5": round(float(last["rvol5"]), 4)
                          if pd.notna(last["rvol5"]) else None,
                "rvol5_ready": bool(last["rvol5_ready"]),
                "excluded_open": 570 <= minute < 600,
                "signal": "SEE_SIGNAL_QUALITY_AND_EVENTS" if signal_quality is not None else "NOT_EVALUATED",
            })
    content = {
        "date_et": str(day),
        "signal_quality": signal_quality or {"state": "NOT_EVALUATED"},
        "signal_events": list(events or []),
        "mode": "SHADOW_DIAGNOSTIC_NO_DISCORD",
        "history": status,
        "tickers": sorted(rows, key=lambda x: x["ticker"]),
        "notice": ("Signal evaluation diagnostic; BUY WATCH Discord still separately gated. "
                   "Refer to signal_quality and signal_events; no order is executed."),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(content, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temp, path)
    return str(path)


def print_saved(root, day):
    path = report_path(root, day)
    if not path.is_file():
        print("RUDRA-PREMARKET | NO TEST RESULT SAVED |", day)
        return 2
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        print("RUDRA-PREMARKET | INVALID TEST REPORT")
        return 2
    print("RUDRA-PREMARKET | ONE ROUND DIAGNOSTIC |", day)
    print("MODE:", report.get("mode"))
    print("HISTORY:", report.get("history"))
    print("SIGNAL QUALITY:", report.get("signal_quality"))
    print("SIGNAL EVENTS:", report.get("signal_events"))
    for item in report.get("tickers", []):
        rv = item["rvol5"]
        label = "%.2fx" % rv if rv is not None else "NOT READY"
        print(item["ticker"], "|", item["session"], "|", item["bar_et"],
              "| RV5", label, "|", item["signal"])
    print(report.get("notice", ""))
    return 0
