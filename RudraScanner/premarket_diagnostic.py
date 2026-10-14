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
        "mode": "EVALUATION_REPORT_ONLY",
        "history": status,
        "tickers": sorted(rows, key=lambda x: x["ticker"]),
        "notice": ("This report checks RVOL and EMA9/VWAP readiness. It is NOT a Discord "
                   "delivery receipt. Check the existing Chakra sender log for delivery; "
                   "no order is executed."),
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


def print_short_status(root, day):
    """Small Discord-friendly read-only RVOL5 health report (no broker call)."""
    from RudraScanner.premarket_live import enabled as alerts_enabled
    from RudraScanner.premarket_live_backfill import config_enabled as backfill_enabled

    print("RUDRA-PREMARKET |", day)
    print("CONFIG | RVOL DISCORD", "ON" if alerts_enabled() else "OFF",
          "| BACKFILL", "ON" if backfill_enabled(root) else "OFF")
    path = report_path(root, day)
    if not path.is_file():
        print("DIAGNOSTIC | NO SAVED REPORT")
        return 2
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        print("DIAGNOSTIC | CORRUPT")
        return 2
    age_seconds = (pd.Timestamp.now(tz="UTC").timestamp() - path.stat().st_mtime)
    print("REPORT AGE | %.1f min | %s" % (age_seconds / 60.0,
          "FRESH" if -60 <= age_seconds <= 1200 else "STALE"))
    q = record.get("signal_quality") or {}
    print("QUALITY |", q.get("state", "UNKNOWN"),
          "| fresh", q.get("latest_completed", "?"),
          "| RV5 ready", q.get("latest_rvol_ready", "?"),
          "| VWAP ready", q.get("latest_vwap_ready", "?"))
    print("BAR | newest", q.get("newest_bar_et", "N/A"),
          "| checked UTC", q.get("asof_utc", "N/A"))
    event_list = record.get("signal_events", [])
    print("BUY WATCH CANDIDATES |", len(event_list))
    for row in event_list[:5]:
        print(row.get("ticker", "?"), "|", row.get("uk_time", "?"),
              "UK | RV5", row.get("rv5", "?"))
    ticker_map = {r.get("ticker"): r for r in record.get("tickers", [])}
    for ticker in ("INTC", "WDC", "AKAM"):
        item = ticker_map.get(ticker)
        if item:
            print(ticker, "| RV5", item.get("rvol5", "N/A"),
                  "| history ready", item.get("rvol5_ready"),
                  "| last ET", item.get("bar_et", "N/A"))
    print("NOTE | candidates are not proof of Discord delivery")
    return 0
