"""Weekend/offline RudraScanner replay from an EXISTING dated ASJR DataLake.

Historic `raw/ibkr_gapup.csv` is a legacy mover list, NOT the new four
scanner-code IBKR discovery. Its membership may have required the old
4% mover condition. Replay alone must never be called a live scan.
Rows are screened with the saved 30-day close/volume observations.
Market cap and current tradability cannot be verified from these files.
No API calls, no Discord messages, no real-time trade signals.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from .discovery import EXCLUDED, read_ai_csv, ticker_valid
from .universe import load_shared_universe, selection_summary

REPLAY_CODE = "LEGACY_GAPUP_REPLAY"


def _source_folder(repo_root, source_date):
    date_text = date.fromisoformat(str(source_date)[:10]).isoformat()
    return Path(repo_root) / "ASJR_Analyst" / "DataLake" / date_text


def _csv_rows(path, required):
    if not path.is_file():
        raise FileNotFoundError(str(path))
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = set(required).difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def historical_ibkr_candidates(repo_root, source_date):
    """Return (ranked rows, metadata) from the historic legacy mover list.

    Require >=20 distinct known daily observations and a latest saved close
    >$5, plus trailing 20-day average volume >=1M. Sort by trailing
    average dollar turnover, then ticker; no missing data is invented.
    This is a deterministic REPLAY quality proxy, not a live ranking
    or current IBKR contract/market-cap check.
    """
    day = date.fromisoformat(str(source_date)[:10]).isoformat()
    folder = _source_folder(repo_root, day)
    raw = folder / "raw"
    old_rows = _csv_rows(raw / "ibkr_gapup.csv", ("ticker",))
    daily_rows = _csv_rows(raw / "daily_30d.csv", ("ticker", "date", "close", "volume"))
    daily_by_ticker = {}
    for record in daily_rows:
        ticker = (record.get("ticker") or "").strip().upper()
        candle_date = (record.get("date") or "")[:10]
        if not ticker_valid(ticker) or candle_date > day:
            continue
        try:
            close = float(record["close"])
            volume = float(record["volume"])
        except (TypeError, ValueError):
            continue
        if not (0 < close < float("inf") and 0 <= volume < float("inf")):
            continue
        daily_by_ticker.setdefault(ticker, {})[candle_date] = (close, volume)

    found = []
    seen = set()
    exclusions = {"invalid_or_excluded": [], "missing_history_or_liquidity": []}
    for entry in old_rows:
        ticker = (entry.get("ticker") or "").strip().upper()
        if not ticker_valid(ticker) or ticker in EXCLUDED or ticker in seen:
            exclusions["invalid_or_excluded"].append(ticker)
            continue
        seen.add(ticker)
        samples = daily_by_ticker.get(ticker, {})
        last20 = sorted(samples.items())[-20:]
        if len(last20) < 20 or last20[-1][0] != day:
            exclusions["missing_history_or_liquidity"].append(ticker)
            continue
        price = last20[-1][1][0]
        average_volume = sum(pair[1][1] for pair in last20) / 20.0
        average_dollar_volume = sum(
            pair[1][0] * pair[1][1] for pair in last20
        ) / 20.0
        if price <= 5 or average_volume <= 1_000_000:
            exclusions["missing_history_or_liquidity"].append(ticker)
            continue
        found.append((ticker, price, average_volume, average_dollar_volume))

    found.sort(key=lambda v: (-v[3], v[0]))
    rows = [
        {"ticker": ticker, "scan_code": REPLAY_CODE, "rank": ix,
         "scanned_at_utc": "", "source_date": day}
        for ix, (ticker, price, avg_volume, turnover)
        in enumerate(found, start=1)
    ]
    status = {
        "source": "LEGACY_GAPUP_REPLAY_NOT_LIVE",
        "trade_date": day,
        "source_csv": str(raw / "ibkr_gapup.csv"),
        "daily_csv": str(raw / "daily_30d.csv"),
        "original_mover_count": len(old_rows),
        "eligible_after_historical_data_checks": len(found),
        "excluded_counts": {key: len(value) for key, value in exclusions.items()},
        "ranking": "20d_average_dollar_volume_desc",
        "verified": ["last_close_gt_5", "20d_avg_shares_gt_1m", "20_completed_daily_rows"],
        "not_verified": ["current_ibkr_scanner", "company_market_cap", "fundamentals",
                         "current_quote", "RTH_signal", "actual_ibkr_wap"],
        "warning": "Legacy 4pct-era mover list only; NOT four-code live IBKR discovery",
    }
    return rows, status


def build_replay(repo_root, trade_date, source_date=None):
    """Use historical IBKR mover tickers + AI CSV + day's existing FIXED list."""
    root = Path(repo_root)
    day = date.fromisoformat(str(trade_date)[:10]).isoformat()
    source = date.fromisoformat(str(source_date or day)[:10]).isoformat()
    if source > day:
        raise ValueError("Replay may not use an IBKR source date after the target date")
    rows, evidence = historical_ibkr_candidates(root, source)
    ai, ai_status = read_ai_csv(
        root / "ASJR_Analyst" / "config" / "ai_scanner_list.csv")
    selected, fixed_status = load_shared_universe(root, day, ai, rows)
    counts = selection_summary(selected)
    return {
        "mode": "REPLAY_ONLY", "state": "HISTORICAL_NOT_LIVE",
        "trade_date": day, "ibkr_source_date": source,
        "candidates": selected, "selection": counts,
        "ai_status": ai_status, "fixed_status": fixed_status,
        "ibkr_status": evidence,
        "ibkr_candidates": rows,
        "signals": [], "alert_delivery": "DISABLED",
        "historical_only": True,
    }


