#!/usr/bin/env python3
"""Bounded, parameterized Yahoo Finance historical OHLCV importer.

Called only by the Admin Bridge after strict JSON request validation.
Writes research CSVs under a fixed local directory. Never touches Git main,
Chakra, IBKR, trading orders, or arbitrary user paths.
"""
from __future__ import annotations

import re
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

ROOT = Path("/root/trading/ASJR")
OUTPUT_ROOT = ROOT / "Rudra-DDB/ResearchData/Yahoo"
INTERVAL_MAX_DAYS = {
    "1m": 7, "2m": 60, "5m": 60, "15m": 60, "30m": 60,
    "60m": 730, "90m": 60, "1h": 730,
    "1d": 3650, "5d": 3650, "1wk": 3650, "1mo": 3650, "3mo": 3650,
}
SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9.^=_-]{0,19}\Z")
MAX_SYMBOLS = 5
MAX_ROWS_PER_SYMBOL = 25000


def validate(job):
    """Returns normalized (symbols, interval, start, end), or raises ValueError."""
    if type(job) is not dict or set(job) != {"schema_version", "id", "operation", "symbols", "interval", "start", "end"}:
        raise ValueError("invalid request keys")
    symbols = job["symbols"]
    interval = job["interval"]
    if type(symbols) is not list or not (1 <= len(symbols) <= MAX_SYMBOLS):
        raise ValueError("symbols must contain 1 to 5 tickers")
    if any(type(v) is not str or not SYMBOL.fullmatch(v) for v in symbols):
        raise ValueError("unsupported symbol syntax")
    if len(set(symbols)) != len(symbols):
        raise ValueError("duplicate symbols")
    if type(interval) is not str or interval not in INTERVAL_MAX_DAYS:
        raise ValueError("unsupported interval")
    if type(job["start"]) is not str or type(job["end"]) is not str:
        raise ValueError("dates must be strings")
    start, end = date.fromisoformat(job["start"]), date.fromisoformat(job["end"])
    if not (date(2000,1,1) <= start < end <= datetime.now(timezone.utc).date()+timedelta(days=1)):
        raise ValueError("invalid or future date range")
    span=(end-start).days
    if span > INTERVAL_MAX_DAYS[interval]:
        raise ValueError("date range exceeds configured Yahoo interval limit")
    # Yahoo may apply stricter limits in practice; empty returns are reported.
    return symbols, interval, start, end


def import_history(job):
    try:
        symbols, interval, start, end = validate(job)
    except (ValueError, TypeError) as exc:
        return {"status":"REFUSED", "reason":str(exc)[:160]}
    import pandas as pd
    import yfinance as yf

    label = f"{start}_{end}_{interval}"
    target_dir = OUTPUT_ROOT / label
    if target_dir.is_symlink() or OUTPUT_ROOT.is_symlink():
        return {"status":"REFUSED","reason":"unsafe output directory"}
    target_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    for symbol in symbols:
        try:
            bars = yf.download(
                symbol, start=start.isoformat(), end=end.isoformat(),
                interval=interval, prepost=True, auto_adjust=False,
                progress=False, threads=False, multi_level_index=False
            )
            if bars is None or bars.empty:
                result[symbol] = {"status":"NO_DATA"}
                continue
            if isinstance(bars.columns,pd.MultiIndex):
                bars.columns=bars.columns.get_level_values(0)
            needed=["Open","High","Low","Close","Volume"]
            if any(c not in bars.columns for c in needed):
                result[symbol]={"status":"BAD_COLUMNS"}
                continue
            bars=bars[needed].dropna(subset=needed[:4]).sort_index()
            bars=bars[~bars.index.duplicated(keep="first")]
            if bars.empty or len(bars)>MAX_ROWS_PER_SYMBOL:
                result[symbol]={"status":"INVALID_ROW_COUNT"}
                continue
            safe_name = symbol.replace("^","IDX_").replace("=","_EQ_").replace(".","_").replace("-","_")
            target=target_dir / f"{safe_name}.csv"
            if target.exists() and target.is_symlink():
                result[symbol]={"status":"UNSAFE_TARGET"}
                continue
            bars.index.name="datetime_source"
            bars.to_csv(target)
            result[symbol]={"status":"SUCCESS","rows":len(bars),
                            "first":str(bars.index[0]),"last":str(bars.index[-1]),
                            "bytes":target.stat().st_size,
                            "path":str(target.relative_to(ROOT))}
        except Exception as exc:
            result[symbol]={"status":"FAILED","reason":type(exc).__name__}
    return {"status":"SUCCESS" if all(v["status"]=="SUCCESS" for v in result.values()) else "PARTIAL_OR_FAILED",
            "source":"Yahoo Finance", "interval":interval,
            "start_inclusive":start.isoformat(),"end_exclusive":end.isoformat(),
            "symbols":result}
