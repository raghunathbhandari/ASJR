"""RudraScanner 5M completed-bar EMA9, exact WAP-based RTH VWAP, RVOL20.

No synthetic bars. Do not fabricate WAP or claim 20-day RVOL
from a three-calendar-day historical request. The same shared OHLCV
DataLake is used by every strategy.
"""
from __future__ import annotations

import pandas as pd

from .ema9 import build_continuous_ema9

ET = "America/New_York"
MINUTE = pd.Timedelta(minutes=5)


def build_scanner_features(raw, *, now=None):
    """Return (completed feature frame, quality status).

    Exact VWAP uses the IBKR historical bar's actual 'WAP' multiplied
    by that bar's transaction volume. WAP is explicitly missing rather
    than synthesized from high/low/close.

    Volume history uses 20 distinct PRIOR COMPLETE US RTH sessions for
    time-matched cumulative RVOL; unavailable when history is too short.
    """
    base, status = build_continuous_ema9(raw, now=now)
    status = dict(status)
    status.update(wap_source="IBKR_HISTORICAL_BAR_WAP_REQUIRED",
                  vwap_ready_rows=0, rvol20_ready_rows=0,
                  exact_wap_rows=0, no_wap_rows=0)
    extra = ["wap", "vwap", "vwap_ready", "wap_present",
             "session_date_et", "minutes_into_rth", "rvol20",
             "rvol20_ready", "prior_complete_sessions",
             "relative_volume_12bar", "ema9_slope5_pct"]
    if base.empty:
        for col in extra:
            base[col] = pd.Series(dtype="object")
        return base, status

    frame = base.copy()
    frame["session_date_et"] = frame["datetime"].dt.tz_convert(ET).dt.date.astype(str)
    local = frame["datetime"].dt.tz_convert(ET)
    frame["minutes_into_rth"] = (local.dt.hour * 60 + local.dt.minute) - 570

    wap = pd.Series(float("nan"), index=frame.index)
    if raw is not None and not raw.empty:
        original = raw.copy()
        original.columns = [str(c).strip().lower() for c in original.columns]
        if "wap" in original.columns:
            dcol = "datetime" if "datetime" in original.columns else "date"
            if dcol not in original.columns or "ticker" not in original.columns:
                raise ValueError("WAP source must identify ticker and date/datetime")
            rawdate = original[dcol].dropna()
            if any(pd.Timestamp(v).tzinfo is None for v in rawdate):
                raise ValueError("WAP candle time must be timezone-aware")
            original["timestamp_utc"] = pd.to_datetime(
                original[dcol], errors="coerce", utc=True)
            original["ticker"] = original["ticker"].astype(str).str.upper().str.strip()
            original["wap"] = pd.to_numeric(original["wap"], errors="coerce")
            original = original.sort_values(["ticker", "timestamp_utc"]).drop_duplicates(
                ["ticker", "timestamp_utc"], keep="last")
            frame = frame.merge(
                original[["ticker", "timestamp_utc", "wap"]],
                how="left", left_on=["ticker", "datetime"],
                right_on=["ticker", "timestamp_utc"], sort=False,
                validate="one_to_one"
            ).drop(columns=["timestamp_utc"])
        else:
            frame["wap"] = wap
    else:
        frame["wap"] = wap

    frame["wap_present"] = (frame["wap"].notna()
                            & (frame["wap"] > 0)
                            & (frame["wap"] <= frame["high"] * 1.01)
                            & (frame["wap"] >= frame["low"] * 0.99))
    frame.loc[~frame["wap_present"], "wap"] = float("nan")
    status["exact_wap_rows"] = int(frame["wap_present"].sum())
    status["no_wap_rows"] = int((~frame["wap_present"]).sum())

    frame["vwap"] = float("nan")
    frame["vwap_ready"] = False
    frame["rvol20"] = float("nan")
    frame["rvol20_ready"] = False
    frame["prior_complete_sessions"] = 0

    # EMA premarket history never resets. RTH VWAP is independent and
    # never uses pre/postmarket volume.
    frame["ema9_slope5_pct"] = (
        frame.groupby("ticker")["ema9"].pct_change(5) * 100
    )
    frame["relative_volume_12bar"] = float("nan")
    for ticker, indices in frame.groupby("ticker", sort=False).groups.items():
        idx = list(indices)
        prior = frame.loc[idx, "volume"].shift(1).rolling(12, min_periods=12).median()
        denominator = prior.where(prior > 0)
        frame.loc[idx, "relative_volume_12bar"] = (
            frame.loc[idx, "volume"].to_numpy() / denominator.to_numpy()
        )

    rth = frame[frame["session"] == "RTH"]
    for ticker, group in rth.groupby("ticker", sort=False):
        complete_prior = []
        for day, current in group.groupby("session_date_et", sort=True):
            indexes = current.index
            minutes = current["minutes_into_rth"].astype(int).tolist()
            # RTH starts exactly at the regular open. If a bar is missing,
            # exact cumulative VWAP is not asserted for that session.
            valid_minutes = (bool(minutes) and minutes[0] == 0
                             and all(b - a == 5 for a, b in zip(minutes, minutes[1:])))
            positive = current["volume"].notna() & (current["volume"] > 0)
            valid_wap = current["wap_present"] & positive
            good_prefix = (valid_wap & (
                current["minutes_into_rth"].eq(0) |
                current["minutes_into_rth"].diff().eq(5)
            )).cummin().astype(bool) if valid_minutes else pd.Series(
                False, index=indexes)
            weighted = (current["wap"] * current["volume"]).cumsum()
            total = current["volume"].cumsum()
            vwap = weighted / total.where(total > 0)
            frame.loc[indexes, "vwap"] = vwap.where(good_prefix)
            frame.loc[indexes, "vwap_ready"] = good_prefix.to_numpy()

            # For true RVOL20 use 20 fully covered prior 78-bar RTH
            # sessions, at the SAME 5M time position, not a 12-bar proxy.
            frame.loc[indexes, "prior_complete_sessions"] = min(len(complete_prior), 20)
            if len(complete_prior) >= 20:
                prior20 = complete_prior[-20:]
                prior_cum = pd.concat(prior20, axis=1).mean(axis=1)
                target = current.set_index("minutes_into_rth")["volume"].cumsum()
                rvol = target / prior_cum.reindex(target.index)
                frame.loc[indexes, "rvol20"] = rvol.to_numpy()
                frame.loc[indexes, "rvol20_ready"] = rvol.notna().to_numpy()

            # Persist only fully completed 78-candle RTH sessions.
            # Incomplete current day can never be an RVOL reference.
            full = (len(current) == 78 and minutes == list(range(0, 390, 5))
                    and current["volume"].notna().all()
                    and (current["volume"] >= 0).all())
            if full:
                complete_prior.append(
                    current.set_index("minutes_into_rth")["volume"].cumsum()
                )

    status["vwap_ready_rows"] = int(frame["vwap_ready"].sum())
    status["rvol20_ready_rows"] = int(frame["rvol20_ready"].sum())
    status["wap_state"] = ("AVAILABLE" if status["vwap_ready_rows"]
                           else "WAP_MISSING_OR_INCOMPLETE_RTH")
    status["rvol_state"] = ("AVAILABLE" if status["rvol20_ready_rows"]
                            else "INSUFFICIENT_20_FULL_RTH_SESSIONS")
    return frame, status
