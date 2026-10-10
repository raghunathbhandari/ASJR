"""Index -> Sector -> ticker context; ambiguous or missing = WAIT.

Use dated, actually observed sector ETF changes. News bias is context
only and never substitutes for market or sector confirmation.
"""
from __future__ import annotations

import math
import pandas as pd


def _pct(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def classify_topdown(sector_daily, *, trade_date, ticker_etfs):
    """Return (market direction, per-ticker sector direction, diagnostics).

    Require SPY and QQQ both directional and dated as-of trade_date.
    Confirm sector aligned and stronger/weaker vs SPY. No sector match,
    unknown source or missing daily ETF data => WAIT, never invention.
    """
    state = {"state": "WAIT", "reason": "", "spy_pct": None,
             "qqq_pct": None, "sector_context": {}}
    biases = {t: "WAIT" for t in ticker_etfs}
    if sector_daily is None or sector_daily.empty:
        state["reason"] = "MISSING_MARKET_SECTOR_DATA"
        return "WAIT", biases, state
    required = {"ticker", "date", "today_pct"}
    if not required.issubset(sector_daily.columns):
        state["reason"] = "MISSING_SECTOR_COLUMNS"
        return "WAIT", biases, state
    source = sector_daily.copy()
    source["ticker"] = source["ticker"].astype(str).str.upper()
    source = source[source["date"].astype(str).str[:10] == str(trade_date)[:10]]
    source = source.drop_duplicates("ticker", keep="last").set_index("ticker")
    spy = _pct(source.at["SPY", "today_pct"]) if "SPY" in source.index else None
    qqq = _pct(source.at["QQQ", "today_pct"]) if "QQQ" in source.index else None
    state.update(spy_pct=spy, qqq_pct=qqq)
    if spy is None or qqq is None:
        state["reason"] = "MISSING_FRESH_SPY_QQQ_PCT"
        return "WAIT", biases, state
    if spy > 0.20 and qqq > 0.20:
        index = "LONG"
    elif spy < -0.20 and qqq < -0.20:
        index = "SHORT"
    else:
        state["reason"] = "MIXED_OR_NEUTRAL_INDEX"
        return "WAIT", biases, state
    for ticker, etf in ticker_etfs.items():
        name = str(etf or "").strip().upper()
        sector_move = (_pct(source.at[name, "today_pct"])
                       if name in source.index else None)
        if sector_move is None:
            continue
        sector_strong = sector_move - spy
        if index == "LONG" and sector_move > 0.20 and sector_strong > 0:
            biases[ticker] = "LONG"
        elif index == "SHORT" and sector_move < -0.20 and sector_strong < 0:
            biases[ticker] = "SHORT"
        state["sector_context"][ticker] = {
            "etf": name, "daily_pct": sector_move,
            "relative_vs_spy_pct": sector_strong,
            "bias": biases[ticker],
        }
    state.update(state=index, reason="CONFIRMED_INDEX;_SECTOR_REQUIRED")
    return index, biases, state


def ticker_etf_from_sources(selected, ai_rows=(), fixed_rows=()):
    """Use only explicitly sourced ETFs or clear sector strings."""
    mapping = {}
    explicit = {str(r.get("ticker", "")).upper(): r.get("sector_etf", "")
                for r in ai_rows}
    for item in selected:
        symbol = str(item.get("ticker", "")).upper()
        etf = str(explicit.get(symbol, "") or "").upper().strip()
        if etf:
            mapping[symbol] = etf
    sector_map = {
        "SEMICONDUCTOR": "SMH",
        "SOFTWARE": "XLK",
        "CLOUD": "XLK",
        "CYBERSECURITY": "XLK",
        "ENERGY": "XLE",
        "HEALTHCARE": "XLV",
        "FINANCIAL": "XLF",
        "INDUSTRIAL": "XLI",
        "CONSUMER": "XLY",
        "TELECOMMUNICATION": "XLC",
        "TELECOM": "XLC",
    }
    for item in selected:
        ticker = str(item.get("ticker", "")).upper()
        if ticker in mapping:
            continue
        sector = str(item.get("fixed_sector", "")).upper()
        hits = {etf for term, etf in sector_map.items() if term in sector}
        if len(hits) == 1:
            mapping[ticker] = next(iter(hits))
    return mapping
