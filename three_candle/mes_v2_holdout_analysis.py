#!/usr/bin/env python3
"""MES v2 held-out historical period checks: structure hypotheses fixed in advance.

Derivation set: Oct 29-30 2026, independent candidate replay outcomes.
Comparison set: September 2026 and Oct 1-28 (historically earlier, NOT
prospective forward validation). Preserve original v1 and input CSVs.
No threshold optimization or inferred institutional activity.
"""
import csv
from collections import Counter, defaultdict
from pathlib import Path

from mes_v2_validate_all_outcomes import validate_all, print_summary

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "MES_v2_research"

# Hypotheses are PREDECLARED based on Oct 29-30 observations.
def hypothesis_masks(row):
    """A few simple price-context hypotheses; same across all windows."""
    aligned = (row["side"] == "BUY" and row["trend"] == "BULLISH") or (
        row["side"] == "SELL" and row["trend"] == "BEARISH")
    return {
        "ALL": True,
        "NO_V_BOTTOM": row["structure_pattern"] != "V_BOTTOM_DEVELOPING",
        "TREND_ALIGNED": aligned,
        "TREND_ALIGNED_NO_V_BOTTOM": aligned and row["structure_pattern"] != "V_BOTTOM_DEVELOPING",
        "V1_GOOD": row["v1_decision"] == "GOOD",
    }


def summarise(rows, period):
    """Print resolution-aware TP rates; no unresolved counted as losses."""
    grouped = defaultdict(list)
    for row in rows:
        for name, include in hypothesis_masks(row).items():
            if include:
                grouped[name].append(row)
    print("\n=== " + period + " | " + str(len(rows)) + " v1 candidates ===")
    for name, group in grouped.items():
        outcomes = Counter(r["next_open_outcome"] for r in group)
        tp, sl = outcomes["TP"], outcomes["SL"]
        unresolved = len(group) - tp - sl
        winrate = f"{tp / (tp+sl)*100:.1f}%" if tp+sl else "N/A"
        nominal_r = tp * 2 - sl
        print(f"{name:<29} total={len(group):>4} TP={tp:>4} SL={sl:>4} "
              f"unresolved={unresolved:>3} tp_rate={winrate:<6} "
              f"gross_candidate_R={nominal_r:+d}")
    print("Daily totals:")
    days = sorted({r["c3_uk"][:10] for r in rows})
    for day in days:
        subset = [r for r in rows if r["c3_uk"].startswith(day)]
        outcome = Counter(r["next_open_outcome"] for r in subset)
        print(day, "candidates", len(subset), dict(outcome))
    return grouped


def write_csv(rows, name):
    OUT.mkdir(parents=True, exist_ok=True)
    if not rows:
        return None
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("CSV", path)
    return path


if __name__ == "__main__":
    # First test not used to select parameter thresholds in this script.
    development = validate_all("2026-10-29", "2026-10-30")
    summarise(development, "29-30 Oct RESEARCH")
    write_csv(development, "MES_Oct29_30_outcome_research.csv")
    holdout_sep = validate_all("2026-09-01", "2026-09-30")
    summarise(holdout_sep, "Sep HISTORICAL HOLDOUT")
    write_csv(holdout_sep, "MES_Sept_2026_heldout_outcomes.csv")
    holdout_oct = validate_all("2026-10-01", "2026-10-28")
    summarise(holdout_oct, "Oct01_28 HISTORICAL HOLDOUT")
    write_csv(holdout_oct, "MES_Oct01_28_2026_heldout_outcomes.csv")
    print("Note: all stats hypothetical independent candidate signals, not portfolio P&L.")
