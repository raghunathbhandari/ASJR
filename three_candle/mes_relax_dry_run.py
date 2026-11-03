"""Read-only MES ThreeCandle Relax v1 signal and filter dry run.

Requires local MESZ2026 IBKR September/October 5m CSVs.
No live orders, no IBKR connection, no download, no file writes.
Never falls back to Yahoo; missing MES data is an explicit failure.

On VPS:
    cd /root/trading/ASJR
    /root/trading/venv_new/bin/python three_candle/mes_relax_dry_run.py --show 20
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from three_candle_learing import (
    load_learning_candles, scan_core_candidates,
    v3_research_checks, v3_pass_checks,
)
from three_candle_relax_mode_v1 import add_relax_flags, PROFILES

DATA = Path(__file__).resolve().parent / "data"
MONTHS = ["2026-09", "2026-10"]
# PROVISIONAL MES research baseline, separate from the MNQ 30/60-point setup.
# MES multiplier is $5 per S&P 500 index point.
MES_STOP_POINTS = 3.0
MES_TARGET_POINTS = 6.0
MES_DOLLARS_PER_POINT = 5.0
FILES = [DATA / f"MESZ2026_IBKR_5m_{month}.csv" for month in MONTHS]
FILTERS = [
    "filter_3_location", "filter_4_v_shape", "filter_5_volume",
    "filter_6_time", "filter_7_wick", "filter_8_daily_range",
]

def audit():
    """Check IBKR data first, without replacing or modifying any CSV."""
    missing = [str(f) for f in FILES if not f.is_file()]
    if missing:
        raise SystemExit("MES DOWNLOAD NOT FOUND ON THIS MACHINE:\n" + "\n".join(missing))
    for f in FILES:
        df = pd.read_csv(f)
        required = {"Datetime_UTC", "Open", "High", "Low", "Close", "Volume"}
        absent = required - set(df)
        if absent:
            raise SystemExit(f"{f}: missing columns {sorted(absent)}")
        t = pd.to_datetime(df.Datetime_UTC, utc=True, errors="coerce")
        p = df[["Open", "High", "Low", "Close", "Volume"]].apply(pd.to_numeric, errors="coerce")
        invalid = (p.High < p[["Open", "Low", "Close"]].max(axis=1)) | (
            p.Low > p[["Open", "High", "Close"]].min(axis=1)
        )
        gaps = int((t.sort_values().diff() > pd.Timedelta(minutes=5)).sum())
        print(f"DATA {f.name}: rows={len(df)} | UTC {t.min()} to {t.max()} | "
              f"duplicates={t.duplicated().sum()} | gaps>5m={gaps} | "
              f"invalidOHLC={invalid.sum()} | zeroVolume={p.Volume.eq(0).sum()}")
        if (t.isna().any() or t.duplicated().any() or
                p.isna().any().any() or invalid.any()):
            raise SystemExit(f"Data review required before signals: {f.name}")
    print("DATA AUDIT: both source files readable; unchanged.")

def examine(show):
    candles = load_learning_candles("MES=F", "2026-09-01", "2026-10-31")
    print(f"MES RESEARCH RISK: SL {MES_STOP_POINTS:g} S&P points = "
          f"$-{MES_STOP_POINTS * MES_DOLLARS_PER_POINT:.2f}; "
          f"TP {MES_TARGET_POINTS:g} S&P points = "
          f"+${MES_TARGET_POINTS * MES_DOLLARS_PER_POINT:.2f}; 2R")
    records = []
    for c1i, c2i, c3i, direction, wait in scan_core_candidates(candles):
        t1, t2, t3 = (candles.index[k] for k in (c1i, c2i, c3i))
        c2, c3 = candles.iloc[c2i], candles.iloc[c3i]
        fvalues = v3_research_checks(candles.iloc[:c3i + 1], t2, direction, "MES=F")
        flags = v3_pass_checks(fvalues)
        body2 = abs(c2.Close - c2.Open)
        directional_wick = (
            min(c2.Open, c2.Close) - c2.Low if direction == "BUY"
            else c2.High - max(c2.Open, c2.Close)
        )
        wick_ratio = directional_wick / body2 if body2 else float("nan")
        c2i_volume20 = candles.Volume.iloc[max(0, c2i - 20):c2i].mean()
        rvol = float(c2.Volume / c2i_volume20) if c2i_volume20 > 0 else float("nan")
        c3body = 100 * abs(c3.Close - c3.Open) / c3.Close
        # Label every core signal, even if all V3 filters reject it.
        record = {
            "month": t3.strftime("%Y-%m"), "date_uk": str(t3.date()),
            "c1_uk": t1.strftime("%Y-%m-%d %H:%M"),
            "c2_uk": t2.strftime("%Y-%m-%d %H:%M"),
            "c3_uk": t3.strftime("%Y-%m-%d %H:%M"),
            "direction": direction, "wait_bars": wait,
            "core_candidate": "YES", "C3_body_pct": c3body,
            "F7_wick_body": wick_ratio, "F5_C2_RVOL20": rvol,
            "zero_volume_in_C2_C3": "YES" if (c2.Volume <= 0 or c3.Volume <= 0) else "NO",
            "all_six_v3_pass": all(flags.values()),
            **flags,
        }
        records.append(add_relax_flags(record))
    if not records:
        print("NO MES CORE SIGNALS in the downloaded data.")
        return
    df = pd.DataFrame(records)
    print(f"\nMES 15m RAW CORE SIGNALS: {len(df)}; V3 six-filter passes: {df.all_six_v3_pass.sum()}")
    print("BY MONTH / DIRECTION:")
    print(df.groupby(["month", "direction"]).size().to_string())
    print("\nFILTER PASS COUNTS (#3–#8 independently, no AND gate on relax mode):")
    for name in FILTERS:
        print(f"  {name}: {int(df[name].sum())}/{len(df)}")
    print("\nRELAX PROFILES (each independently flagged, no signals discarded):")
    for name in PROFILES:
        print(f"  {name}: {(df[name + '_pass'] == 'YES').sum()}/{len(df)}")
    cols = [
        "c3_uk", "direction", "c1_uk", "c2_uk",
        "C3_body_pct", "F7_wick_body", "F5_C2_RVOL20",
        *FILTERS, "relax_v1_pass", "relax_v1_wick_025_rvol_030_pass",
        "relax_v1_wick_050_rvol_050_pass",
    ]
    print(f"\nFIRST {min(show, len(df))} RAW CANDIDATES AND FILTERS:")
    print(df[cols].head(show).to_string(index=False, float_format=lambda n: f"{n:.3f}"))
    print("\nDRY RUN COMPLETE: no orders, no trade simulation, no file modifications.")
    print("NOTE: MES has $5/point, whereas MNQ has $2/point.")
    print("NOTE: profile thresholds are exploratory and inherited from NQ, not validated on MES.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", type=int, default=20)
    args = parser.parse_args()
    audit()
    examine(args.show)
