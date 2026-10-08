"""Rudra-Reversal 1H live alert scanner.

Production/live rules mirror the tested Rudra-Reversal research:
- LONG only
- 1H candles
- BB(20, 2.0), population std ddof=0
- Current candle touches/near-touches Lower BB
- At least 2 of last 3 candles touch/near-touch Lower BB
- Near tolerance = 0.15%
- 150-bar range including signal candle
- Depth = (high150 - signal close) / (high150 - low150) >= 20%
- Entry = signal candle close
- Up to 2 simultaneous entries per ticker
- Exit = first later candle touching Upper BB or within 0.15% below it
- No new entry on an exit candle

The detector reconstructs accepted positions from historical 1H candles each run,
then queues only newly completed accepted entry candles. First deployment seeds
latest bars and does not replay historical entries.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

UK = ZoneInfo("Europe/London")

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent
STATE_FILE = ROOT / "rudra_reversal_1h_alert_state.json"
BATCH_FILE = ROOT / "rudra_reversal_1h_alert_batch.json"
CACHE_ROOT = (
    REPO_ROOT / "Backtesting" / "BacktestData" / "IBKR" / "MarketData" / "1h"
)

STATE_SCHEMA_VERSION = 1
NEAR_TOL = 0.0015
MIN_DEPTH = 0.20
MAX_POSITIONS = 2

STRATEGY_TICKERS = (
    "NQ",
    "INTC", "MU", "AMAT", "LRCX", "PLTR",
    "XOM", "GOOG", "SPY", "META", "NVDA",
)


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write_json_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temp, path)


def _new_state():
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "last_seen_bar": {},
        "pending": [],
        "seed_latest": True,
    }


def _load_state(path=STATE_FILE):
    state = _read_json(path, None)
    if not isinstance(state, dict) or state.get("schema_version") != STATE_SCHEMA_VERSION:
        return _new_state()
    state.setdefault("last_seen_bar", {})
    state.setdefault("pending", [])
    state.setdefault("seed_latest", False)
    return state


def _event_key(event):
    return f'{event["ticker"]}|{event["bar_time_uk"]}|RUDRA_REVERSAL_1H_ENTRY'


def _find_source(ticker, trade_date=None):
    ticker = str(ticker).upper()
    candidates = []

    if ticker == "NQ":
        # NQ is Yahoo Finance ONLY. Never fall through to the IBKR stock cache.
        nq_path = (
            REPO_ROOT
            / "Backtesting"
            / "BacktestData"
            / "OpenSource"
            / "NQ"
            / "NQ_1h_1y.csv"
        )
        return nq_path if nq_path.exists() else None

    if trade_date is not None:
        day = str(trade_date)[:10]
        raw = ROOT / "DataLake" / day / "raw"
        candidates.extend([
            raw / f"{ticker}_1h.csv",
            raw / "intraday_1h.csv",
            raw / "hourly_1h.csv",
        ])
        if raw.exists():
            candidates.extend(sorted(raw.glob("*1h*.csv")))
            candidates.extend(sorted(raw.glob("*hour*.csv")))

    candidates.append(CACHE_ROOT / f"{ticker}_1h.csv")

    for path in candidates:
        if path.exists():
            return path
    return None


def _load_ticker_1h(ticker, trade_date=None):
    path = _find_source(ticker, trade_date)
    if path is None:
        return pd.DataFrame()

    df = pd.read_csv(path)
    if df.empty:
        return df

    if "ticker" in df.columns:
        df = df[df["ticker"].astype(str).str.upper() == str(ticker).upper()].copy()
        if df.empty:
            return df

    rename = {}
    for col in df.columns:
        lc = str(col).lower()
        if lc in {"datetime", "date", "timestamp", "time"}:
            rename[col] = "datetime"
        elif lc == "open":
            rename[col] = "open"
        elif lc == "high":
            rename[col] = "high"
        elif lc == "low":
            rename[col] = "low"
        elif lc == "close":
            rename[col] = "close"
    df = df.rename(columns=rename)

    required = {"datetime", "open", "high", "low", "close"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    df["datetime"] = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = (
        df.dropna(subset=["datetime", "open", "high", "low", "close"])
        .sort_values("datetime")
        .drop_duplicates("datetime", keep="last")
        .reset_index(drop=True)
    )

    # Never evaluate the still-forming latest 1H candle.
    now_utc = pd.Timestamp.now(tz="UTC")
    completed = df["datetime"] + pd.Timedelta(hours=1) <= now_utc
    return df[completed].reset_index(drop=True)


def _add_features(df):
    frame = df.copy()
    frame["bb_mid"] = frame["close"].rolling(20).mean()
    frame["bb_std"] = frame["close"].rolling(20).std(ddof=0)
    frame["bb_upper"] = frame["bb_mid"] + 2.0 * frame["bb_std"]
    frame["bb_lower"] = frame["bb_mid"] - 2.0 * frame["bb_std"]

    frame["high150"] = frame["high"].rolling(150).max()
    frame["low150"] = frame["low"].rolling(150).min()
    span = frame["high150"] - frame["low150"]
    frame["depth"] = (frame["high150"] - frame["close"]) / span

    frame["near_lower"] = (
        (frame["low"] <= frame["bb_lower"])
        | (((frame["low"] - frame["bb_lower"]) / frame["bb_lower"]) <= NEAR_TOL)
    )
    frame["near_upper"] = (
        (frame["high"] >= frame["bb_upper"])
        | (((frame["bb_upper"] - frame["high"]) / frame["bb_upper"]) <= NEAR_TOL)
    )
    frame["touch3"] = frame["near_lower"].astype(int).rolling(3).sum()
    frame["signal"] = (
        frame["near_lower"]
        & (frame["touch3"] >= 2)
        & (frame["depth"] >= MIN_DEPTH)
    )
    return frame


def _accepted_entries(frame):
    accepted = []
    active = []

    for i in range(149, len(frame)):
        row = frame.iloc[i]
        exited_this_bar = False
        remaining = []

        for position in active:
            if i > position["entry_i"] and bool(row["near_upper"]):
                exited_this_bar = True
            else:
                remaining.append(position)
        active = remaining

        if (
            not exited_this_bar
            and bool(row["signal"])
            and len(active) < MAX_POSITIONS
        ):
            event = {
                "entry_i": i,
                "entry_slot": len(active) + 1,
                "datetime": row["datetime"],
                "entry_price": float(row["close"]),
                "depth_pct": float(row["depth"] * 100.0),
                "touch_count": int(row["touch3"]),
                "bb_lower": float(row["bb_lower"]),
                "bb_mid": float(row["bb_mid"]),
                "bb_upper": float(row["bb_upper"]),
            }
            accepted.append(event)
            active.append(event)

    return accepted


def build_rudra_reversal_alerts(
    trade_date=None,
    state_file=STATE_FILE,
    tickers=STRATEGY_TICKERS,
):
    state = _load_state(state_file)
    pending = {
        _event_key(event): event
        for event in state.get("pending", [])
        if isinstance(event, dict)
    }

    for ticker in tickers:
        raw = _load_ticker_1h(ticker, trade_date)
        if len(raw) < 150:
            continue

        frame = _add_features(raw)
        accepted = _accepted_entries(frame)
        latest_bar = frame.iloc[-1]["datetime"]
        latest_uk = latest_bar.tz_convert(UK)
        latest_key = latest_uk.isoformat()

        if state.get("seed_latest"):
            state["last_seen_bar"][ticker] = latest_key
            continue

        marker_text = state["last_seen_bar"].get(ticker)
        marker = pd.Timestamp(marker_text) if marker_text else None
        if marker is not None:
            marker = (
                marker.tz_localize(UK)
                if marker.tzinfo is None
                else marker.tz_convert(UK)
            )

        for entry in accepted:
            bar_uk = entry["datetime"].tz_convert(UK)
            if marker is not None and bar_uk <= marker:
                continue

            event = {
                "type": "RUDRA_REVERSAL_1H_ENTRY",
                "ticker": str(ticker).upper(),
                "bar_time_uk": bar_uk.strftime("%Y-%m-%d %H:%M"),
                "entry_price": entry["entry_price"],
                "entry_slot": entry["entry_slot"],
                "depth_pct": entry["depth_pct"],
                "touch_count": entry["touch_count"],
                "bb_lower": entry["bb_lower"],
                "bb_mid": entry["bb_mid"],
                "bb_upper": entry["bb_upper"],
            }
            pending.setdefault(_event_key(event), event)

        state["last_seen_bar"][ticker] = latest_key

    state["seed_latest"] = False
    state["pending"] = sorted(
        pending.values(),
        key=lambda e: (e["bar_time_uk"], e["ticker"]),
    )
    _write_json_atomic(state_file, state)
    return list(state["pending"])


def prepare_alert(result, batch_file=BATCH_FILE):
    events = result.get("rudra_reversal_alerts", []) if result else []
    events = [e for e in events if e.get("type") == "RUDRA_REVERSAL_1H_ENTRY"]
    if not events:
        return ""

    lines = ["RUDRA REVERSAL | 1H"]
    keys = []
    tickers = []

    for event in events:
        line = (
            f'{event["ticker"]} | BUY #{event["entry_slot"]} | {event["bar_time_uk"][-5:]} | '
            f'{event["entry_price"]:.2f} | DEPTH {event["depth_pct"]:.1f}%'
        )
        candidate = "\n".join(
            lines + [line, "", ", ".join(tickers + [event["ticker"]])]
        )
        if len(candidate) > 1900:
            break
        lines.append(line)
        keys.append(_event_key(event))
        if event["ticker"] not in tickers:
            tickers.append(event["ticker"])

    if not keys:
        return ""

    lines.extend(["", ", ".join(tickers)])
    _write_json_atomic(batch_file, {"event_keys": keys})
    fence = chr(96) * 3
    return fence + "\n" + "\n".join(lines) + "\n" + fence


def has_prepared_batch(batch_file=BATCH_FILE):
    batch = _read_json(batch_file, {})
    return bool(isinstance(batch, dict) and batch.get("event_keys"))


def mark_alert_sent(state_file=STATE_FILE, batch_file=BATCH_FILE):
    batch = _read_json(batch_file, {})
    keys = set(batch.get("event_keys", [])) if isinstance(batch, dict) else set()
    if not keys:
        return 0

    state = _read_json(state_file, {})
    if not isinstance(state, dict):
        return 0

    before = list(state.get("pending", []))
    after = [event for event in before if _event_key(event) not in keys]
    state["pending"] = after
    _write_json_atomic(state_file, state)

    try:
        Path(batch_file).unlink()
    except OSError:
        pass

    return len(before) - len(after)
