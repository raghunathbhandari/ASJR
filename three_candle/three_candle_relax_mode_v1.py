"""ThreeCandle relax mode v1 — broad NQ candidate classification.

Keep EVERY C1-C2-C3 core candidate in the master table. Rules are research
profiles for the existing signal records, not replacement core detectors.
Neither original V3 nor existing notebooks are changed.

Example:
    python three_candle/three_candle_relax_mode_v1.py \\
        three_candle/results/NQ_2026-09_10_V3_RAW_CANDIDATES_UNIFIED_MASTER.csv \\
        --output three_candle/results/NQ_2026-09_10_RELAX_V1_FLAGS.csv
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

VERSION = "ThreeCandle relax mode v1"
# MNQ 1-contract research risk configuration (2026-11-03).
# Stop points are NOT an execution guarantee: live stop-market fills can slip.
# 1 MNQ point = $2, hence risk = $20 and target = $40 before fees.
STOP_POINTS_NQ = 10.0
TARGET_POINTS_NQ = 20.0
RISK_POINTS_NQ = STOP_POINTS_NQ
TARGET_R = TARGET_POINTS_NQ / STOP_POINTS_NQ   # 2R
MNQ_DOLLARS_PER_POINT = 2.0
TRAIL_TO_BREAKEVEN_AT_POINTS = 10.0
# Historical September-October backtest still available separately:
LEGACY_BACKTEST_RISK_PCT_NQ = 0.20
LEGACY_BACKTEST_TARGET_R = 3.0

# Evaluate combinations independently. Never use F3–F8 as an AND gate.
PROFILES = {
    "raw": {"label": "Raw core only"},
    "relax_v1": {"label": "Broad: C3 body <0.10%", "body_max": 0.10},
    "relax_v1_body_008": {"label": "C3 body <0.08%", "body_max": 0.08},
    "relax_v1_body_012": {"label": "C3 body <0.12%", "body_max": 0.12},
    "relax_v1_wick_025": {"label": "C3 body <0.10%; wick >=0.25", "body_max": 0.10, "wick_min": 0.25},
    "relax_v1_wick_050": {"label": "C3 body <0.10%; wick >=0.5", "body_max": 0.10, "wick_min": 0.50},
    "relax_v1_wick_1_10": {"label": "C3 body <0.10%; wick 1–10", "body_max": 0.10, "wick_min": 1.0, "wick_max": 10.0},
    "relax_v1_rvol_030": {"label": "C3 body <0.10%; C2 RVOL >=0.3", "body_max": 0.10, "rvol_min": 0.3},
    "relax_v1_rvol_050": {"label": "C3 body <0.10%; C2 RVOL >=0.5", "body_max": 0.10, "rvol_min": 0.5},
    "relax_v1_rvol_05_12": {"label": "C3 body <0.10%; C2 RVOL 0.5–1.2", "body_max": 0.10, "rvol_min": 0.5, "rvol_max": 1.2},
    "relax_v1_wick_025_rvol_030": {"label": "C3 body <0.10%; wick>=0.25; C2 RVOL>=0.3", "body_max": 0.10, "wick_min": 0.25, "rvol_min": 0.3},
    "relax_v1_wick_050_rvol_050": {"label": "C3 body <0.10%; wick>=0.5; C2 RVOL>=0.5", "body_max": 0.10, "wick_min": 0.5, "rvol_min": 0.5},
    "relax_v1_clean": {"label": "C3 body <0.10%; no zero-volume 5m in C2 or C3", "body_max": 0.10, "require_clean": True},
}

# These reference the existing unified master columns (NQ only).
COLUMNS = {
    "body": "C3_body_pct",
    "wick": "F7_wick_body",
    "rvol": "F5_C2_RVOL20",
    "clean": "zero_volume_in_C2_C3",
}


def numeric(record, field):
    """Return numeric input, or None when a metric was not recorded."""
    try:
        return float(record[field])
    except (ValueError, TypeError, KeyError):
        return None


def passes_profile(record, settings):
    """Flag a core candidate; NEVER delete non-passing rows.

    body_min/wick_min/rvol_min are inclusive; max values are exclusive.
    Missing measurements fail only when the profile requires that measure.
    """
    if record.get("core_candidate") not in ("YES", "True", "true", "1"):
        return False
    for name in ("body", "wick", "rvol"):
        lower, upper = settings.get(name + "_min"), settings.get(name + "_max")
        if lower is None and upper is None:
            continue
        value = numeric(record, COLUMNS[name])
        if value is None or (lower is not None and value < lower) or (upper is not None and value >= upper):
            return False
    if settings.get("require_clean") and record.get(COLUMNS["clean"]) != "NO":
        return False
    return True


def add_relax_flags(record):
    """Add all profile booleans to a copy of a single raw row."""
    out = dict(record)
    for name, settings in PROFILES.items():
        out[name + "_pass"] = "YES" if passes_profile(record, settings) else "NO"
    return out


def main():
    parser = argparse.ArgumentParser(description=VERSION)
    parser.add_argument("master", type=Path, help="Input: all-raw candidate CSV")
    parser.add_argument("--output", type=Path, required=True, help="Output: same rows, new profile flag columns")
    args = parser.parse_args()
    with args.master.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    flagged = [add_relax_flags(row) for row in rows]
    if not flagged:
        raise SystemExit("No candidate rows found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flagged[0]))
        writer.writeheader()
        writer.writerows(flagged)
    print(f"{VERSION}: preserved {len(flagged)} raw candidates")
    for name in PROFILES:
        print(f"  {name}: {sum(row[name + '_pass'] == 'YES' for row in flagged)}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
