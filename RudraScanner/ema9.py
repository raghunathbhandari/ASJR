"""Continuous EMA9 on IBKR's actual completed 5-minute bars.

Regular-session and extended-hours bars share one EMA series per ticker.
There is intentionally NO daily/session reset and NO synthetic gap-filling.
Use the existing DataLake's raw/intraday_5m.csv or normalized intraday frame.
This module is NOT connected to live Chakra/Discord.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd


PERIOD = 9
BAR_MINUTES = 5
FIELD_ALIASES = {
    "ticker": "ticker",
    "date": "datetime",
    "datetime": "datetime",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
}
OUTPUT_COLUMNS = (
    "ticker", "datetime", "bar_close_utc", "bar_time_uk",
    "session", "open", "high", "low", "close", "volume",
    "ema9", "ema9_ready", "prior_gap_minutes"
)


def _now_utc(now):
    stamp = pd.Timestamp(now if now is not None else datetime.now(timezone.utc))
    if stamp.tzinfo is None:
        raise ValueError("now must be timezone-aware (UTC recommended)")
    return stamp.tz_convert("UTC")


def _session_label(utc_times):
    """Labels are informational, not a substitute for an exchange calendar."""
    et = utc_times.dt.tz_convert("America/New_York")
    minute = et.dt.hour * 60 + et.dt.minute
    labels = pd.Series("OVERNIGHT", index=utc_times.index, dtype="object")
    labels.loc[(minute >= 4 * 60) & (minute < 9 * 60 + 30)] = "PREMARKET"
    labels.loc[(minute >= 9 * 60 + 30) & (minute < 16 * 60)] = "RTH"
    labels.loc[(minute >= 16 * 60) & (minute < 20 * 60)] = "POSTMARKET"
    return labels


def build_continuous_ema9(raw, *, now=None):
    """Return (feature DataFrame, validation summary).

    Timestamp is a 5-minute bar's START. A bar is included only if its
    end <= now. The incoming timestamps MUST include timezone information.
    The existing IBKR parser emits timezone-aware America/New_York dates.
    No rows are invented when bars are missing overnight or intraday.
    """
    status = {
        "state": "OK", "input_rows": 0, "completed_rows": 0,
        "invalid_rows": 0, "duplicate_rows": 0, "unfinished_rows": 0,
        "tickers": 0, "min_periods": PERIOD, "session_reset": False,
        "extended_hours_included": True, "timezone": "UTC",
    }
    if raw is None or raw.empty:
        status["state"] = "MISSING"
        return pd.DataFrame(columns=OUTPUT_COLUMNS), status

    out = raw.copy()
    status["input_rows"] = len(out)
    # Both legacy IBKR and normalized intraday schemas are supported.
    renamed = {col: FIELD_ALIASES.get(str(col).strip().lower(), str(col))
               for col in out.columns}
    out = out.rename(columns=renamed)
    if out.columns.duplicated().any():
        raise ValueError("Ambiguous/duplicated OHLCV column aliases")
    expected = {"ticker", "datetime", "open", "high", "low", "close", "volume"}
    missing = expected.difference(out.columns)
    if missing:
        raise ValueError("Missing 5-minute OHLCV columns: " + ", ".join(sorted(missing)))

    out = out[list(expected)].copy()
    out["ticker"] = out["ticker"].astype("string").str.strip().str.upper()
    # Do not silently interpret timezone-naive ET inputs as UTC.
    for item in out["datetime"].dropna():
        stamp = pd.Timestamp(item)
        if stamp.tzinfo is None:
            raise ValueError("Incoming bar timestamps must include a timezone")
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce", utc=True)
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    valid = (
        out["ticker"].notna()
        & out["ticker"].str.len().gt(0).fillna(False)
        & out["datetime"].notna()
        & out[["open", "high", "low", "close", "volume"]].notna().all(axis=1)
        & (out["low"] > 0)
        & (out["high"] >= out[["open", "close", "low"]].max(axis=1))
        & (out["low"] <= out[["open", "close"]].min(axis=1))
        & (out["volume"] >= 0)
    )
    status["invalid_rows"] = int((~valid).sum())
    out = out.loc[valid].sort_values(["ticker", "datetime"]).copy()
    dup = out.duplicated(["ticker", "datetime"], keep="last")
    status["duplicate_rows"] = int(dup.sum())
    out = out.loc[~dup].copy()

    clock = _now_utc(now)
    complete = out["datetime"] + pd.Timedelta(minutes=BAR_MINUTES) <= clock
    status["unfinished_rows"] = int((~complete).sum())
    out = out.loc[complete].sort_values(["ticker", "datetime"]).reset_index(drop=True)

    if out.empty:
        status["state"] = "INCOMPLETE" if status["unfinished_rows"] else "MISSING"
        return pd.DataFrame(columns=OUTPUT_COLUMNS), status

    grouped = out.groupby("ticker", sort=False)
    out["ema9"] = grouped["close"].transform(
        lambda close: close.ewm(span=PERIOD, adjust=False).mean()
    )
    # Warm-up crosses days, just like the underlying EMA.
    out["ema9_ready"] = grouped.cumcount() >= PERIOD - 1
    out["prior_gap_minutes"] = (
        grouped["datetime"].diff().dt.total_seconds() / 60.0
    )
    out["bar_close_utc"] = out["datetime"] + pd.Timedelta(minutes=BAR_MINUTES)
    out["bar_time_uk"] = out["datetime"].dt.tz_convert("Europe/London")
    out["session"] = _session_label(out["datetime"])
    status["completed_rows"] = len(out)
    status["tickers"] = int(out["ticker"].nunique())
    if status["invalid_rows"] or status["duplicate_rows"] or status["unfinished_rows"]:
        status["state"] = "PARTIAL"
    return out[list(OUTPUT_COLUMNS)], status
