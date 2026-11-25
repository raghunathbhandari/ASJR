#!/usr/bin/env python3
"""ASJR AlgoWithRenko: reproducible, research-only MES Renko backtest.

Standard-library only. Signals: 15-minute CLOSE-based synthetic Renko.
Fills: next 15-minute OPEN. Stops: 5-minute OHLC, including gap-through fills.
No actual broker orders and no claims of tick-accurate Renko.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "three_candle" / "data"


@dataclass
class Bar:
    t: datetime
    o: float
    h: float
    l: float
    c: float
    subs: list[tuple[datetime, float, float, float, float]]


def read_bars(folder: Path = DEFAULT_DATA, pattern: str = "MESZ2026_IBKR_5m_2026-*.csv") -> list[Bar]:
    five = []
    paths = sorted(folder.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No data files found: {folder / pattern}")
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                t = datetime.fromisoformat(row["Datetime_UTC"].replace("Z", "+00:00"))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=UTC)
                t = t.astimezone(UTC)
                five.append((t, float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])))
    five.sort(key=lambda x: x[0])
    if any(five[i][0] == five[i - 1][0] for i in range(1, len(five))):
        raise ValueError("Duplicate 5-minute timestamps detected. Verify source files.")
    groups: dict[datetime, Bar] = {}
    for t, o, h, l, c in five:
        start = t.replace(minute=t.minute // 15 * 15, second=0, microsecond=0)
        if start not in groups:
            groups[start] = Bar(start, o, h, l, c, [])
        b = groups[start]
        b.h = max(b.h, h)
        b.l = min(b.l, l)
        b.c = c
        b.subs.append((t, o, h, l, c))
    incomplete = [b for b in groups.values() if len(b.subs) != 3]
    if incomplete:
        raise ValueError(f"{len(incomplete)} incomplete 15-minute groups: fix source data first")
    return sorted(groups.values(), key=lambda b: b.t)


def indicators(bars: list[Bar], period: int = 14) -> tuple[list[float | None], list[float | None]]:
    """Wilder RSI and Wilder ADX on underlying 15-minute OHLC (not bricks)."""
    n = len(bars)
    rsis: list[float | None] = [None] * n
    adxs: list[float | None] = [None] * n
    if n < 2 * period:
        return rsis, adxs
    avg_gain = avg_loss = smooth_tr = smooth_plus = smooth_minus = dx_sum = 0.0
    for i in range(1, n):
        current, previous = bars[i], bars[i - 1]
        gain = max(0.0, current.c - previous.c)
        loss = max(0.0, previous.c - current.c)
        tr = max(current.h - current.l, abs(current.h - previous.c), abs(current.l - previous.c))
        up_move = current.h - previous.h
        down_move = previous.l - current.l
        plus = up_move if up_move > down_move and up_move > 0 else 0.0
        minus = down_move if down_move > up_move and down_move > 0 else 0.0
        if i <= period:
            avg_gain += gain
            avg_loss += loss
            smooth_tr += tr
            smooth_plus += plus
            smooth_minus += minus
            if i == period:
                avg_gain /= period
                avg_loss /= period
        else:
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            smooth_tr = smooth_tr - smooth_tr / period + tr
            smooth_plus = smooth_plus - smooth_plus / period + plus
            smooth_minus = smooth_minus - smooth_minus / period + minus
        if i < period:
            continue
        rsis[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
        di_plus = 100.0 * smooth_plus / smooth_tr if smooth_tr else 0.0
        di_minus = 100.0 * smooth_minus / smooth_tr if smooth_tr else 0.0
        dx = 100.0 * abs(di_plus - di_minus) / (di_plus + di_minus) if di_plus + di_minus else 0.0
        if i < 2 * period - 1:
            dx_sum += dx
        elif i == 2 * period - 1:
            dx_sum += dx
            adxs[i] = dx_sum / period
        else:
            assert adxs[i - 1] is not None
            adxs[i] = (adxs[i - 1] * (period - 1) + dx) / period
    return rsis, adxs


def renko_events(bars: list[Bar], brick: float) -> tuple[dict[int, list[dict]], int]:
    """2-brick reversal, 15-minute close-only bricks. Multiple per bar allowed."""
    if brick <= 0:
        raise ValueError("Brick size must be positive")
    level = round(bars[0].c / brick) * brick
    direction = run = prev = prev2 = 0
    events: dict[int, list[dict]] = {}
    count = 0
    for i in range(1, len(bars)):
        close = bars[i].c
        current = []

        def push(new_direction: int, new_close: float, reverse: bool = False) -> None:
            nonlocal direction, run, prev, prev2, level, count
            if new_direction != direction:
                prev2, prev = prev, run
                run = 0
            run += 1
            current.append({"d": new_direction, "c": new_close, "reverse": reverse,
                            "run": run, "prev": prev, "prev2": prev2})
            direction, level = new_direction, new_close
            count += 1

        if direction == 0:
            while close >= level + brick:
                push(1, level + brick)
            while close <= level - brick:
                push(-1, level - brick)
        elif direction == 1:
            if close <= level - 2 * brick:
                push(-1, level - 2 * brick, True)
                while close <= level - brick:
                    push(-1, level - brick)
            else:
                while close >= level + brick:
                    push(1, level + brick)
        else:
            if close >= level + 2 * brick:
                push(1, level + 2 * brick, True)
                while close >= level + brick:
                    push(1, level + brick)
            else:
                while close <= level - brick:
                    push(-1, level - brick)
        if current:
            events[i] = current
    return events, count


def run_backtest(bars: list[Bar], *, brick: float = 20, stop: float = 20,
                 entry_brick: int = 2, chop_screen: bool = True,
                 filter_mode: str = "rsi-adx", cutoff: datetime | None = None) -> tuple[list[dict], dict]:
    """Replay earliest data as warmup. Cutoff is exclusive; EOM close at last candle."""
    if stop <= 0 or entry_brick < 1:
        raise ValueError("Stop must be positive; entry brick must be >= 1")
    if filter_mode not in ("none", "rsi-adx"):
        raise ValueError("filter_mode must be none or rsi-adx")
    rsis, adxs = indicators(bars)
    events, brick_count = renko_events(bars, brick)
    position = None
    pending = None
    trades: list[dict] = []
    passed = rejected = 0
    last = None

    def close(t: datetime, price: float, why: str) -> None:
        nonlocal position
        assert position is not None
        p = position
        trades.append({"entry_time": p["t"].isoformat(), "exit_time": t.isoformat(),
                       "side": "BUY" if p["d"] > 0 else "SHORT",
                       "entry_price": p["price"], "exit_price": price,
                       "points": round((price - p["price"]) * p["d"], 2),
                       "exit_reason": why, "signal_rsi": p["rsi"], "signal_adx": p["adx"]})
        position = None

    for i in range(1, len(bars)):
        b = bars[i]
        if cutoff is not None and b.t >= cutoff:
            break
        last = b
        if pending is not None:
            if position is not None:
                close(b.t, b.o, "opposite_brick")
            if pending["action"] == "entry":
                position = {"t": b.t, "price": b.o, "d": pending["d"],
                            "sl": b.o - pending["d"] * stop,
                            "rsi": pending["rsi"], "adx": pending["adx"]}
            pending = None
        if position is not None:
            for t, o, high, low, _ in b.subs:
                if position is not None and (low <= position["sl"] if position["d"] > 0 else high >= position["sl"]):
                    fill = min(o, position["sl"]) if position["d"] > 0 else max(o, position["sl"])
                    close(t, fill, "stop")
                    break
        for event in events.get(i, []):
            if event["reverse"] and position is not None:
                pending = {"action": "exit"}
            if event["run"] != entry_brick:
                continue
            if entry_brick == 1 and not event["reverse"]:
                continue
            if chop_screen and event["prev"] <= 1 and event["prev2"] <= 1:
                rejected += 1
                continue
            rsi, adx = rsis[i], adxs[i]
            valid = filter_mode == "none" or (
                rsi is not None and adx is not None and adx >= 30
                and (rsi >= 50 if event["d"] > 0 else rsi >= 20)
            )
            if not valid:
                rejected += 1
                continue
            passed += 1
            if position is None or position["d"] != event["d"]:
                pending = {"action": "entry", "d": event["d"], "rsi": rsi, "adx": adx}
    if position is not None and last is not None:
        close(last.t + timedelta(minutes=15), last.c, "end_of_data")
    return trades, {"renko_bricks_all_data": brick_count, "signals_passed": passed, "signals_rejected": rejected}


def summarize(trades: list[dict], month: str) -> dict:
    chosen = [x for x in trades if x["entry_time"].startswith(month)]
    winners = [x for x in chosen if x["points"] > 0]
    losers = [x for x in chosen if x["points"] < 0]
    gross_w = sum(x["points"] for x in winners)
    gross_l = -sum(x["points"] for x in losers)
    equity = peak = drawdown = 0.0
    for trade in chosen:
        equity += trade["points"]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    net = round(sum(x["points"] for x in chosen), 2)
    return {"month": month, "trades": len(chosen), "winners": len(winners), "losers": len(losers),
            "breakeven": len(chosen) - len(winners) - len(losers),
            "win_rate_pct": round(len(winners) / len(chosen) * 100, 2) if chosen else 0.0,
            "net_mes_points": net, "gross_usd_1_mes": round(net * 5, 2),
            "profit_factor": round(gross_w / gross_l, 2) if gross_l else None,
            "max_closed_trade_drawdown_pts": round(drawdown, 2),
            "trades_detail": chosen}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True, help="YYYY-MM, e.g. 2026-09")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--pattern", default="MESZ2026_IBKR_5m_2026-*.csv")
    parser.add_argument("--filter", choices=("none", "rsi-adx"), default="rsi-adx")
    parser.add_argument("--brick", type=float, default=20.0)
    parser.add_argument("--stop", type=float, default=20.0)
    parser.add_argument("--entry-brick", type=int, default=2)
    parser.add_argument("--no-chop-screen", action="store_true")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    start = datetime.strptime(args.month, "%Y-%m").replace(tzinfo=UTC)
    cutoff = (start.replace(year=start.year + 1, month=1) if start.month == 12
              else start.replace(month=start.month + 1))
    bars = read_bars(args.data_dir, args.pattern)
    trades, diagnostics = run_backtest(bars, brick=args.brick, stop=args.stop,
                                       entry_brick=args.entry_brick,
                                       chop_screen=not args.no_chop_screen,
                                       filter_mode=args.filter, cutoff=cutoff)
    report = summarize(trades, args.month)
    report["setup"] = {"contract": "MESZ2026", "source_candle_minutes": 15,
                       "renko_close_based": True, "brick": args.brick, "stop_points": args.stop,
                       "entry_brick": args.entry_brick, "chop_screen": not args.no_chop_screen,
                       "indicator_filter": args.filter}
    report["diagnostics"] = diagnostics
    print(json.dumps(report, indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
