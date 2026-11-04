#!/usr/bin/env python3
"""MES v1 + v2 outcome validation: replay every 29-30 Oct 2026 candidate.

Inputs: ORIGINAL IBKR MES 5m September/October source files (read-only).
C3 timestamp is the 15m BAR START. Decision available at start+15m.
An executable scenario assumes the NEXT available 5m OPEN fill, with no
commissions/slippage. Historical OHLC does not establish actual fills.
If TP and SL hit inside the SAME 5m bar, result is AMBIGUOUS; no guess.
If the 5m feed contains a gap before exit, report DATA_GAP.
A second C3-CLOSE reference scenario is provided for comparison.
"""
import csv
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import mes_relax_structure_first_v1 as base
import mes_relax_pipeline_v1 as v1
import market_structure_v2 as structure_v2

STOP_POINTS = 5.0          # Existing MES chart reference, not proven fills
TARGET_POINTS = 10.0       # 2R research bracket
MAX_HOLD_MINUTES = 240     # 4h observation limit, not a trading rule
OUTPUT = Path(__file__).resolve().parent / "results" / "MES_v2_research"


def price_outcome(five, start_time, side, entry, max_minutes=MAX_HOLD_MINUTES):
    """Bracket replay at 5m OHLC resolution; distinguish uncertain outcomes.

    Entry is assumed filled at given price at start_time. No transaction
    costs; a gap-through target/stop may change realised outcome.
    """
    direction = 1 if side == "BUY" else -1
    stop = entry - direction * STOP_POINTS
    target = entry + direction * TARGET_POINTS
    previous = None
    checked = 0

    for bar in five:
        if bar.ts < start_time:
            continue
        if bar.ts >= start_time + timedelta(minutes=max_minutes):
            return dict(outcome="TIMEOUT", exit_utc=bar.ts.isoformat(),
                        bars_checked=checked, stop=stop, target=target)
        if previous is not None and bar.ts != previous + timedelta(minutes=5):
            return dict(outcome="DATA_GAP", exit_utc=bar.ts.isoformat(),
                        bars_checked=checked, stop=stop, target=target)
        previous = bar.ts
        checked += 1
        stop_hit = bar.l <= stop if side == "BUY" else bar.h >= stop
        tp_hit = bar.h >= target if side == "BUY" else bar.l <= target
        if stop_hit or tp_hit:
            if stop_hit and tp_hit:
                outcome = "AMBIGUOUS_BOTH"
            else:
                outcome = "TP" if tp_hit else "SL"
            return dict(outcome=outcome, exit_utc=bar.ts.isoformat(),
                        bars_checked=checked, stop=stop, target=target,
                        exit_open=bar.o, exit_high=bar.h, exit_low=bar.l,
                        exit_close=bar.c)
    return dict(outcome="NO_MORE_DATA", exit_utc=None, bars_checked=checked,
                stop=stop, target=target)


def load_candidates(datefrom="2026-10-29", dateTo="2026-10-30"):
    """Use unchanged v1 scanner and append causal v2 context."""
    five = base.read_ibkr_5m(base.SOURCES)
    fifteen = base.to_15m(five)
    # Scan all historical candles for indicators and earlier confirmed pivots.
    candidates = [r for r in v1.scan(fifteen)
                  if datefrom <= r["c3_uk"][:10] <= dateTo]
    return five, fifteen, candidates


