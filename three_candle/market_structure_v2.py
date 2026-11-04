#!/usr/bin/env python3
"""Rudra MES v2: causal market-structure research, v1 remains unchanged.

Classify structure at each completed 15m bar, then annotate ALL v1 core
candidates (GOOD and WAIT). Information only; no new trade filtering.
Uses earlier September/October IBKR 5m history for pivot/ATR warm-up.
"""
import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import mes_relax_structure_first_v1 as base
import mes_relax_pipeline_v1 as v1

# Research parameters only. Change after visual verification, not as filters.
ATR_PERIOD = 14
V_LOOKBACK = 16                 # recent 15m bars examined for reversal shape
V_IMPULSE_ATR = 1.5             # directional impulse relative to ATR14
V_RECOVERY_RATIO = 0.50         # rebound/rejection >= 50% of impulse
V_MAX_RECOVERY_BARS = 8         # speed requirement
MIN_BREAK_POINTS = 0.25         # close beyond swing level (MES tick)
ROOT = Path(__file__).resolve().parent


def atr_at(bars, index):
    """ATR14 average true range through index, no future or partial seed."""
    if index < ATR_PERIOD:
        return None
    ranges = []
    for i in range(index - ATR_PERIOD + 1, index + 1):
        bar, prior = bars[i], bars[i - 1]
        ranges.append(max(bar.h - bar.l, abs(bar.h - prior.c),
                          abs(bar.l - prior.c)))
    return sum(ranges) / len(ranges)


def latest_structure_break(bars, index, highs, lows, prior_trend):
    """Describe a fresh close crossing a previously confirmed pivot level.

    Only a first cross on THIS bar counts; previous close was not beyond.
    A countertrend first cross is labelled CHOCH, continuation BOS.
    If prior trend is mixed, retain BREAK_UP/BREAK_DOWN rather than guessing.
    """
    if index == 0:
        return "NONE", None
    previous_close, close = bars[index - 1].c, bars[index].c
    eligible_highs = [(i, p) for i, p in highs
                      if i + base.SWING_RIGHT <= index - 1]
    eligible_lows = [(i, p) for i, p in lows
                     if i + base.SWING_RIGHT <= index - 1]
    up = [(i, price) for i, price in eligible_highs
          if previous_close <= price and close > price + MIN_BREAK_POINTS]
    down = [(i, price) for i, price in eligible_lows
            if previous_close >= price and close < price - MIN_BREAK_POINTS]
    if up:
        price = max(up, key=lambda item: item[1])[1]
        if prior_trend == "BEARISH":
            return "BULLISH_CHOCH", price
        if prior_trend == "BULLISH":
            return "BULLISH_BOS", price
        return "BREAK_UP", price
    if down:
        price = min(down, key=lambda item: item[1])[1]
        if prior_trend == "BULLISH":
            return "BEARISH_CHOCH", price
        if prior_trend == "BEARISH":
            return "BEARISH_BOS", price
        return "BREAK_DOWN", price
    return "NONE", None


def v_shape_at(bars, index, atr):
    """Developing V shape: fast meaningful counter-impulse from a recent extreme.

    No future pivot confirmation required for shape observation. The
    extreme MUST have occurred before the current close. Do not call this
    confirmed CHOCH or claim future price completion. An early recovery can
    still be in a bearish market; both labels must be kept separately.
    """
    if atr is None or atr == 0 or index < V_LOOKBACK:
        return "NONE", None, None, None
    first = max(0, index - V_LOOKBACK)
    window = bars[first:index + 1]
    low_idx = min(range(first, index), key=lambda i: bars[i].l)
    high_idx = max(range(first, index), key=lambda i: bars[i].h)
    low = bars[low_idx].l
    high = bars[high_idx].h

    # V-bottom requires decline into the low, then recovery after that low.
    if first < low_idx < index and index - low_idx <= V_MAX_RECOVERY_BARS:
        prior_high = max(b.h for b in bars[first:low_idx])
        decline = prior_high - low
        recovery = bars[index].c - low
        if decline >= V_IMPULSE_ATR * atr and recovery >= V_RECOVERY_RATIO * decline:
            return "V_BOTTOM_DEVELOPING", low, recovery / decline * 100, index - low_idx

    # Inverted V-top: rise into high then fast downward recovery/rejection.
    if first < high_idx < index and index - high_idx <= V_MAX_RECOVERY_BARS:
        prior_low = min(b.l for b in bars[first:high_idx])
        impulse = high - prior_low
        rejection = high - bars[index].c
        if impulse >= V_IMPULSE_ATR * atr and rejection >= V_RECOVERY_RATIO * impulse:
            return "V_TOP_DEVELOPING", high, rejection / impulse * 100, index - high_idx
    return "NONE", None, None, None


