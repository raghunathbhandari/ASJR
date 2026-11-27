#!/usr/bin/env python3
"""RudraEMA5: repeatable daily signal/filter audit. Research only, no trading orders.

Example:
    python RudraEMA5/filter_audit.py --date 2026-11-25

Active V2 rules retain the >=2% swing-down filter, remove the former C2-low
range filter entirely, and check Wilder RSI(14) <36 at completed C1.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, date, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / (
    "three_candle/data/ibkr_bridge/research-1795805412345/"
    "COHR_2026-11-01_2026-11-27_5min_UTC.csv"
)


def load(path: Path, cutoff: datetime) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8") as stream:
        for item in csv.DictReader(stream):
            stamp = datetime.fromisoformat(item["Datetime_UTC"].replace("Z", "+00:00"))
            if stamp >= cutoff:
                continue
            rows.append({
                "time": stamp, "open": float(item["Open"]),
                "high": float(item["High"]), "low": float(item["Low"]),
                "close": float(item["Close"]),
            })
    rows.sort(key=lambda b: b["time"])
    if len({b["time"] for b in rows}) != len(rows):
        raise ValueError("Duplicate candle timestamps")
    return rows


def add_indicators(bars: list[dict]) -> None:
    """EMA5 on closes; Wilder RSI(14), seeded from first 14 close changes."""
    ema = None
    avg_gain = avg_loss = 0.0
    for i, b in enumerate(bars):
        close = b["close"]
        ema = close if ema is None else (close + 2.0 * ema) / 3.0
        b["ema5"] = ema
        b["rsi14"] = None
        if i == 0:
            continue
        change = close - bars[i - 1]["close"]
        gain, loss = max(change, 0.0), max(-change, 0.0)
        if i <= 14:
            avg_gain += gain
            avg_loss += loss
            if i < 14:
                continue
            avg_gain /= 14.0
            avg_loss /= 14.0
        else:
            avg_gain = (avg_gain * 13 + gain) / 14.0
            avg_loss = (avg_loss * 13 + loss) / 14.0
        if avg_loss == 0:
            b["rsi14"] = 100.0 if avg_gain > 0 else 50.0
        else:
            b["rsi14"] = 100 - 100 / (1 + avg_gain / avg_loss)


def entry_trigger(c1: dict) -> float:
    from math import ceil
    return max(
        ceil((c1["high"] + 0.02 - 1e-9) * 100) / 100,
        ceil((c1["close"] * 1.002 - 1e-9) * 100) / 100,
    )


def audit(bars: list[dict], day: date, rsi_threshold: float = 36.0) -> dict:
    candidates = []
    for i in range(25, len(bars)):
        c2, c1, prior = bars[i], bars[i - 1], bars[i - 4]
        if c2["time"].date() != day:
            continue
        if (c2["time"] - c1["time"]).total_seconds() != 300:
            continue
        if (c1["time"] - prior["time"]).total_seconds() != 900:
            continue
        slope = (c1["ema5"] / prior["ema5"] - 1) * 100
        if not c1["high"] < c1["ema5"] or slope > -0.15:
            continue
        swing_high = max(b["high"] for b in bars[i - 25:i - 1])
        decline = (swing_high - c1["low"]) / swing_high * 100
        rsi = c1["rsi14"]
        candidates.append({
            "c1_time_uk": c1["time"].isoformat(),
            "c2_time_uk": c2["time"].isoformat(),
            "ema_slope_pct": round(slope, 4),
            "swing_down_pct": round(decline, 4),
            "rsi14_at_c1": round(rsi, 4) if rsi is not None else None,
            "swing_pass": decline >= 2,
            "rsi_pass": rsi is not None and rsi < rsi_threshold,
            "breakout_reached": c2["high"] >= entry_trigger(c1),
            "entry_trigger": entry_trigger(c1),
        })
    has = lambda p: sum(bool(p(x)) for x in candidates)
    return {
        "date_uk": day.isoformat(),
        "candidate_count": len(candidates),
        "swing_pass": has(lambda x: x["swing_pass"]),
        "rsi_threshold": rsi_threshold,
        "rsi_below_threshold": has(lambda x: x["rsi_pass"]),
        "swing_and_rsi": has(lambda x: x["swing_pass"] and x["rsi_pass"]),
        "swing_rsi_breakout": has(lambda x: x["swing_pass"] and x["rsi_pass"] and x["breakout_reached"]),
        "all_filters_with_breakout": has(lambda x: x["swing_pass"] and x["rsi_pass"] and x["breakout_reached"]),
        "CAUTION": "C2 intrabar fill/stop/trail sequencing cannot be verified from 5m OHLC; use finer resolution for validation.",
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-11-25", type=date.fromisoformat)
    parser.add_argument("--rsi-threshold", type=float, default=36.0)
    parser.add_argument("--csv", default=DEFAULT_CSV, type=Path)
    parser.add_argument("--cutoff", default="2026-11-27T18:00:00+00:00",
                        type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.cutoff.tzinfo is None:
        parser.error("--cutoff must include a timezone offset")
    bars = load(args.csv, args.cutoff.astimezone(timezone.utc))
    add_indicators(bars)
    print(json.dumps(audit(bars, args.date, args.rsi_threshold), indent=2))


if __name__ == "__main__":
    main()
