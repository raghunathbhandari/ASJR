#!/usr/bin/env python3
"""Short SMB-style research shortlist from the LAST SAVED Chakra category board.

No broker connection, scans, orders, or alert sends. Freshness is explicit.
"""
from __future__ import annotations
import argparse
import csv
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
        if not cats.intersection(
                {"STRONG_MOMENTUM", "WEAK_SELLING", "TOP_IN_PLAY", "REVERSAL_WATCH"}):
            continue
        change = row.get("change_5m_pct")
        volume = row.get("vol_12bar")
        fresh = row.get("data_state") == "FRESH_5M"
        if fresh and "STRONG_MOMENTUM" in cats:
            direction = "WATCH LONG"
            reason = "Rising 5m price + EMA9"
            directional = 3
        elif fresh and "WEAK_SELLING" in cats:
            direction = "WATCH SHORT"
            reason = "Weak 5m price + EMA9"
            directional = 3
        elif fresh and "REVERSAL_WATCH" in cats:
            direction = "WATCH REVERSAL"
            reason = "Early 5m recovery"
            directional = 2
        else:
            direction = "WATCH"
            codes = row.get("scanner_codes") or ""
            reason = "IBKR scanner: " + codes.replace(",", "/") if codes else "AI research watch"
            directional = 0
        if fresh and volume is not None and volume >= 1.5:
            reason += " + active volume"
        elif fresh and row.get("scanner_codes") and directional:
            reason += " + scanner interest"
        score = (directional, int(volume is not None and volume >= 1.0),
                 int(row.get("discovery_priority") or 0),
                 abs(float(change)) if change is not None else 0.0)
        picked.append((score, row["ticker"], direction, reason))
    picked.sort(key=lambda x: (tuple(-v for v in x[0]), x[1]))
    return picked[:limit]