def validate_all(datefrom="2026-10-29", dateTo="2026-10-30"):
    """Independently replay all candidates, never selecting by v1 GOOD first."""
    five, fifteen, candidates = load_candidates(datefrom, dateTo)
    five_lookup = {bar.ts: bar for bar in five}
    data = []
    for candidate in candidates:
        c3 = fifteen[candidate["_c3_i"]]
        # If 15m group is [C3start, +5m, +10m], its close is available
        # at +15m. The first executable candle STARTS at that timestamp.
        decision_time = c3.ts + timedelta(minutes=15)
        next_bar = five_lookup.get(decision_time)
        record = {
            "c3_uk": candidate["c3_uk"],
            "c3_end_uk": decision_time.astimezone(base.UK).isoformat(timespec="minutes"),
            "side": candidate["side"],
            "c3_close_reference": candidate["c3_close"],
            "v1_decision": candidate["decision"],
            "v1_reason": candidate["reason"],
            "v1_sweep_points": candidate["sweep_points"],
            "v1_c2_wick_body": candidate["c2_wick_body"],
        }
        record.update(structure_v2.market_structure_v2(fifteen, candidate["_c3_i"]))

        # Missing immediate next 5m bar: mark no fill; do not skip forward.
        if next_bar is None:
            record.update(
                next_open=None, next_open_outcome="NO_NEXT_5M_BAR",
                next_open_exit_utc=None, next_open_bars=None,
                next_open_stop=None, next_open_target=None,
                c3_close_outcome="NO_NEXT_5M_BAR",
                c3_close_exit_utc=None, c3_close_bars=None
            )
        else:
            next_open_entry = next_bar.o
            next_open = price_outcome(five, decision_time, candidate["side"],
                                      next_open_entry)
            c3_ref = price_outcome(five, decision_time, candidate["side"],
                                   candidate["c3_close"])
            record.update(
                next_open=next_open_entry,
                next_open_outcome=next_open["outcome"],
                next_open_exit_utc=next_open["exit_utc"],
                next_open_bars=next_open["bars_checked"],
                next_open_stop=next_open["stop"],
                next_open_target=next_open["target"],
                c3_close_outcome=c3_ref["outcome"],
                c3_close_exit_utc=c3_ref["exit_utc"],
                c3_close_bars=c3_ref["bars_checked"],
            )
        data.append(record)
    return data


def print_summary(records):
    """Compare raw winning/losing candidates by observed v1/v2 categories."""
    def print_group(title, field):
        groups = defaultdict(list)
        for r in records:
            groups[r[field]].append(r)
        print("\n" + title)
        print(f"{'GROUP':<25} {'TOTAL':>5} {'TP':>5} {'SL':>5} "
              f"{'AMB':>5} {'OTHER':>6} {'TP/(TP+SL)':>13}")
        for name, rows in sorted(groups.items(), key=lambda x: str(x[0])):
            outcomes = Counter(r["next_open_outcome"] for r in rows)
            tp, sl = outcomes["TP"], outcomes["SL"]
            resolved = tp+sl
            rate = f"{100*tp/resolved:.1f}%" if resolved else "N/A"
            print(f"{str(name):<25} {len(rows):5} {tp:5} {sl:5} "
                  f"{outcomes['AMBIGUOUS_BOTH']:5} "
                  f"{len(rows)-tp-sl-outcomes['AMBIGUOUS_BOTH']:6} {rate:>13}")

    print(f"\nREPLAY: {len(records)} v1 core candidates | "
          f"reference SL={STOP_POINTS}pt TP={TARGET_POINTS}pt | "
          f"max hold={MAX_HOLD_MINUTES}m")
    print("Entry: first 5m OPEN following 15m C3 completion.")
    print("No commissions, slippage, actual fills or overlapping-position limits.")
    print_group("ALL", "side")
    for field in ("v1_decision", "trend", "structure_pattern", "structure_event"):
        print_group(field.upper(), field)
    print("\nSIGNAL-BY-SIGNAL OUTCOMES:")
    for row in records:
        print(f"{row['c3_uk']} {row['side']:<4} "
              f"v1={row['v1_decision']:<4} "
              f"trend={row['trend']:<8} "
              f"shape={row['structure_pattern']:<19} "
              f"event={row['structure_event']:<16} "
              f"open={str(row['next_open']):<8} "
              f"next5m={row['next_open_outcome']:<15} "
              f"c3close={row['c3_close_outcome']}")
    unresolved = Counter(r["next_open_outcome"] for r in records
                         if r["next_open_outcome"] not in ("TP", "SL"))
    print("UNRESOLVED (not winners or losers):", dict(unresolved))
    print("Not an independent set of trades: candidates may overlap; study only.")


def save_csv(records):
    """Preserve the entire comparison for independent visual inspection."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "MES_2026-10-29_30_ALL_candidates_5m_outcomes.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return path


if __name__ == "__main__":
    observations = validate_all()
    print_summary(observations)
    print("\nCSV:", save_csv(observations))