def market_structure_v2(bars, current_index):
    """Return market context as independent trend + shape + break fields.

    A snapshot uses candles 0..current_index ONLY, completed confirmed
    swing pivots, no future bars. Never rejects a trade.
    """
    if not 0 <= current_index < len(bars):
        raise IndexError("current_index outside candle series")
    highs, lows = base.confirmed_pivots(bars, current_index)
    # The break event references prior bar's already-confirmed context.
    previous_highs, previous_lows = base.confirmed_pivots(bars, max(0, current_index - 1))
    previous_trend = base.classify_structure(previous_highs, previous_lows)
    trend = base.classify_structure(highs, lows)
    atr = atr_at(bars, current_index)
    shape, turning_price, recovery_pct, recovery_bars = v_shape_at(
        bars, current_index, atr)
    event, broken_level = latest_structure_break(
        bars, current_index, highs, lows, previous_trend)
    bar = bars[current_index]
    return {
        "uk_time": bar.ts.astimezone(base.UK).isoformat(timespec="minutes"),
        "trend": trend,
        "previous_trend": previous_trend,
        "structure_pattern": shape,
        "structure_event": event,
        "break_level": broken_level,
        "last_swing_high": highs[-1][1] if highs else None,
        "last_swing_low": lows[-1][1] if lows else None,
        "confirmed_swing_highs": len(highs),
        "confirmed_swing_lows": len(lows),
        "atr14_points": round(atr, 4) if atr is not None else None,
        "v_turning_price": turning_price,
        "v_recovery_pct": round(recovery_pct, 2) if recovery_pct is not None else None,
        "v_recovery_bars": recovery_bars,
    }


def analyse_mes_29_30(datefrom="2026-10-29", dateTo="2026-10-30"):
    """Align v2 structure snapshots with every UNMODIFIED v1 core candidate.

    Scans all available earlier history; stores classification from each
    C3 close, instead of using end-of-day hindsight.
    """
    if date.fromisoformat(dateTo) < date.fromisoformat(datefrom):
        raise ValueError("dateTo before datefrom")
    bars = base.to_15m(base.read_ibkr_5m(base.SOURCES))
    if not bars:
        raise FileNotFoundError("MES historical CSV missing")
    original = v1.scan(bars)
    selected = [row for row in original
                if datefrom <= row["c3_uk"][:10] <= dateTo]
    records = []
    for row in selected:
        structure = market_structure_v2(bars, row["_c3_i"])
        report = {
            "side": row["side"],
            "c2_uk": row["c2_uk"],
            "c3_uk": row["c3_uk"],
            "c3_close": row["c3_close"],
            "v1_decision": row["decision"],
            "v1_reasons": row["reason"],
            "v1_market_structure": row["market_structure"],
            **structure,
        }
        records.append(report)
    return bars, records


def print_report(records):
    """Compact visible comparison of every candidate and its v2 context."""
    by_day = defaultdict(list)
    for row in records:
        by_day[row["c3_uk"][:10]].append(row)
    for day, rows in sorted(by_day.items()):
        print(f"\n{day}: {len(rows)} CORE, "
              f"{sum(r['v1_decision'] == 'GOOD' for r in rows)} GOOD")
        print("TIME UK   SIDE   V1   TREND      PATTERN                 EVENT              PRICE")
        for r in rows:
            time = r["c3_uk"][11:16]
            print(f"{time:<9} {r['side']:<6} {r['v1_decision']:<5} "
                  f"{r['trend']:<10} {r['structure_pattern']:<23} "
                  f"{r['structure_event']:<18} {r['c3_close']:.2f}")
        print("Trend distribution:", dict(Counter(r["trend"] for r in rows)))
        print("V-shapes:", dict(Counter(r["structure_pattern"] for r in rows
                                        if r["structure_pattern"] != "NONE")))
        print("Break events:", dict(Counter(r["structure_event"] for r in rows
                                            if r["structure_event"] != "NONE")))


def save_csv(records, path):
    """Export every candidate snapshot for later visual chart validation."""
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)



