#!/usr/bin/env python3
"""ASJR HotSector — replay of the November 2026 09:45 ET long strategy.

Reproducible, Python-standard-library research; no broker API and no orders.
Input data: local November master CSV and IBKR 5m CSV paths inside Git repo.
CAUTION: the daily 10-stock universe was picked using FULL-DAY web returns:
look-ahead bias. This is an exploratory candidate-shortlist replay, not a
point-in-time tradable strategy. OHLC price paths are unknowable inside 5m bars.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = "Rudra-HotSectorHotStock/november_2026_daily_top10_stocks.csv"
LEADERS = "Rudra-HotSectorHotStock/november_2026_sector_leaders.csv"


def csv_read(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def price_bars(path: Path, session: str):
    rows = csv_read(path)
    all_bars = []
    for row in rows:
        stamp = datetime.fromisoformat(row["Datetime_UTC"])
        if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError(f"UTC stamp required: {path}")
        if stamp.date().isoformat() != session:
            continue
        hm = stamp.strftime("%H:%M")
        if "14:30" <= hm <= "20:55":
            all_bars.append({
                "stamp": stamp, "hm": hm,
                "o": float(row["Open"]), "h": float(row["High"]),
                "l": float(row["Low"]), "c": float(row["Close"]),
                "v": float(row["Volume"]),
            })
    if len(all_bars) != 78 or all_bars[0]["hm"] != "14:30" or all_bars[-1]["hm"] != "20:55":
        raise ValueError(f"78 regular-session 5m bars required: {session} {path}: got {len(all_bars)}")
    for n, row in enumerate(all_bars):
        if n and (row["stamp"] - all_bars[n-1]["stamp"]).total_seconds() != 300:
            raise ValueError(f"Missing 5-minute interval: {session} {path} {n}")
        if not (row["l"] <= min(row["o"], row["c"]) <= max(row["o"], row["c"]) <= row["h"]):
            raise ValueError(f"Invalid OHLC: {session} {path} {n}")
    return all_bars


def replay(bars: list[dict], path_model: str):
    """Replay O-L-H-C or O-H-L-C for each bar, updating stops at +1% steps.

    At each segment, the previous protective stop is checked as the price
    moves down. Rising price triggers +1% gain milestones. At n=1 stop is
    entry, at n=2 stop is entry +1%, etc. A gap through a stop fills at the
    observable new open rather than at an inaccessible old stop.
    """
    if len(bars) != 75 or bars[0]["hm"] != "14:45" or bars[-1]["hm"] != "20:55":
        raise ValueError("Expected all 75 bars from 14:45–20:55 UK")
    entry = bars[0]["o"]
    if entry <= 0:
        raise ValueError("Invalid entry")
    stop = entry * .99
    level = 0
    last_close = entry

    def advance(price):
        nonlocal stop, level
        # Upgrade all crossed milestones, including if opening gap jumps
        # above the previous high or multiple levels at once.
        while level < 100 and price + 1e-9 >= entry*(1+(level+1)/100):
            level += 1
            stop = max(stop, entry*(1+(level-1)/100))

    for bar in bars:
        # Treat a gap through the existing stop as filled at this bar's open.
        if bar["o"] <= stop + 1e-9:
            return dict(entry=entry, exit=bar["o"], exit_time=bar["hm"],
                        reason="GAP_STOP", milestone=level,
                        pct=100*(bar["o"]/entry - 1))
        # An opening gap higher also upgrades protective stop immediately.
        if bar["o"] > last_close:
            advance(bar["o"])
        points = ([bar["o"], bar["l"], bar["h"], bar["c"]]
                  if path_model == "LOW_FIRST" else
                  [bar["o"], bar["h"], bar["l"], bar["c"]])
        for start, end in zip(points, points[1:]):
            if end > start:
                advance(end)
            elif end < start:
                if start <= stop + 1e-9:
                    fill = start  # stop was crossed by preceding gap/segment
                elif end <= stop + 1e-9:
                    fill = stop
                else:
                    continue
                return dict(entry=entry, exit=fill, exit_time=bar["hm"],
                            reason="STOP", milestone=level,
                            pct=100*(fill/entry - 1))
        last_close = bar["c"]

    exit_price = bars[-1]["c"]
    return dict(entry=entry, exit=exit_price, exit_time=bars[-1]["hm"],
                reason="EOD", milestone=level, pct=100*(exit_price/entry - 1))


def aggregate(trades: list[dict], key: str):
    returns = [r[key]["pct"] for r in trades]
    wins = sum(x > 1e-9 for x in returns)
    losses = sum(x < -1e-9 for x in returns)
    zero = len(returns) - wins - losses
    gains = sum(x for x in returns if x > 0)
    losses_gross = -sum(x for x in returns if x < 0)
    balance = peak = 1.0
    drawdown = 0.
    for ret in returns:
        balance *= (1+ret/100)
        peak = max(peak, balance)
        drawdown = min(drawdown, 100*(balance/peak - 1))
    return dict(trades=len(returns), wins=wins, losses=losses,
                flat=zero, win_rate=100*wins/len(returns),
                sum_pct=sum(returns), avg_pct=sum(returns)/len(returns),
                compounded_pct=100*(balance-1), max_dd_pct=drawdown,
                profit_factor=(gains/losses_gross if losses_gross else float("inf")))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, help="Write day-wise CSV (optional)")
    args = parser.parse_args()
    repo = args.repo.resolve()
    rows = csv_read(repo/MASTER)
    leaders = {r["date_us"]: r["leader_etf"] for r in csv_read(repo/LEADERS)}
    groups = {}
    for r in rows:
        groups.setdefault(r["date_us"], []).append(r)

    trades = []
    for date, candidates in sorted(groups.items()):
        if len(candidates) != 10 or any(not r["ibkr_stock_5min_csv"]
                                          or not r["ibkr_first_15min_gain_pct"]
                                          or not r["ibkr_first_15min_shares"]
                                          for r in candidates):
            raise ValueError(f"Day missing complete 10-stock research: {date}")
        ranked = sorted(candidates, key=lambda x: (-float(x["ibkr_first_15min_gain_pct"]), x["ticker"]))
        top3 = ranked[:3]
        selected = sorted(top3, key=lambda x: (-float(x["ibkr_first_15min_shares"]), x["ticker"]))[0]
        if selected["sector_etf"] != leaders.get(date):
            raise ValueError(f"Sector ranking mismatch for {date}")
        bars = price_bars(repo/selected["ibkr_stock_5min_csv"], date)
        real_opening_gain = 100*(bars[2]["c"]/bars[0]["o"] - 1)
        real_vol = sum(b["v"] for b in bars[:3])
        if abs(real_opening_gain-float(selected["ibkr_first_15min_gain_pct"])) > .02:
            raise ValueError(f"Opening 15m price mismatch: {date} {selected['ticker']}")
        if abs(real_vol-float(selected["ibkr_first_15min_shares"])) > 2:
            raise ValueError(f"Opening 15m volume mismatch: {date} {selected['ticker']}")
        trade_bars = bars[3:]
        trades.append({
            "date": date, "sector": selected["sector_etf"], "ticker": selected["ticker"],
            "top3": ",".join(x["ticker"] for x in top3),
            "entry": trade_bars[0]["o"], "opening_gain_pct": real_opening_gain,
            "opening_volume": real_vol,
            "low_first": replay(trade_bars, "LOW_FIRST"),
            "high_first": replay(trade_bars, "HIGH_FIRST"),
        })

    print("LOOK-AHEAD WARNING: full-day web gainer candidates; not an unbiased backtest")
    print("Entry 14:45 UK 5m open; 1% SL, stepped trailing, EOD 20:55 close")
    print("Date       Sector Ticker   Entry   Low-first% High-first%  ExitL  ExitH")
    for r in trades:
        print(f"{r['date']} {r['sector']:6s} {r['ticker']:6s} "
              f"{r['entry']:8.2f} {r['low_first']['pct']:+10.3f} "
              f"{r['high_first']['pct']:+11.3f}  "
              f"{r['low_first']['exit_time']:5s}  {r['high_first']['exit_time']:5s}")
    for key in ("low_first", "high_first"):
        print(key, aggregate(trades, key))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=[
                "date", "sector", "ticker", "top3", "entry", "opening_gain_pct",
                "opening_volume", "low_first_pct", "low_first_exit",
                "low_first_time", "high_first_pct", "high_first_exit",
                "high_first_time", "path_sensitive"])
            writer.writeheader()
            for r in trades:
                lo, hi = r["low_first"], r["high_first"]
                writer.writerow({
                    "date": r["date"], "sector": r["sector"], "ticker": r["ticker"],
                    "top3": r["top3"], "entry": r["entry"],
                    "opening_gain_pct": round(r["opening_gain_pct"], 6),
                    "opening_volume": int(r["opening_volume"]),
                    "low_first_pct": round(lo["pct"], 6),
                    "low_first_exit": lo["reason"], "low_first_time": lo["exit_time"],
                    "high_first_pct": round(hi["pct"], 6),
                    "high_first_exit": hi["reason"], "high_first_time": hi["exit_time"],
                    "path_sensitive": int(abs(lo["pct"]-hi["pct"]) > 1e-6),
                })
        print("CSV:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
