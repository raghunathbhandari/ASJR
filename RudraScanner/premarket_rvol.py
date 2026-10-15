"""Strict, no-lookahead 5-day cumulative Relative Volume at Time.

Independent of RudraScanner's original RTH RVOL20. Uses only completed,
continuous 5-minute session buckets; missing history never becomes RVOL zero.
Persist compact completed-session cumulative profiles inside the shared DataLake.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo
import os

import pandas as pd

ET = ZoneInfo("America/New_York")
FIELDS = ["ticker", "session_date_et", "session", "minute", "cum_volume"]
SEGMENTS = {"PRE": (240, 570), "RTH": (570, 960), "POST": (960, 1200)}
MAX_SESSIONS = 5
LOW_RVOL5_MAX = 0.58
HIGH_RVOL5_MIN = 2.00


def durable_reference_path(root):
    """Outside dated DataLake; survives day-folder retention cleanup."""
    return Path(root) / "ASJR_Analyst" / "state" / "rudra_premarket_rvol5.csv"


def reference_path(root, trading_day):
    return (Path(root) / "ASJR_Analyst" / "DataLake" / str(trading_day)
            / "processed" / "rudra_premarket_rvol_history.csv")


def _previous_reference(root, trading_day):
    lake = Path(root) / "ASJR_Analyst" / "DataLake"
    if not lake.is_dir():
        return None
    options = []
    for folder in lake.iterdir():
        if not folder.is_dir() or folder.name > str(trading_day):
            continue
        try:
            date.fromisoformat(folder.name)
        except ValueError:
            continue
        path = folder / "processed" / "rudra_premarket_rvol_history.csv"
        if path.is_file():
            options.append((folder.name, path))
    return max(options)[1] if options else None


def normalize_bars(bars):
    """Use ET timestamps and start-of-bar time; never infer missing bars."""
    required = {"ticker", "datetime", "volume"}
    if bars is None or bars.empty or not required.issubset(bars.columns):
        return pd.DataFrame(columns=FIELDS + ["timestamp_et", "complete"])
    b = bars[["ticker", "datetime", "volume"]].copy()
    utc = pd.to_datetime(b["datetime"], errors="coerce", utc=True)
    b["timestamp_et"] = utc.dt.tz_convert(ET)
    b["volume"] = pd.to_numeric(b["volume"], errors="coerce")
    b = b[b["timestamp_et"].notna() & b["volume"].ge(0)].copy()
    b["ticker"] = b["ticker"].astype(str).str.strip().str.upper()
    b["session_date_et"] = b["timestamp_et"].dt.strftime("%Y-%m-%d")
    b["minute"] = b["timestamp_et"].dt.hour * 60 + b["timestamp_et"].dt.minute
    b = b[b["minute"].mod(5).eq(0)].copy()
    b["session"] = ""
    for session, (start, end) in SEGMENTS.items():
        b.loc[b["minute"].ge(start) & b["minute"].lt(end), "session"] = session
    b = b[b["session"].ne("")].copy()
    b = b.sort_values("timestamp_et").drop_duplicates(
        ["ticker", "session_date_et", "session", "minute"], keep="last")
    b["cum_volume"] = b.groupby(
        ["ticker", "session_date_et", "session"])["volume"].cumsum()
    return b


def _complete_profiles(bars, *, before_day):
    """Archive ONLY whole, consecutive 5m session segments from prior days."""
    items = []
    if bars.empty:
        return pd.DataFrame(columns=FIELDS)
    for (ticker, day, session), part in bars.groupby(
            ["ticker", "session_date_et", "session"], sort=False):
        if day >= str(before_day):
            continue
        first, last = SEGMENTS[session]
        minutes = part.sort_values("minute")["minute"].tolist()
        if minutes != list(range(first, last, 5)):
            continue
        items.append(part[FIELDS])
    return pd.concat(items, ignore_index=True) if items else pd.DataFrame(columns=FIELDS)


def _clean_reference(frame, day):
    if frame is None or frame.empty or not set(FIELDS).issubset(frame.columns):
        return pd.DataFrame(columns=FIELDS)
    p = frame[FIELDS].copy()
    p["ticker"] = p["ticker"].astype(str).str.upper().str.strip()
    p["session_date_et"] = p["session_date_et"].astype(str)
    p["minute"] = pd.to_numeric(p["minute"], errors="coerce")
    p["cum_volume"] = pd.to_numeric(p["cum_volume"], errors="coerce")
    p = p.dropna()
    p = p[p["session_date_et"] < str(day)].copy()
    p = p[p["session"].isin(SEGMENTS)].sort_values(
        ["ticker", "session", "session_date_et", "minute"])
    p = p.drop_duplicates(FIELDS[:4], keep="last")
    good = []
    for (ticker, session, date_key), x in p.groupby(
            ["ticker", "session", "session_date_et"], sort=False):
        start, end = SEGMENTS[session]
        if (x["minute"].astype(int).tolist() == list(range(start, end, 5))
                and x["cum_volume"].ge(0).all()
                and x["cum_volume"].diff().fillna(x["cum_volume"]).ge(0).all()):
            good.append(x)
    p = pd.concat(good, ignore_index=True) if good else pd.DataFrame(columns=FIELDS)
    keep = []
    for _, group in p.groupby(["ticker", "session"], sort=False):
        days = sorted(group["session_date_et"].unique())[-MAX_SESSIONS:]
        keep.append(group[group["session_date_et"].isin(days)])
    return pd.concat(keep, ignore_index=True) if keep else pd.DataFrame(columns=FIELDS)


def calculate(bars, reference, *, trading_day):
    """Return 5-day current-bar RVOL; unavailable means NaN and ready=False.

    Comparisons use the 5 *previous full sessions of the same segment*
    and identical minute-of-day; per-current-session cumulative history must
    be contiguous from session open to that bar.
    """
    normalized = normalize_bars(bars)
    reference = _clean_reference(reference, trading_day)
    current = normalized[normalized["session_date_et"].eq(str(trading_day))].copy()
    current["rvol5"] = float("nan")
    current["rvol5_ready"] = False
    for (ticker, session), group in current.groupby(["ticker", "session"], sort=False):
        history = reference[(reference["ticker"] == ticker)
                            & (reference["session"] == session)]
        available = sorted(history["session_date_et"].unique())
        group = group.sort_values("minute")
        start, _ = SEGMENTS[session]
        for period in (5,):
            days = available[-period:]
            if len(days) < period:
                continue
            baseline = history[history["session_date_et"].isin(days)].groupby(
                "minute")["cum_volume"].mean()
            previous = None
            for idx, row in group.iterrows():
                minute = int(row["minute"])
                if previous is None:
                    contiguous = minute == start
                else:
                    contiguous = minute == previous + 5
                if not contiguous:
                    break
                previous = minute
                denom = baseline.get(minute, float("nan"))
                if pd.notna(denom) and denom > 0:
                    current.loc[idx, "rvol%d" % period] = float(row["cum_volume"]) / denom
                    current.loc[idx, "rvol%d_ready" % period] = True
    return current


def update_history(bars, root, trading_day, *, save=False):
    """Roll forward verified old complete sessions; no external requests."""
    source = durable_reference_path(root)
    if not source.is_file():
        source = _previous_reference(root, trading_day)
    if source is None:
        stored = pd.DataFrame(columns=FIELDS)
    else:
        try:
            stored = pd.read_csv(source)
        except (OSError, ValueError, pd.errors.EmptyDataError):
            stored = pd.DataFrame(columns=FIELDS)
    incoming = _complete_profiles(normalize_bars(bars), before_day=trading_day)
    parts = [p for p in (stored, incoming) if not p.empty]
    reference = _clean_reference(
        pd.concat(parts, ignore_index=True) if parts else None, trading_day)
    if save and not reference.empty:
        target = reference_path(root, trading_day)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Each concurrent pipeline invocation must own a distinct staging file.
        # Reusing <target>.tmp lets another process rename it first and causes
        # FileNotFoundError; os.replace remains atomic per completed file.
        import tempfile
        csv_data = reference.to_csv(index=False)
        for destination in (target, durable_reference_path(root)):
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=destination.name + ".", suffix=".tmp",
                dir=str(destination.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(csv_data)
                os.replace(temp_name, destination)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
    current = calculate(bars, reference, trading_day=trading_day)
    return current, {
        "reference_file": str(source) if source else None,
        "ready5": int(current["rvol5_ready"].sum()) if len(current) else 0,
        "stored_rows": len(reference),
        "saved": bool(save and not reference.empty),
    }


def candidates(features):
    """Pure premarket watch candidates; not a Discord sender."""
    if features is None or features.empty:
        return features.iloc[0:0] if features is not None else pd.DataFrame()
    needed = {"close", "ema9", "vwap", "rvol5",
              "rvol5_ready", "minute", "session"}
    if not needed.issubset(features.columns):
        return features.iloc[0:0]
    minute = pd.to_numeric(features["minute"], errors="coerce")
    rv = pd.to_numeric(features["rvol5"], errors="coerce")
    ok = (features["rvol5_ready"].eq(True)
          & pd.to_numeric(features["close"], errors="coerce").gt(
                pd.to_numeric(features["ema9"], errors="coerce"))
          & pd.to_numeric(features["ema9"], errors="coerce").gt(
                pd.to_numeric(features["vwap"], errors="coerce"))
          & (rv.le(LOW_RVOL5_MAX) | rv.ge(HIGH_RVOL5_MIN))
          & ~(minute.ge(570) & minute.lt(600)))
    result = features[ok].copy()
    result["rvol5_signal"] = result["rvol5"].apply(
        lambda value: "LOW_RVOL" if value <= LOW_RVOL5_MAX else "HIGH_RVOL")
    return result
