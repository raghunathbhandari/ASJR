"""V1 transparent five-category discovery board, independent of trading-signal gates.

Shows provenance even when WAP, benchmark or 20-day RVOL is missing.
Never describes an old 5m candle as today's live price. No order/Discord.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import pandas as pd
from .storage import _atomic

CATEGORIES = ("TOP_IN_PLAY", "STRONG_MOMENTUM", "WEAK_SELLING",
              "REVERSAL_WATCH", "LOW_RVOL_WATCH")


def _num(value):
    try:
        val = float(value)
        return val if math.isfinite(val) else None
    except (ValueError, TypeError):
        return None


def build_board(candidates, features, *, day, now=None):
    """Return category rows and coverage; unverified categories stay empty."""
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        raise ValueError("now must be timezone aware")
    now = now.tz_convert("UTC")
    current = {}
    if features is not None and not features.empty:
        for ticker, group in features.groupby("ticker"):
            group = group.sort_values("datetime")
            latest = group.iloc[-1]
            stamp = pd.Timestamp(latest["datetime"]).tz_convert("UTC")
            # Today's eligible data, closed candle, sufficiently recent.
            fresh = (str(stamp.tz_convert("America/New_York").date()) == str(day)
                     and pd.Timedelta(0) <= now - stamp <= pd.Timedelta(minutes=20))
            if not fresh:
                continue
            past = group[group["datetime"] < stamp]
            old = past.iloc[-1] if not past.empty else None
            price = _num(latest.get("close"))
            prior_price = _num(old.get("close")) if old is not None else None
            ema = _num(latest.get("ema9"))
            slope = _num(latest.get("ema9_slope5_pct"))
            rel_vol = _num(latest.get("relative_volume_12bar"))
            change = ((price / prior_price - 1) * 100 if price is not None
                      and prior_price and prior_price > 0 else None)
            current[str(ticker).upper()] = {
                "price": price, "bar_time_uk": stamp.tz_convert("Europe/London").strftime("%H:%M"),
                "change_5m_pct": change, "ema9": ema, "slope5_pct": slope,
                "vol_12bar": rel_vol, "volume": _num(latest.get("volume")),
                "rvol20": _num(latest.get("rvol20")) if bool(latest.get("rvol20_ready", False)) else None,
                "vwap": _num(latest.get("vwap")) if bool(latest.get("vwap_ready", False)) else None,
            }
    rows = []
    for entry in candidates:
        sym = str(entry.get("ticker", "")).upper()
        f = current.get(sym)
        codes = list(entry.get("scan_codes") or [])
        sources = list(entry.get("sources") or [entry.get("selection_source", "UNKNOWN")])
        categories = []
        if codes or entry.get("ai_freshness") == "FRESH":
            categories.append("TOP_IN_PLAY")
        # Observed technical classifications require same-day fresh completed bars.
        if f and f["ema9"] is not None and f["price"] is not None:
            change, slope = f["change_5m_pct"], f["slope5_pct"]
            if (change is not None and change > 0 and f["price"] > f["ema9"]
                    and slope is not None and slope > 0):
                categories.append("STRONG_MOMENTUM")
            elif (change is not None and change < 0 and f["price"] < f["ema9"]
                  and slope is not None and slope < 0):
                categories.append("WEAK_SELLING")
            elif (change is not None and change > 0 and slope is not None
                  and slope >= 0 and f["price"] <= f["ema9"]):
                categories.append("REVERSAL_WATCH")
            if (f["vol_12bar"] is not None and f["vol_12bar"] <= .5
                    and slope is not None and slope > 0 and f["price"] > f["ema9"]):
                categories.append("LOW_RVOL_WATCH")
        if not categories:
            categories = ["UNCLASSIFIED"]
        priority = (len(codes) * 2 + int(entry.get("ai_freshness") == "FRESH")
                    + int("IBKR" in sources))
        rows.append({
            "ticker": sym, "categories": categories,
            "discovery_priority": priority, "source": "+".join(sources),
            "scanner_codes": "+".join(codes), "ai_bias": entry.get("ai_bias") or "N/A",
            "price": f["price"] if f else None,
            "bar_time_uk": f["bar_time_uk"] if f else None,
            "change_5m_pct": f["change_5m_pct"] if f else None,
            "volume": f["volume"] if f else None,
            "vol_12bar": f["vol_12bar"] if f else None,
            "rvol20": f["rvol20"] if f else None,
            "data_state": "FRESH_5M" if f else "NO_FRESH_5M",
            "selection_reason": ("scanner="+",".join(codes) if codes else
                                "AI research" if "AI" in sources else
                                "fixed watchlist")
        })
    rows.sort(key=lambda x: (-x["discovery_priority"], x["ticker"]))
    return {"day": str(day), "generated_at_uk": now.tz_convert("Europe/London").isoformat(),
            "counts": {key: sum(key in r["categories"] for r in rows)
                       for key in (*CATEGORIES, "UNCLASSIFIED")},
            "rows": rows, "status": "RESEARCH_ONLY_NO_TRADE_ORDERS"}


def format_board(board):
    lines = [f"RUDRA SCANNER | CATEGORIZED V1 | {board['day']} | UK",
             "RESEARCH ONLY | NO BUY/SELL ALERT | missing = N/A"]
    names = {"TOP_IN_PLAY":"TOP IN PLAY", "STRONG_MOMENTUM":"STRONG / MOMENTUM",
             "WEAK_SELLING":"WEAK / SELLING", "REVERSAL_WATCH":"REVERSAL WATCH",
             "LOW_RVOL_WATCH":"LOW RVOL WATCH"}
    for key in CATEGORIES:
        group = [r for r in board["rows"] if key in r["categories"]]
        lines.append(f"{names[key]} | {len(group)}")
        for idx, r in enumerate(group[:10], 1):
            pct = f"{r['change_5m_pct']:+.2f}%" if r["change_5m_pct"] is not None else "N/A"
            price = f"${r['price']:.2f}" if r["price"] is not None else "N/A"
            rv = f"{r['vol_12bar']:.2f}x" if r["vol_12bar"] is not None else "N/A"
            lines.append(f"{idx}. {r['ticker']} | {r['source']} | {r['bar_time_uk'] or 'N/A'} UK | price {price} | 5m {pct} | vol12 {rv} | {r['selection_reason']} | {r['data_state']}")
        if not group:
            lines.append("NO VERIFIED TICKERS (data or classification unavailable)")
    rest = [r["ticker"] for r in board["rows"] if r["categories"] == ["UNCLASSIFIED"]]
    lines.append(f"UNCLASSIFIED / NO VERIFIED CURRENT CATEGORY | {len(rest)} | {', '.join(rest)}")
    lines.append("LOW RVOL WATCH uses 12-prior-bar volume proxy, NOT Rudra-Premarket RVOL5.")
    lines.append("BUY WATCH gate remains separate and disabled until independently verified.")
    return "\n".join(lines)+"\n"


def save_board(root, day, board):
    folder = Path(root) / "ASJR_Analyst" / "DataLake" / str(day)
    report = folder / "reports" / "rudra_scanner_categories.txt"
    structured = folder / "processed" / "rudra_scanner_categories.json"
    _atomic(report, format_board(board))
    _atomic(structured, json.dumps(board, indent=2, default=str)+"\n")
    return str(report)
