#!/usr/bin/env python3
"""MES Relax v1: structure-FIRST, four-check research scanner.

This is a NEW, independently editable research file. It does NOT modify the
original V3 state machine, notebooks, source CSVs or historical 593-row master.
No broker connection and NO ORDERS. Python 3.9+ standard library only.

Run from repository root:
    python3 three_candle/mes_relax_structure_first_v1.py --date 2026-10-29
    python3 three_candle/mes_relax_structure_first_v1.py --date 2026-10-30
    python3 three_candle/mes_relax_structure_first_v1.py --date 2026-10-30 --all

Causal rules: structure pivots require two FUTURE bars to become confirmed;
they are used only AFTER those bars have closed. Each candidate's five-candle
congestion window ends at the C3 closing candle. Signals are not trade fills.
"""
import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# 1. SIMPLE SETTINGS: change one option at a time for controlled experiments.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
SOURCES = [
    ROOT / "data" / "MESZ2026_IBKR_5m_2026-09.csv",
    ROOT / "data" / "MESZ2026_IBKR_5m_2026-10.csv",
]
UK = ZoneInfo("Europe/London")
SWING_LEFT = 2
SWING_RIGHT = 2
LEVEL_LOOKBACK_BARS = 100
MAX_C3_WAIT_BARS = 3

# The FOUR checks requested during visual review.
MIN_C2_WICK_BODY = 2.0              # Check 1: directional C2 wick >= 2 x real body
MIN_C2_SWEEP_POINTS = 2.0           # Check 2: C2 crosses C1 high/low >= 2 MES pts
REQUIRE_C3_DIRECTIONAL_CLOSE = True # Check 3: C3 CLOSE beyond C2 body, right direction
WICK_CONGESTION_LOOKBACK = 5
MAX_EXCESSIVE_WICK_CANDLES = 1       # Check 4: 2 or more => WAIT
WICK_BODY_FLOOR_POINTS = 0.25       # Avoid division by zero on doji bodies
# 'both': each candle must have BOTH wicks >= body (documented default).
# 'either': conservative alternative, EITHER side >= body.
EXCESSIVE_WICK_MODE = "both"

# Structure and location BEFORE inspecting candle type.
# A bearish structure favours SELL; bullish structure favours BUY.
# Ranging/unknown => WAIT (still print candidate on --all).
REQUIRE_STRUCTURE_ALIGNMENT = True
# Optional research price-level context, not one of the four hard checks:
# C2 must touch a prior confirmed swing high (SELL) or low (BUY) when enabled.
REQUIRE_CONFIRMED_SWING_LEVEL = False
LEVEL_TOLERANCE_POINTS = 1.0

# To avoid forcing displacement into the wick-reversal method, this module
# scans ONLY reversal-sweep candidates; displacement continuation comes later.

@dataclass(frozen=True)
class Bar:
    ts: datetime
    o: float
    h: float
    l: float
    c: float
    v: float


def read_ibkr_5m(files):
    """Read 5m IBKR CSV without changing them; UTC timestamps avoid DST bugs."""
    out = {}
    for file in files:
        if not file.exists():
            continue
        with file.open(newline="", encoding="utf-8-sig") as fp:
            for record in csv.DictReader(fp):
                when = datetime.fromisoformat(record["Datetime_UTC"])
                out[when] = Bar(
                    when, float(record["Open"]), float(record["High"]),
                    float(record["Low"]), float(record["Close"]),
                    float(record["Volume"]),
                )
    return [out[k] for k in sorted(out)]


def to_15m(five):
    """Build ONLY complete, contiguous sets of three 5m candles."""
    groups = defaultdict(list)
    for x in five:
        q = x.ts.minute // 15 * 15
        start = x.ts.replace(minute=q, second=0, microsecond=0)
        groups[start].append(x)
    out = []
    for stamp in sorted(groups):
        group = sorted(groups[stamp], key=lambda x: x.ts)
        if len(group) != 3 or any(
            x.ts != stamp + timedelta(minutes=5 * j)
            for j, x in enumerate(group)
        ):
            continue
        out.append(Bar(stamp, group[0].o,
                       max(x.h for x in group), min(x.l for x in group),
                       group[-1].c, sum(x.v for x in group)))
    return out


def wick_sizes(c):
    """Real body and upper/lower shadows in MES INDEX POINTS."""
    body = abs(c.c - c.o)
    return (body, c.h - max(c.o, c.c), min(c.o, c.c) - c.l)


def directional_wick_ratio(c2, side):
    """BUY uses lower wick; SELL uses upper wick. A zero body is floor-capped."""
    body, upper, lower = wick_sizes(c2)
    return (lower if side == "BUY" else upper) / max(body, WICK_BODY_FLOOR_POINTS)


