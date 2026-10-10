"""Live 5-minute scanner sidecar — same Chakra IBKR app and common DataLake.

Never replaces Wicks' universe. Always reuses already imported actual
IBKR OHLCV/WAP before asking for extra selected stocks/benchmark ETFs.
Runs only after selected candidates have been validated in SHADOW/ACTIVE.
Live directional context uses completed, timestamp-matched SPY/QQQ/sector
5M bars against the last available PRIOR completed 15:55 ET RTH close.
No Yahoo daily future-close leak. No trades or Discord in this module.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .engine import evaluate_scanner, persist_features, format_report
from .features import build_scanner_features
from .patterns import PatternSettings, detect_five_patterns
from .topdown import ticker_etf_from_sources
from .volume_history import apply_rolling_rvol20
from .storage import _atomic
from .discovery import read_ai_csv

ET = "America/New_York"


def _last_rth_close(frame, day):
    previous = frame[
        (frame["session"] == "RTH") &
        (frame["session_date_et"] < day) &
        (frame["minutes_into_rth"] == 385)
    ].sort_values("datetime")
    if previous.empty:
        return None
    # Don't assume Friday exists in the shorter duration: be explicit.
    prior = previous.iloc[-1]
    return float(prior["close"]) if float(prior["close"]) > 0 else None


def intraday_direction(features, day, *, ticker_etfs):
    """Return (index, ticker sector biases, audit) at latest common 5M bar.

    Fail CLOSED when ETF candles are absent/stale/unfinished or previous
    full RTH close is unknown. This is as-of candle, not daily yfinance.
    """
    status = {"state": "WAIT", "reason": "", "timestamp": None,
              "index_pct": {}, "sector_etf": ticker_etfs,
              "sector_pct": {}, "source": "IBKR_COMPLETED_5M"}
    biases = {s: "WAIT" for s in ticker_etfs}
    if features is None or features.empty:
        status["reason"] = "NO_COMPLETED_BARS"
        return "WAIT", biases, status
    ref = {}
    for sym in {"SPY", "QQQ", *ticker_etfs.values()}:
        history = features[
            (features["ticker"] == sym) &
            (features["session_date_et"] == day) &
            (features["session"] == "RTH")
        ].sort_values("datetime")
        full = features[features["ticker"] == sym]
        prev = _last_rth_close(full, day)
        if history.empty or prev is None:
            continue
        ref[sym] = (history.iloc[-1]["datetime"], 100 *
                    (float(history.iloc[-1]["close"]) / prev - 1))
    if not {"SPY", "QQQ"}.issubset(ref):
        status["reason"] = "MISSING_BENCHMARK_OR_PREV_RTH_CLOSE"
        return "WAIT", biases, status
    if ref["SPY"][0] != ref["QQQ"][0]:
        status["reason"] = "UNALIGNED_SPY_QQQ_5M_TIMESTAMP"
        return "WAIT", biases, status
    now = ref["SPY"][0]
    status["timestamp"] = str(now)
    spy = ref["SPY"][1]
    qqq = ref["QQQ"][1]
    status["index_pct"] = {"SPY": round(spy, 4), "QQQ": round(qqq, 4)}
    if spy > 0.20 and qqq > 0.20:
        direction = "LONG"
    elif spy < -0.20 and qqq < -0.20:
        direction = "SHORT"
    else:
        status["reason"] = "MIXED_OR_NEUTRAL_BENCHMARKS"
        return "WAIT", biases, status
    for ticker, etf in ticker_etfs.items():
        lookup = ref.get(etf)
        if not lookup or lookup[0] != now:
            continue
        value = lookup[1]
        if direction == "LONG" and value > .20 and value > spy:
            biases[ticker] = "LONG"
        elif direction == "SHORT" and value < -.20 and value < spy:
            biases[ticker] = "SHORT"
        status["sector_pct"][ticker] = {
            "etf": etf, "pct": round(value, 4),
            "vs_spy": round(value - spy, 4),
            "bias": biases[ticker],
        }
    status.update(state=direction, reason="AS_OF_5M_INDEX_CONFIRMED")
    return direction, biases, status


def _raw_symbols(raw):
    if raw is None or raw.empty or "Ticker" not in raw.columns:
        return set()
    return set(raw["Ticker"].astype(str).str.upper())


def collect_live_bars(app, candidates, legacy_5m, *, fetch, ai_rows=(),
                      duration="3 D"):
    """Bound selected stock+ETF requests and retain actual WAP on joined rows.

    Keep legacy data untouched; a symbol already in legacy 5M feed does
    not trigger a duplicate broker historicalData request.
    """
    symbols = [str(c["ticker"]).upper() for c in candidates]
    if len(symbols) > 30 or len(set(symbols)) != len(symbols):
        raise ValueError("Scanner selected universe must be <=30 unique stocks")
    mapped = ticker_etf_from_sources(candidates, ai_rows=ai_rows)
    context = ["SPY", "QQQ", *sorted(set(mapped.values()))]
    needed = list(dict.fromkeys(symbols + context))
    available = _raw_symbols(legacy_5m)
    missing = [name for name in needed if name not in available]
    extra = pd.DataFrame()
    if missing:
        data = fetch(app, missing, duration=duration, batch_size=5, wait_time=20)
        from ASJR_Analyst.Utils.asjr_ibkr import combine_5m
        extra = combine_5m(data)
    portions = []
    if legacy_5m is not None and not legacy_5m.empty:
        portions.append(legacy_5m[
            legacy_5m["Ticker"].astype(str).str.upper().isin(needed)].copy())
    if not extra.empty:
        portions.append(extra)
    if not portions:
        return pd.DataFrame(columns=[
            "Ticker", "Date", "Open", "High", "Low", "Close", "Volume"
        ]), {"requested": missing, "symbols": needed, "etfs": mapped,
             "state": "DATA_NOT_READY"}
    joined = pd.concat(portions, ignore_index=True, sort=False)
    joined["Date"] = pd.to_datetime(joined["Date"], utc=True)
    joined = joined.sort_values(["Ticker", "Date"]).drop_duplicates(
        ["Ticker", "Date"], keep="last").reset_index(drop=True)
    return joined, {"requested": missing, "symbols": needed,
                    "etfs": mapped, "state": "COLLECTED",
                    "count": len(joined), "source": "SAME_IBKR_APP"}


def run_live_scanner_round(app, repo_root, trade_date, candidates, legacy_5m,
                           *, fetch, research=True, now=None):
    """Collect, compute and save scanner-only features and reports.

    Does not send alerts or import separate 1H data. Return events for
    the verified external Discord sender / ACK bridge.
    """
    root = Path(repo_root)
    day = str(trade_date)[:10]
    ai, ai_state = read_ai_csv(
        root / "ASJR_Analyst" / "config" / "ai_scanner_list.csv")
    raw, collection = collect_live_bars(
        app, candidates, legacy_5m, fetch=fetch, ai_rows=ai)
    features, report = evaluate_scanner(raw, now=now)
    features, rvol = apply_rolling_rvol20(features, root, day, save=True)
    report["feature_status"]["rvol_state"] = rvol["state"]
    report["feature_status"]["rvol20_ready_rows"] = rvol["ready_rows"]
    report["volume_history"] = rvol
    index, sector_biased, context = intraday_direction(
        features, day, ticker_etfs=collection["etfs"])
    report["context"] = context
    report["collection"] = collection
    if research and not features.empty:
        stock_bars = features[features["ticker"].isin(
            {c["ticker"] for c in candidates}
        )].copy()
        # All selected equities require current completed 5M bar matching
        # SPY/QQQ. Never alert a stale stock after its ETF has moved on.
        if context["timestamp"]:
            stock_bars = stock_bars.groupby("ticker", sort=False).filter(
                lambda g: (str(g["datetime"].max()) ==
                           str(pd.Timestamp(context["timestamp"])))
            )
        events, detector = detect_five_patterns(
            stock_bars, index_bias=index,
            sector_bias_by_ticker=sector_biased,
            settings=PatternSettings(enabled_for_research=True))
        report.update(state="EXPERIMENTAL_RESEARCH",
                      detector_status=detector, events=events)
    files = persist_features(root, day, features, report)
    target = root / "ASJR_Analyst" / "DataLake" / day / "reports"
    text_report = (
        f"RUDRA SCANNER LIVE DATA | {day} | 5M | UK TIME\n"
        f"MODE | RESEARCH_ONLY | NO TRADE ORDERS\n"
        f"SELECTED | {len(candidates)} tickers\n"
        f"TOP DOWN | {context['state']} | {context['reason']}\n"
        f"INDEX | {context['index_pct']}\n"
        f"WAP | {report['feature_status']['wap_state']}\n"
        f"RVOL20 | {rvol['state']}\n"
        f"DISCOVERY | {collection['state']} | "
        f"extra historical requests: {len(collection['requested'])}\n"
        + format_report(day, report)
        + "TICKERS | " + ", ".join(c["ticker"] for c in candidates) + "\n"
    )
    _atomic(target / "scalp_radar.txt", text_report)
    _atomic(target / "rudra_scanner_live_status.json",
            json.dumps(report, indent=2, default=str)+"\n")
    return {"state": report["state"], "events": report["events"],
            "collection": collection, "context": context,
            "files": files, "report": str(target / "scalp_radar.txt"),
            "quality": report["feature_status"],
            "alert_delivery": "DISABLED"}
