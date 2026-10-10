"""Throttled 1H stock bar ingestion for locked Rudra-Reversal strategy.

Uses the existing connected IBKR EWrapper app, not a new connection.
Only invoked when the experimental ACTIVE feature gate is enabled.
Results are published inside the SAME day DataLake raw/intraday_1h.csv
and may be used by the existing locked Rudra-Reversal code unchanged.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def get_hourly_history(app, tickers, *, duration="35 D",
                       batch_size=5, wait_time=20):
    """Bounded IBKR historical requests; no retries in a 5M live cycle."""
    from ASJR_Analyst.Utils.asjr_ibkr import stock_contract, parse_ibkr_bars, _next_req_id

    tickers = list(dict.fromkeys(
        t for t in (str(s).strip().upper() for s in tickers) if t
    ))[:30]
    all_rows, statuses = [], {}
    for offset in range(0, len(tickers), batch_size):
        active = {}
        for ticker in tickers[offset:offset + batch_size]:
            req = _next_req_id(app)
            app.data[req] = []
            app.hist_done[req] = False
            active[req] = ticker
            try:
                app.reqHistoricalData(
                    req, stock_contract(ticker), "", duration,
                    "1 hour", "TRADES", 0, 2, False, [],
                )
            except Exception as exc:
                statuses[ticker] = {"state": "ERROR", "error": str(exc)}
                active.pop(req, None)
                app.data.pop(req, None)
                app.hist_done.pop(req, None)
        start = time.monotonic()
        while active and time.monotonic() - start < wait_time:
            if all(app.hist_done.get(req, False) for req in active):
                break
            time.sleep(0.10)
        for req, ticker in active.items():
            complete = bool(app.hist_done.get(req, False))
            if not complete:
                try:
                    app.cancelHistoricalData(req)
                except Exception:
                    pass
            rows = list(app.data.pop(req, []))
            app.hist_done.pop(req, None)
            # Hourly callback WAP sidecar is not needed by Reversal.
            wap_tap = getattr(app, "_rudra_wap_sidecar", None)
            if isinstance(wap_tap, dict):
                wap_tap.pop(req, None)
            try:
                parsed = parse_ibkr_bars(rows)
                if not complete or parsed.empty:
                    statuses[ticker] = {
                        "state": "TIMEOUT" if not complete else "EMPTY",
                        "rows": len(parsed),
                    }
                    continue
                block = parsed.reset_index().copy()
                block.insert(0, "ticker", ticker)
                all_rows.append(block)
                statuses[ticker] = {"state": "OK", "rows": len(parsed)}
            except Exception as exc:
                statuses[ticker] = {"state": "ERROR", "error": str(exc)}
    if all_rows:
        frame = pd.concat(all_rows, ignore_index=True)
        frame = frame.rename(columns={"Date": "datetime"})
        frame = frame[["ticker", "datetime", "Open", "High", "Low", "Close", "Volume"]]
        frame["datetime"] = pd.to_datetime(frame["datetime"], utc=True)
        frame = frame.sort_values(["ticker", "datetime"]).drop_duplicates(
            ["ticker", "datetime"], keep="last").reset_index(drop=True)
    else:
        frame = pd.DataFrame(columns=[
            "ticker", "datetime", "Open", "High", "Low", "Close", "Volume",
        ])
    return frame, statuses


def refresh_hourly_cache(app, repo_root, trade_date, tickers,
                         *, now=None, refresh_minutes=60):
    """Skip repeats within one hour; never silently use missing ticker data."""
    from .storage import _atomic

    root = Path(repo_root) / "ASJR_Analyst" / "DataLake" / str(trade_date)
    csv_file = root / "raw" / "intraday_1h.csv"
    state_file = root / "raw" / "rudra_scanner_hourly_status.json"
    now_utc = pd.Timestamp(now if now is not None
                           else datetime.now(timezone.utc))
    if now_utc.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now_utc.tz_convert("UTC")
    selected = sorted(set(str(t).strip().upper() for t in tickers))[:30]
    if csv_file.is_file() and state_file.is_file():
        try:
            prior = json.loads(state_file.read_text(encoding="utf-8"))
            stamp = pd.Timestamp(prior["generated_at_utc"])
            if (stamp.tzinfo is not None and
                    pd.Timedelta(0) <= now_utc - stamp.tz_convert("UTC")
                    < pd.Timedelta(minutes=refresh_minutes) and
                    prior["selected_tickers"] == selected):
                return {"state": "CACHE_FRESH",
                        "file": str(csv_file), "source": "SAVED_IBKR_1H",
                        "tickers": len(selected)}
        except (ValueError, KeyError, OSError, TypeError):
            pass

    frame, statuses = get_hourly_history(app, selected)
    status = {
        "state": "COMPLETE" if len(frame) and all(
            x.get("state") == "OK" for x in statuses.values()) else "PARTIAL",
        "source": "IBKR_TRADES_1H",
        "generated_at_utc": now_utc.isoformat(),
        "selected_tickers": selected,
        "per_ticker": statuses,
        "rows": len(frame),
        "usable_150bars": sorted([
            ticker for ticker, data in frame.groupby("ticker")
            if len(data) >= 150
        ]) if not frame.empty else [],
    }
    # Do not overwrite good previous data with transient zero rows.
    if frame.empty:
        status["state"] = "DATA_NOT_READY"
        return status
    _atomic(csv_file, frame.to_csv(index=False))
    _atomic(state_file, json.dumps(status, indent=2, default=str) + "\n")
    status["file"] = str(csv_file)
    return status
