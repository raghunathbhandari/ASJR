"""Carry the last 21 full US RTH sessions through ONE common ASJR DataLake.

Saved reference: DataLake/YYYY-MM-DD/processed/rudra_scanner_rvol20_baseline.csv
The latest previous day's reference is copied forward by calculation,
not by creating another DataLake or retaining 20 whole raw 5M files.

Only 78 complete, strictly consecutive 5-minute regular-session bars
count as a full reference day. Unknown/partial days are NOT backfilled.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from .storage import _atomic

FIELDS = ["ticker", "session_date_et", "minutes_into_rth", "cum_volume"]
MAX_DAYS = 21
MIN_PRIOR = 20


def _source_path(root, day):
    return (Path(root) / "ASJR_Analyst" / "DataLake" / str(day) /
            "processed" / "rudra_scanner_rvol20_baseline.csv")


def _load_source(root, day):
    current = _source_path(root, day)
    if current.is_file():
        return current
    lake = Path(root) / "ASJR_Analyst" / "DataLake"
    if not lake.is_dir():
        return None
    earlier = []
    for folder in lake.iterdir():
        if not folder.is_dir() or folder.name >= str(day):
            continue
        try:
            date.fromisoformat(folder.name)
        except ValueError:
            continue
        candidate = folder / "processed" / "rudra_scanner_rvol20_baseline.csv"
        if candidate.is_file():
            earlier.append((folder.name, candidate))
    return max(earlier)[1] if earlier else None


def _verified_history(features):
    rows = []
    if features is None or features.empty:
        return pd.DataFrame(columns=FIELDS)
    rth = features[features["session"].eq("RTH")]
    for (ticker, day), sub in rth.groupby(
            ["ticker", "session_date_et"], sort=False):
        ordered = sub.sort_values("minutes_into_rth")
        mins = ordered["minutes_into_rth"].astype(int).tolist()
        volume = pd.to_numeric(ordered["volume"], errors="coerce")
        if (mins != list(range(0, 390, 5)) or
                volume.isna().any() or (volume < 0).any()):
            continue
        cumulative = volume.cumsum()
        for minute, amount in zip(mins, cumulative):
            rows.append({"ticker": str(ticker), "session_date_et": str(day),
                         "minutes_into_rth": int(minute),
                         "cum_volume": float(amount)})
    return pd.DataFrame(rows, columns=FIELDS)


def apply_rolling_rvol20(features, repo_root, trade_date, *, save=False):
    """Return features, status, with true 20-prior-session relative volume.

    Reads only already stored common DataLake daily reference material.
    Never creates new reference rows for a partial RTH session. No
    in-memory loss after the normal five-day raw-folder cleanup.
    """
    source = _load_source(repo_root, trade_date)
    if source is not None:
        try:
            older = pd.read_csv(source)
            if not set(FIELDS).issubset(older.columns):
                older = pd.DataFrame(columns=FIELDS)
        except (ValueError, OSError, pd.errors.EmptyDataError):
            older = pd.DataFrame(columns=FIELDS)
    else:
        older = pd.DataFrame(columns=FIELDS)
    incoming = _verified_history(features)
    combined = pd.concat([older[FIELDS], incoming], ignore_index=True)
    combined["ticker"] = combined["ticker"].astype(str).str.strip().str.upper()
    combined["session_date_et"] = combined["session_date_et"].astype(str)
    combined["minutes_into_rth"] = pd.to_numeric(
        combined["minutes_into_rth"], errors="coerce")
    combined["cum_volume"] = pd.to_numeric(combined["cum_volume"], errors="coerce")
    combined = combined.dropna().sort_values(
        ["ticker", "session_date_et", "minutes_into_rth"])
    combined = combined.drop_duplicates(
        ["ticker", "session_date_et", "minutes_into_rth"], keep="last")
    # Never retain future reference data for a historical replay.
    combined = combined[combined["session_date_et"] <= str(trade_date)[:10]].copy()
    survivors = []
    for ticker, sub in combined.groupby("ticker", sort=False):
        full_days = []
        for day, x in sub.groupby("session_date_et", sort=True):
            minutes = x["minutes_into_rth"].astype(int).tolist()
            if (minutes == list(range(0, 390, 5))
                    and (x["cum_volume"].diff().fillna(x["cum_volume"]) >= 0).all()):
                full_days.append(day)
        full_days = full_days[-MAX_DAYS:]
        survivors.append(sub[sub["session_date_et"].isin(full_days)])
    reference = pd.concat(survivors, ignore_index=True) if survivors else (
        pd.DataFrame(columns=FIELDS))

    updated = features.copy()
    if not updated.empty:
        updated["rvol20"] = float("nan")
        updated["rvol20_ready"] = False
        updated["prior_complete_sessions"] = 0
        for (ticker, day), current in updated[
            updated["session"].eq("RTH")
        ].groupby(["ticker", "session_date_et"], sort=False):
            pool = reference[(reference["ticker"] == str(ticker))
                             & (reference["session_date_et"] < str(day))]
            sessions = sorted(pool["session_date_et"].unique())[-MIN_PRIOR:]
            updated.loc[current.index, "prior_complete_sessions"] = len(sessions)
            if len(sessions) < MIN_PRIOR:
                continue
            baseline = pool[pool["session_date_et"].isin(sessions)]
            average = baseline.groupby("minutes_into_rth")["cum_volume"].mean()
            current = current.sort_values("minutes_into_rth")
            target_cum = current["volume"].cumsum()
            matching = current["minutes_into_rth"].map(average)
            ratio = target_cum / matching.where(matching > 0)
            updated.loc[current.index, "rvol20"] = ratio.to_numpy()
            updated.loc[current.index, "rvol20_ready"] = ratio.notna().to_numpy()
    ready_count = int(updated["rvol20_ready"].sum()) if not updated.empty else 0
    status = {"state": "AVAILABLE" if ready_count else "INSUFFICIENT_20_FULL_RTH_SESSIONS",
              "ready_rows": ready_count,
              "stored_rows": len(reference),
              "reference_file": str(source) if source else None,
              "saved": False,
              "preserved_within_common_datalake": True}
    if save and len(reference):
        output = _source_path(repo_root, trade_date)
        _atomic(output, reference.to_csv(index=False))
        status["saved"] = True
        status["output"] = str(output)
    return updated, status