def scan_rankings(repo_root, day, board, *, now=None, limit=5):
    """Rank ALL IBKR four-code discoveries, not only the selected 30.

    No fallback to AI-only/FIXED. Scanner membership and rank describe
    attention rather than trade probability; direction is scan-list bias.
    """
    now = now or datetime.now(timezone.utc)
    root = Path(repo_root)
    path = root/"ASJR_Analyst"/"DataLake"/str(day)/"raw"/"ibkr_scanner_list.csv"
    if not path.is_file():
        return "RUDRA SCANNER | SMB WATCH | NO SCANNER CSV\n"
    entries = {}
    with path.open(newline="",encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            sym = str(row.get("ticker") or "").strip().upper()
            code = str(row.get("scan_code") or "").strip()
            if not sym or sym in {"BEAT","ONDS"} or code not in {
                "TOP_PERC_GAIN","TOP_PERC_LOSE","HOT_BY_VOLUME","MOST_ACTIVE"}:
                continue
            try:
                ts=datetime.fromisoformat(str(row.get("scanned_at_utc","")).replace("Z","+00:00"))
                rank=int(row.get("rank") or 999)
            except (ValueError,TypeError):
                continue
            if ts.tzinfo is None or (now-ts).total_seconds()>1200 or (now-ts).total_seconds() < -60:
                continue
            e=entries.setdefault(sym,{"codes":set(),"ranks":{},"ts":ts})
            e["codes"].add(code)
            e["ranks"][code]=min(e["ranks"].get(code,999),rank)
            e["ts"]=max(e["ts"],ts)
    if not entries:
        return "RUDRA SCANNER | SMB WATCH | NO RECENT IBKR SCAN\n"
    stock_info={r["ticker"]:r for r in board.get("rows",[])}
    ranked=[]
    for sym,e in entries.items():
        codes=e["codes"]
        gain="TOP_PERC_GAIN" in codes
        lose="TOP_PERC_LOSE" in codes
        bias=("GAINER" if gain and not lose else "LOSER" if lose and not gain else "ACTIVE")
        hot="HOT_BY_VOLUME" in codes
        active="MOST_ACTIVE" in codes
        f=stock_info.get(sym,{})
        fresh=f.get("data_state")=="FRESH_5M"
        pct=f.get("change_5m_pct") if fresh else None
        vol=f.get("vol_12bar") if fresh else None
        # Volume and 5m movement are supplemental; not a verified session gap/RVOL.
        evidence=len(codes)*100 + (45 if hot else 0) + (20 if active else 0)
        evidence += sum(max(0,51-min(int(v),51)) for v in e["ranks"].values())
        if vol is not None:
            evidence += min(40,max(0,float(vol)*10))
        if pct is not None:
            evidence += min(25,abs(float(pct))*20)
        reasons=[]
        if gain and not lose:
            reasons.append("GAINER")
        elif lose and not gain:
            reasons.append("LOSER")
        if hot: reasons.append("HOT VOL")
        if active: reasons.append("ACTIVE")
        ranked.append((evidence,sym,bias,"+".join(reasons) or "SCANNER",f,e["ts"]))
    ranked.sort(key=lambda x:(-x[0],x[1]))
    stamp=max(e["ts"] for e in entries.values()).astimezone(UK).strftime("%H:%M")
    lines=[f"RUDRA SCANNER | SMB TOP IN PLAY | {stamp} UK"]
    for i,(_,sym,bias,reason,f,_) in enumerate(ranked[:limit],1):
        price=f.get("price") if f.get("data_state")=="FRESH_5M" else None
        price_text=f" | ${price:.2f}" if price is not None else ""
        lines.append(f"{i}. {sym} | {bias} | {reason}{price_text}")
    lines.append(f"REMAINING SCANNER | {len(ranked)-min(limit,len(ranked))} tickers")
    lines.append("SCANNER DISCOVERY | NOT TRADE SIGNALS")
    return "\n".join(lines)+"\n"


def raw_ibkr_by_code(repo_root, day, *, code="ALL", limit=10):
    """Print unmodified saved IBKR scan memberships and source ranks.

    No scoring, no direction inference, no price inference, no API request.
    """
    scan_codes=("TOP_PERC_GAIN","TOP_PERC_LOSE","HOT_BY_VOLUME","MOST_ACTIVE")
    path=(Path(repo_root)/"ASJR_Analyst"/"DataLake"/str(day)/
          "raw"/"ibkr_scanner_list.csv")
    if not path.is_file():
        return "IBKR SCANNER | NO SAVED RAW CSV\n"
    groups={key:[] for key in scan_codes}
    with path.open(newline="",encoding="utf-8-sig") as handle:
        for item in csv.DictReader(handle):
            key=item.get("scan_code","")
            if key in groups:
                groups[key].append(item)
    out=["IBKR SCANNER | RAW SAVED RESULTS | "+str(day)]
    for key in scan_codes:
        if code!="ALL" and code!=key:
            continue
        rows=groups[key]
        try:
            rows=sorted(rows,key=lambda x:int(x.get("rank") or 999999))
        except ValueError:
            pass
        stamp=rows[0].get("scanned_at_utc","N/A") if rows else "N/A"
        tickers=",".join(str(item.get("ticker","")).strip() for item in rows[:limit]
                         if str(item.get("ticker","")).strip())
        out.append(f"{key} | {len(rows)} | {tickers or 'NONE'} | UTC {stamp}")
    out.append("RAW IBKR SCAN CSV | no ranking calculation or trading signals")
    return "\n".join(out)+"\n"

def render(board, *, now=None, limit=5):
    now = now or datetime.now(timezone.utc)
    generated = datetime.fromisoformat(board["generated_at_uk"])
    age = (now - generated.astimezone(timezone.utc)).total_seconds()
    day = now.astimezone(ET).date().isoformat()
    if board.get("day") != day or age < -60 or age > 86400:
        return ("RUDRA SCANNER | TOP IN PLAY | DATA STALE\n"
                "No current shortlist. Wait for the next Chakra cycle.\n")
    stamp = generated.astimezone(UK).strftime("%H:%M")
    lines = [f"RUDRA SCANNER | TOP IN PLAY | {stamp} UK"]
    if age > 1200:
        lines.append("SAVED WATCHLIST | data older than 20 min")
    picks = choose(board,limit)
    for i, (_, ticker, direction, reason) in enumerate(picks, 1):
        lines.append(f"{i}. {ticker} | {direction} | {reason}")
    if not picks:
        lines.append("NO RANKED DISCOVERY CANDIDATES")
    lines.append(f"REMAINING WATCHLIST | {max(0,len(board.get('rows',[]))-len(picks))} tickers")
    lines.append("RESEARCH WATCH ONLY | Not confirmed entries")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Short Top In Play from saved scanner board")
    parser.add_argument("--ibkr-raw", action="store_true", help="Raw IBKR output grouped by scanner code")
    parser.add_argument("--code", choices=("ALL","TOP_PERC_GAIN","TOP_PERC_LOSE","HOT_BY_VOLUME","MOST_ACTIVE"), default="ALL")
    parser.add_argument("--limit", type=int, default=10, help="Maximum per scanner code")
    parser.add_argument("--date", help="ET trading date; default current ET date")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--top", type=int, default=5, choices=range(1,6), metavar="1-5")
    args = parser.parse_args(argv)
    day = args.date or datetime.now(ET).date().isoformat()
    if args.ibkr_raw:
        if args.limit < 1 or args.limit > 50:
            parser.error("--limit must be between 1 and 50")
        print(raw_ibkr_by_code(args.repo,day,code=args.code,limit=args.limit),end="")
        return 0
    path = (Path(args.repo)/"ASJR_Analyst"/"DataLake"/day/"processed"/"rudra_scanner_categories.json")
    if not path.is_file():
        print("RUDRA SCANNER | TOP IN PLAY | NO SAVED DATA")
        return 2
    print(scan_rankings(args.repo, day, json.loads(path.read_text(encoding="utf-8")), limit=args.top),end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
