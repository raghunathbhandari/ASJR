#!/usr/bin/env python3
"""Short SMB-style research shortlist from the LAST SAVED Chakra category board.

No broker connection, scans, orders, or alert sends. Freshness is explicit.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")


def choose(board, limit=5):
    rows = board.get("rows", [])
    picked = []
    for row in rows:
        cats = set(row.get("categories") or ())
        if row.get("data_state") != "FRESH_5M" or not cats.intersection(
                {"STRONG_MOMENTUM", "WEAK_SELLING", "TOP_IN_PLAY", "REVERSAL_WATCH"}):
            continue
        change = row.get("change_5m_pct")
        volume = row.get("vol_12bar")
        if "STRONG_MOMENTUM" in cats:
            direction = "WATCH LONG"
            reason = "Rising 5m price + EMA9"
            directional = 3
        elif "WEAK_SELLING" in cats:
            direction = "WATCH SHORT"
            reason = "Weak 5m price + EMA9"
            directional = 3
        elif "REVERSAL_WATCH" in cats:
            direction = "WATCH REVERSAL"
            reason = "Early 5m recovery"
            directional = 2
        else:
            direction = "WATCH"
            reason = "Multiple scanner sources"
            directional = 0
        if volume is not None and volume >= 1.5:
            reason += " + active volume"
        elif row.get("scanner_codes"):
            reason += " + scanner interest"
        score = (directional, int(volume is not None and volume >= 1.0),
                 int(row.get("discovery_priority") or 0),
                 abs(float(change)) if change is not None else 0.0)
        picked.append((score, row["ticker"], direction, reason))
    picked.sort(key=lambda x: (tuple(-v for v in x[0]), x[1]))
    return picked[:limit]


def render(board, *, now=None, limit=5):
    now = now or datetime.now(timezone.utc)
    generated = datetime.fromisoformat(board["generated_at_uk"])
    age = (now - generated.astimezone(timezone.utc)).total_seconds()
    day = now.astimezone(ET).date().isoformat()
    if board.get("day") != day or age < -60 or age > 1200:
        return ("RUDRA SCANNER | TOP IN PLAY | DATA STALE\n"
                "No current shortlist. Wait for the next Chakra cycle.\n")
    stamp = generated.astimezone(UK).strftime("%H:%M")
    lines = [f"RUDRA SCANNER | TOP IN PLAY | {stamp} UK"]
    picks = choose(board,limit)
    for i, (_, ticker, direction, reason) in enumerate(picks, 1):
        lines.append(f"{i}. {ticker} | {direction} | {reason}")
    if not picks:
        lines.append("NO VERIFIED CURRENT 5M CANDIDATES")
    lines.append(f"REMAINING WATCHLIST | {max(0,len(board.get('rows',[]))-len(picks))} tickers")
    lines.append("RESEARCH WATCH ONLY | Not confirmed entries")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Short Top In Play from saved scanner board")
    parser.add_argument("--date", help="ET trading date; default current ET date")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--top", type=int, default=5, choices=range(1,6), metavar="1-5")
    args = parser.parse_args(argv)
    day = args.date or datetime.now(ET).date().isoformat()
    path = (Path(args.repo)/"ASJR_Analyst"/"DataLake"/day/"processed"/"rudra_scanner_categories.json")
    if not path.is_file():
        print("RUDRA SCANNER | TOP IN PLAY | NO SAVED DATA")
        return 2
    print(render(json.loads(path.read_text(encoding="utf-8")), limit=args.top),end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