def plot_structure_days(bars, records, output_dir):
    """Draw one MES candlestick overview per day with v1 + v2 annotations.

    Purple dots = original v1 candidate C2. Gold diamonds = v1 GOOD C3.
    Cyan triangles = developing V bottoms, orange inverted triangles = V tops.
    Structure-break events are annotated only at the C3 they occur.
    These are research snapshots, not trade confirmations.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    output_dir.mkdir(parents=True, exist_ok=True)
    dates = sorted({row["c3_uk"][:10] for row in records})
    for day in dates:
        day_indices = [i for i, bar in enumerate(bars)
                       if bar.ts.astimezone(base.UK).date().isoformat() == day]
        if not day_indices:
            continue
        start, end = day_indices[0], day_indices[-1]
        rows = [row for row in records if row["c3_uk"][:10] == day]
        fig, ax = plt.subplots(figsize=(21, 10), facecolor="#101722")
        ax.set_facecolor("#101722")
        ax.tick_params(colors="#dbe5f0")
        ax.grid(color="#526174", alpha=0.25)
        for i in range(start, end + 1):
            b = bars[i]
            colour = "#23c985" if b.c >= b.o else "#ff6471"
            ax.vlines(i - start, b.l, b.h, color=colour, lw=0.85)
            ax.add_patch(Rectangle((i - start - 0.3, min(b.o, b.c)),
                         0.6, max(abs(b.c - b.o), 0.01),
                         facecolor=colour, edgecolor=colour))
        # Index lookup avoids time-string conversions or assumptions.
        lookup = {bar.ts.astimezone(base.UK).isoformat(timespec="minutes"): i
                  for i, bar in enumerate(bars[start:end + 1], start)}
        legend_seen = set()
        def marker(x, y, shape, colour, label, size):
            shown = label if label not in legend_seen else None
            legend_seen.add(label)
            ax.scatter(x, y, marker=shape, color=colour, s=size,
                       edgecolors="#e2e8f0", linewidths=0.65,
                       zorder=8, label=shown)
        for row in rows:
            c2_idx = lookup.get(row["c2_uk"][:22])
            if c2_idx is not None:
                c2_bar = bars[c2_idx]
                ypos = c2_bar.l - 0.75 if row["side"] == "BUY" else c2_bar.h + 0.75
                marker(c2_idx-start, ypos, "o", "#c084fc", "V1 candidate C2", 30)
            idx = lookup.get(row["c3_uk"][:22])
            if idx is None:
                continue
            b = bars[idx]
            x = idx - start
            if row["v1_decision"] == "GOOD":
                marker(x, b.c, "D", "#facc15", "V1 GOOD C3", 95)
            if row["structure_pattern"] == "V_BOTTOM_DEVELOPING":
                marker(x, b.l - 2, "^", "#2dd4bf", "V-bottom developing", 65)
            if row["structure_pattern"] == "V_TOP_DEVELOPING":
                marker(x, b.h + 2, "v", "#fb923c", "V-top developing", 65)
            event = row["structure_event"]
            if event != "NONE":
                ax.annotate(event.replace("BULLISH_", "B+").replace("BEARISH_", "B-"),
                            (x, b.h), xytext=(0, 15), textcoords="offset points",
                            ha="center", fontsize=7, color="#f8fafc",
                            rotation=40)
        ticks = list(range(0, end-start+1, max(1, (end-start+1)//18)))
        ax.set_xticks(ticks, [
            bars[start+i].ts.astimezone(base.UK).strftime("%H:%M")
            for i in ticks], rotation=35, ha="right")
        ax.set_xlim(-1, end-start+2)
        ax.set_ylabel("MES futures", color="#dbe5f0")
        ax.set_title(f"MES v2 structure research | {day} UK | "
                     f"{len(rows)} v1 CORE candidates", color="white", fontsize=14)
        if legend_seen:
            ax.legend(facecolor="#1a2534", edgecolor="#526174", labelcolor="white")
        fig.tight_layout()
        path = output_dir / f"MES_{day}_v2_structure.png"
        fig.savefig(path, dpi=145, facecolor=fig.get_facecolor())
        plt.close(fig)
        print("CHART:", path)

if __name__ == "__main__":
    bars, records = analyse_mes_29_30()
    print_report(records)
    path = ROOT / "results" / "MES_v2_research" / "MES_2026-10-29_30_structure_v2.csv"
    save_csv(records, path)
    plot_structure_days(bars, records, path.parent)
    print("\nWritten:", path)
    print("NOTE: v2 exploratory classifications are NOT profitability results.")
