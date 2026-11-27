#!/usr/bin/env python3
"""RudraEMA5 V3 experimental RSI-rising variant. Does not send orders.

Usage:
  python RudraEMA5/backtest_rsi_rising.py --date 2026-11-25 --rsi-threshold 36
  python RudraEMA5/backtest_rsi_rising.py --date 2026-11-27 --rsi-threshold 36

Experimental V3 adds: RSI14 at completed C1 is strictly greater than RSI14\nof the preceding completed candle. Existing V2 2% swing and RSI<36 remain;
EMA5 falls >=0.15% over 3 bars; entire C1 below EMA5; C2 intrabar
breakout over both C1 close+0.2% and C1 high+$0.02.
Initial SL -1% of entry. When price reaches +1%, retain full position
and trail 0.2% below subsequently attained highs.

OHLC limitations: 5-minute bars do not reveal the exact order of intra-bar
high/low movements. For entry-bar initial-stop ambiguity, assume stop first.
For established stops check at the start of each new bar, before updating
trailing stops. A newly ratcheted stop in a candle only executes intrabar
when that candle's close is already below it, so a post-high stop crossing
is certain. Cases where the high and low both cross a newly formed trail,
but the close does not, have unknown sequencing and require 1m/tick tests.
No fees, spreads, borrow costs or slippage are included.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from filter_audit import DEFAULT_CSV, add_indicators, entry_trigger, load


def replay(bars: list[dict], selected_day: date, rsi_threshold: float = 36.0,
           min_swing_down_pct: float = 2.0) -> dict:
    trades = []
    candidate_count = swing_count = rsi_count = 0
    open_trade = None
    day_bars = [bar for bar in bars if bar["time"].date() == selected_day]
    if not day_bars:
        raise ValueError(f"No candles for {selected_day}")

    def finish(bar: dict, exit_price: float, reason: str) -> None:
        nonlocal open_trade
        assert open_trade is not None
        result = dict(open_trade)
        result.update({
            "exit_time_uk": bar["time"].isoformat(),
            "exit_price": round(exit_price, 5),
            "exit_reason": reason,
            "result_R": round(100.0 * (exit_price / result["entry_price"] - 1), 6),
            "result_price_pct": round(100.0 * (exit_price / result["entry_price"] - 1), 6),
        })
        trades.append(result)
        open_trade = None

    for i in range(25, len(bars)):
        c2 = bars[i]
        if c2["time"].date() > selected_day:
            break
        if c2["time"].date() < selected_day:
            continue

        if open_trade is not None:
            stop = open_trade["active_stop"]
            if c2["open"] <= stop:
                finish(c2, c2["open"], "gap_through_stop")
                continue
            if c2["low"] <= stop:
                finish(c2, stop, "trailing_stop" if open_trade["armed"] else "initial_stop")
                continue
            if not open_trade["armed"] and c2["high"] >= open_trade["entry_price"] * 1.01:
                open_trade["armed"] = True
                open_trade["peak"] = c2["high"]
            if open_trade["armed"]:
                open_trade["peak"] = max(open_trade["peak"], c2["high"])
                new_stop = max(open_trade["active_stop"], open_trade["peak"] * 0.998)
                if c2["close"] <= new_stop:
                    finish(c2, new_stop, "trail_same_bar_close_confirmation")
                    continue
                open_trade["active_stop"] = new_stop
            continue

        c1, three_bars_earlier = bars[i - 1], bars[i - 4]
        if (c2["time"] - c1["time"]).total_seconds() != 300:
            continue
        if (c1["time"] - three_bars_earlier["time"]).total_seconds() != 900:
            continue
        ema_slope_pct = (c1["ema5"] / three_bars_earlier["ema5"] - 1) * 100
        if c1["high"] >= c1["ema5"] or ema_slope_pct > -0.15:
            continue

        candidate_count += 1
        prior_high = max(b["high"] for b in bars[i - 25:i - 1])
        swing_down_pct = (prior_high - c1["low"]) / prior_high * 100
        if swing_down_pct < min_swing_down_pct:
            continue
        swing_count += 1

        rsi = c1["rsi14"]
        previous_rsi = bars[i - 2]["rsi14"]
        if rsi is None or previous_rsi is None or rsi >= rsi_threshold or rsi <= previous_rsi:
            continue
        rsi_count += 1

        threshold = entry_trigger(c1)
        if c2["high"] < threshold:
            continue

        entry = max(c2["open"], threshold)
        open_trade = {
            "c1_time_uk": c1["time"].isoformat(),
            "entry_time_uk": c2["time"].isoformat(),
            "entry_price": round(entry, 5),
            "rsi14_at_c1": round(rsi, 4),
            "rsi14_previous": round(previous_rsi, 4),
            "swing_down_pct": round(swing_down_pct, 4),
            "entry_trigger": threshold,
            "initial_stop": round(entry * 0.99, 5),
            "active_stop": entry * 0.99,
            "armed": False,
            "peak": entry,
        }
        if c2["low"] <= open_trade["active_stop"]:
            finish(c2, open_trade["active_stop"], "entry_bar_ambiguous_initial_stop_first")
            continue
        if c2["high"] >= entry * 1.01:
            open_trade["armed"] = True
            open_trade["peak"] = c2["high"]
            new_stop = max(open_trade["active_stop"], c2["high"] * 0.998)
            if c2["close"] <= new_stop:
                finish(c2, new_stop, "entry_bar_trail_close_confirmation")
                continue
            open_trade["active_stop"] = new_stop

    if open_trade is not None:
        finish(day_bars[-1], day_bars[-1]["close"], "end_of_day_mark_to_market")

    wins = [x for x in trades if x["result_R"] > 0]
    losses = [x for x in trades if x["result_R"] < 0]
    return {
        "ticker": "COHR", "date_uk": str(selected_day), "timeframe": "5min",
        "session": "IBKR available extended hours",
        "c2_low_filter_enabled": False,
        "swing_min_pct": min_swing_down_pct,
        "rsi_max_exclusive": rsi_threshold,
        "rsi_must_be_rising_at_c1": True,
        "strategy_version": "V3 experimental; V2 remains the dashboard default",
        "day_candles": len(day_bars),
        "c1_candidates_reachable_without_open_position": candidate_count,
        "swing_passes": swing_count, "swing_and_rsi_passes": rsi_count,
        "trades": len(trades), "wins": len(wins), "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / len(trades), 4) if trades else None,
        "sum_R": round(sum(x["result_R"] for x in trades), 6),
        "compounded_full_allocation_pct": round(
            100 * (
                __import__("functools").reduce(
                    lambda eq, t: eq * (1 + t["result_price_pct"] / 100),
                    trades, 1.0
                ) - 1), 6
        ),
        "execution_caveat": "5m OHLC inferred fills and trailing stops are not tick-confirmed",
        "fills": trades,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, default=date(2026, 11, 25))
    parser.add_argument("--rsi-threshold", type=float, default=36.0)
    parser.add_argument("--min-swing-down-pct", type=float, default=2.0)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--cutoff", type=datetime.fromisoformat,
                        default=datetime.fromisoformat("2026-11-27T18:00:00+00:00"))
    args = parser.parse_args()
    if args.cutoff.tzinfo is None:
        parser.error("--cutoff must include a timezone offset")
    bars = load(args.csv, args.cutoff.astimezone(timezone.utc))
    add_indicators(bars)
    print(json.dumps(replay(bars, args.date, args.rsi_threshold,
                            args.min_swing_down_pct), indent=2))


if __name__ == "__main__":
    main()