def excessive_wick(c):
    """Flag one indecisive candle. BOTH and EITHER remain separately testable."""
    body, upper, lower = wick_sizes(c)
    limit = max(body, WICK_BODY_FLOOR_POINTS)
    if EXCESSIVE_WICK_MODE == "both":
        return upper >= limit and lower >= limit
    if EXCESSIVE_WICK_MODE == "either":
        return upper >= limit or lower >= limit
    raise ValueError("EXCESSIVE_WICK_MODE must be 'both' or 'either'")


def excessive_wicks_last5(bars, c3_index):
    """Only five COMPLETED candles through C3; never inspect later candles."""
    window = bars[max(0, c3_index - WICK_CONGESTION_LOOKBACK + 1):c3_index + 1]
    return sum(excessive_wick(x) for x in window), len(window)


def confirmed_pivots(bars, current):
    """Pivots usable by C3 close: right-hand candles must already exist.

    Returns (pivot_index, level). No lookahead: only pivot indices for which
    pivot_index + SWING_RIGHT <= current are eligible.
    """
    highs, lows = [], []
    for i in range(SWING_LEFT, current - SWING_RIGHT + 1):
        if i < max(SWING_LEFT, current - LEVEL_LOOKBACK_BARS):
            continue
        area = bars[i - SWING_LEFT:i + SWING_RIGHT + 1]
        p = bars[i]
        # Unique maximum/minimum prevents tied pivots from duplicating levels.
        if p.h == max(x.h for x in area) and sum(x.h == p.h for x in area) == 1:
            highs.append((i, p.h))
        if p.l == min(x.l for x in area) and sum(x.l == p.l for x in area) == 1:
            lows.append((i, p.l))
    return highs, lows


def classify_structure(highs, lows):
    """HH+HL => bullish, LH+LL => bearish. Otherwise ranging or unknown.

    This is a minimal, deliberately readable market-structure classifier.
    It never decides direction from a lone candle's colour or wick.
    """
    if len(highs) < 2 or len(lows) < 2:
        return "UNKNOWN"
    hh = highs[-1][1] > highs[-2][1]
    hl = lows[-1][1] > lows[-2][1]
    lh = highs[-1][1] < highs[-2][1]
    ll = lows[-1][1] < lows[-2][1]
    if hh and hl:
        return "BULLISH"
    if lh and ll:
        return "BEARISH"
    return "RANGING"


def near_confirmed_level(c2, side, highs, lows):
    """Assess recent confirmed liquidity levels; never use a future pivot."""
    levels = lows if side == "BUY" else highs
    if not levels:
        return False, None
    # A sweep can exceed its level; check range overlap within tolerance.
    level = levels[-1][1]
    reached = (c2.l <= level + LEVEL_TOLERANCE_POINTS if side == "BUY"
               else c2.h >= level - LEVEL_TOLERANCE_POINTS)
    return reached, level


def evaluate(bars, c1_i, c2_i, c3_i, side):
    """Make every condition visible; no hard-coded retrospective winner choice."""
    c1, c2, c3 = bars[c1_i], bars[c2_i], bars[c3_i]
    # This is a directional SWEEP; both-sided sweeps are examined independently
    # by BUY and SELL detectors, but can still be rejected as ambiguous later.
    sweep = c1.l - c2.l if side == "BUY" else c2.h - c1.h
    if sweep <= 0:
        return None
    # C3 must not invalidate the extreme swept by C2.
    if side == "BUY" and c3.l < c2.l:
        return None
    if side == "SELL" and c3.h > c2.h:
        return None
    c2_ratio = directional_wick_ratio(c2, side)
    c3_boundary = max(c2.o, c2.c) if side == "BUY" else min(c2.o, c2.c)
    close_pass = (c3.c > c3_boundary and c3.c > c3.o if side == "BUY"
                  else c3.c < c3_boundary and c3.c < c3.o)
    highs, lows = confirmed_pivots(bars, c3_i)
    structure = classify_structure(highs, lows)
    aligned = (structure == "BULLISH" if side == "BUY"
               else structure == "BEARISH")
    level_pass, level = near_confirmed_level(c2, side, highs, lows)
    wick_count, available = excessive_wicks_last5(bars, c3_i)

    checks = {
        "wick2": c2_ratio >= MIN_C2_WICK_BODY,
        "sweep2": sweep >= MIN_C2_SWEEP_POINTS,
        "c3_close": (close_pass if REQUIRE_C3_DIRECTIONAL_CLOSE else
                     c3.h > c3_boundary if side == "BUY" else c3.l < c3_boundary),
        "wick_congestion": available == WICK_CONGESTION_LOOKBACK
                           and wick_count <= MAX_EXCESSIVE_WICK_CANDLES,
    }
    structure_ok = aligned or not REQUIRE_STRUCTURE_ALIGNMENT
    location_ok = level_pass or not REQUIRE_CONFIRMED_SWING_LEVEL
    passes = all(checks.values()) and structure_ok and location_ok
    failures = [key for key, value in checks.items() if not value]
    if not structure_ok:
        failures.append("structure_not_aligned")
    if not location_ok:
        failures.append("not_near_confirmed_level")
    return {
        "c1_uk": c1.ts.astimezone(UK).isoformat(timespec="minutes"),
        "c2_uk": c2.ts.astimezone(UK).isoformat(timespec="minutes"),
        "c3_uk": c3.ts.astimezone(UK).isoformat(timespec="minutes"),
        "side": side, "structure": structure,
        "sweep_points": round(sweep, 3), "c2_wick_body": round(c2_ratio, 3),
        "c3_close": round(c3.c, 2), "c3_body_boundary": round(c3_boundary, 2),
        "confirmed_level": level, "last5_excessive_wicks": wick_count,
        "c3_wait_bars": c3_i - c2_i, "structure_aligned": aligned,
        "level_reached": level_pass,
        **{"pass_" + k: v for k, v in checks.items()},
        "decision": "CANDIDATE" if passes else "WAIT",
        "reason": ";".join(failures),
    }


