"""Shared DataLake scanner processor: indicator features and safe reports.

This module cannot send orders or Discord messages. An explicit mode
is required to generate experimental research candidates; the safe
production default only publishes data-quality/indicator diagnostics.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .features import build_scanner_features
from .patterns import PatternSettings, detect_five_patterns
from .storage import _atomic, _csv_text

FEATURE_COLUMNS = (
    "ticker", "datetime", "bar_time_uk", "session", "close", "volume",
    "ema9", "ema9_ready", "wap", "wap_present", "vwap",
    "vwap_ready", "rvol20", "rvol20_ready",
    "prior_complete_sessions", "relative_volume_12bar",
    "ema9_slope5_pct", "prior_gap_minutes",
)


def evaluate_scanner(raw, *, now=None, enable_research=False,
                     index_bias="WAIT", sector_bias_by_ticker=None):
    frame, status = build_scanner_features(raw, now=now)
    config = PatternSettings(enabled_for_research=bool(enable_research))
    events, detector = detect_five_patterns(
        frame, index_bias=index_bias,
        sector_bias_by_ticker=sector_bias_by_ticker,
        settings=config,
    )
    report = {
        "state": "RESEARCH_ONLY" if enable_research else "INDICATORS_ONLY",
        "feature_status": status, "detector_status": detector,
        "events": events, "alert_delivery": "DISABLED",
    }
    return frame, report


def format_report(day, report):
    features = report["feature_status"]
    patterns = report["detector_status"]
    lines = [
        f"RUDRA RADAR | 5M | {day} | NOT A LIVE TRADE ALERT",
        f"MODE | {report['state']} | DISCORD DISABLED",
        f"INPUT | {features['input_rows']} bars | "
        f"{features['tickers']} tickers | {features['completed_rows']} completed",
        f"EMA9 | continuous across real available bars | "
        f"status={features['state']}",
        f"VWAP | exact IBKR WAP RTH-reset | {features['wap_state']} "
        f"| valid bars={features['vwap_ready_rows']}",
        f"RVOL20 | {features['rvol_state']} | valid bars={features['rvol20_ready_rows']}",
        f"TOP-DOWN | context gate | {patterns['blocked_context']} tickers WAIT/mixed",
        f"DETECTORS | {patterns['state']} | research candidates={patterns['emitted']}",
    ]
    for event in report["events"]:
        lines.append(
            f"{event['pattern']} | {event['ticker']} | {event['direction']} | "
            f"{event['bar_time_uk']} | {event['price']:.2f} | "
            f"EMA9 {event['ema9']:.2f} | VWAP {event['vwap']:.2f} | "
            f"12BAR_VOL {event['volume_vs_12bar_median']:.2f}x | EXPERIMENTAL"
        )
    if not report["events"]:
        lines.append("NO VERIFIED TRADING SIGNALS; missing WAP/context or detectors OFF.")
    return "\n".join(lines) + "\n"


def persist_features(repo_root, day, frame, report):
    """Write scanner-only processed/report outputs under COMMON DataLake.

    Called only in explicitly opted-in shadow research mode. No Git
    operation or Discord sender here. Never edit shared raw bar files.
    """
    folder = Path(repo_root) / "ASJR_Analyst" / "DataLake" / str(day)
    processed = folder / "processed"
    reports = folder / "reports"
    csv_path = processed / "rudra_scanner_features.csv"
    text_path = reports / "rudra_scanner_research.txt"
    state_path = reports / "rudra_scanner_research_status.json"
    fields = list(FEATURE_COLUMNS)
    if frame.empty:
        _atomic(csv_path, _csv_text(fields, []))
    else:
        content = frame.loc[:, fields].copy()
        content["datetime"] = content["datetime"].astype(str)
        content["bar_time_uk"] = content["bar_time_uk"].astype(str)
        _atomic(csv_path, content.to_csv(index=False))
    _atomic(text_path, format_report(day, report))
    _atomic(state_path, json.dumps(report, default=str, indent=2) + "\n")
    return {
        "feature_csv": str(csv_path), "research_report": str(text_path),
        "research_status": str(state_path),
    }