def render_replay(result):
    counts = result["selection"]
    lines = [
        "RUDRA SCANNER | BOT HOOK REPLAY | HISTORICAL DATA - NOT LIVE",
        f'DataLake date: {result["trade_date"]} | IBKR legacy source: {result["ibkr_source_date"]}',
        f'AI: {result["ai_status"]["state"]} | FIXED: {result["fixed_status"]["state"]}',
        f'IBKR: {result["ibkr_status"]["source"]} | screened: {result["ibkr_status"]["eligible_after_historical_data_checks"]}',
        f'Candidates: {counts["selected_total"]} / {counts["max_total"]}',
        f'Sources: {counts["selected_by_source"]}',
        "",
    ]
    for source in ("FIXED", "AI", "IBKR"):
        tickers = [r["ticker"] for r in result["candidates"]
                   if r["selection_source"] == source]
        lines.append(f'{source} ({len(tickers)}/10): {", ".join(tickers) or "none"}')
    lines.extend(["", "Signals: NOT IMPLEMENTED; 0 live alerts sent.",
                  "Existing WICKS/Reversal jobs NOT RUN; no IBKR API requested.",
                  "Historical eligibility is approximate; market cap NOT verified."])
    return "\n".join(lines) + "\n"


def persist_replay(repo_root, result):
    """Opt-in save of clearly named replay artifacts in the COMMON DataLake.

    Do not overwrite true scanner files (ibkr_scanner_list.csv) or
    production reports. Do not automatically stage, commit or push.
    """
    import io
    import os

    from .storage import _atomic, _csv_text

    day = _source_folder(repo_root, result["trade_date"])
    raw = day / "raw"
    processed = day / "processed"
    reports = day / "reports"
    replay = result["ibkr_candidates"]
    _atomic(raw / "ibkr_scanner_replay_list.csv",
            _csv_text(("ticker", "scan_code", "rank", "scanned_at_utc", "source_date"),
                      replay))
    _atomic(processed / "rudra_scanner_replay_candidates.csv",
            _csv_text(("ticker", "selection_source", "sources", "scan_codes",
                       "ai_bias", "ai_freshness", "fixed_sector"),
                      [{**r, "sources": "+".join(r.get("sources", [])),
                        "scan_codes": "+".join(r.get("scan_codes", []))}
                       for r in result["candidates"]]))
    _atomic(reports / "rudra_scanner_replay_report.txt", render_replay(result))
    _atomic(reports / "rudra_scanner_replay_status.json",
            json.dumps({
                "mode": result["mode"], "state": result["state"],
                "trade_date": result["trade_date"],
                "ibkr_source_date": result["ibkr_source_date"],
                "selection": result["selection"],
                "ibkr_status": result["ibkr_status"],
                "ai_status": result["ai_status"],
                "fixed_status": result["fixed_status"],
                "warning": "Not a live market or trade signal result",
            }, indent=2) + "\n")
    return str(reports / "rudra_scanner_replay_report.txt")