def scan(bars):
    """Parallel BUY/SELL evaluation: neither direction blocks the other.

    Consecutive C1/C2 plus a C3 within MAX_C3_WAIT_BARS.
    Later confirmation can be a separate candidate, flagged by its time.
    This intentionally differs from the original V3 persistent-C1 machine.
    """
    out = []
    for c2_i in range(1, len(bars) - 1):
        c1_i = c2_i - 1
        if bars[c2_i].ts - bars[c1_i].ts != timedelta(minutes=15):
            continue
        for side in ("BUY", "SELL"):
            for c3_i in range(c2_i + 1, min(len(bars), c2_i + MAX_C3_WAIT_BARS + 1)):
                # Don't bridge missing bars, overnight maintenance or data gaps.
                if bars[c3_i].ts - bars[c3_i - 1].ts != timedelta(minutes=15):
                    break
                x = evaluate(bars, c1_i, c2_i, c3_i, side)
                if x is None:
                    break  # C2 invalidated, or this isn't the sweep direction
                if x["pass_c3_close"]:
                    out.append(x)
                    break  # earliest confirmed C3 for each C1/C2/side
                # Weak C3 is a diagnostic WAIT, not a confirmed signal.
                if c3_i == c2_i + MAX_C3_WAIT_BARS:
                    out.append(x)
    return out


def write_csv(rows, filename):
    filename.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "c1_uk", "c2_uk", "c3_uk", "side", "structure", "sweep_points",
        "c2_wick_body", "c3_close", "c3_body_boundary", "confirmed_level",
        "last5_excessive_wicks", "c3_wait_bars", "structure_aligned",
        "level_reached", "pass_wick2", "pass_sweep2", "pass_c3_close",
        "pass_wick_congestion", "decision", "reason",
    ]
    with filename.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="UK date YYYY-MM-DD; omit for all dates")
    parser.add_argument("--all", action="store_true", help="show WAIT candidates too")
    parser.add_argument("--output", help="CSV output path, optional")
    args = parser.parse_args()
    five = read_ibkr_5m(SOURCES)
    if not five:
        raise SystemExit("IBKR CSV missing; check SOURCES above")
    candles = to_15m(five)
    rows = scan(candles)
    if args.date:
        rows = [r for r in rows if r["c3_uk"].startswith(args.date)]
    if not args.all:
        rows = [r for r in rows if r["decision"] == "CANDIDATE"]
    if args.output:
        write_csv(rows, Path(args.output))
    for r in rows:
        print(f'{r["c3_uk"]} | {r["side"]:4s} | {r["structure"]:7s} | '
              f'sweep {r["sweep_points"]:>5.2f} | wick {r["c2_wick_body"]:>5.2f}x | '
              f'congest {r["last5_excessive_wicks"]}/5 | {r["decision"]} | {r["reason"]}')
    print(f"15m candles: {len(candles)} | matching rows: {len(rows)} | "
          f"trade candidates: {sum(x['decision']=='CANDIDATE' for x in rows)}")


if __name__ == "__main__":
    main()
