"""Strict completed-bar RVOL5 + IBKR WAP VWAP BUY WATCH, fail closed."""
from __future__ import annotations
import json,os
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from .features import build_scanner_features
from .premarket_rvol import calculate,candidates,durable_reference_path
UK=ZoneInfo("Europe/London")
ET=ZoneInfo("America/New_York")
CONFIG=Path(__file__).resolve().parent/"premarket_alert_config.json"
def enabled():
    try:return json.loads(CONFIG.read_text()).get("enabled") is True
    except (OSError,ValueError):return False
def _exact_segment_vwap(joined):
    """Exact per-segment IBKR-WAP VWAP. Fail closed after any missing bar."""
    joined = joined.sort_values(["ticker", "timestamp_et"]).copy()
    joined["vwap"] = float("nan")
    joined["vwap_ready"] = False
    starts = {"PRE": 240, "RTH": 570, "POST": 960}
    groups = joined.groupby(["ticker", "session_date_et", "session"], sort=False)
    for (_, _, session), part in groups:
        if session not in starts:
            continue
        minute = part["minute"].astype(int)
        start = starts[session]
        expected = pd.Series(range(start, start + 5 * len(part), 5), index=part.index)
        volume = pd.to_numeric(part["volume"], errors="coerce")
        wap = pd.to_numeric(part["wap"], errors="coerce")
        # IBKR can supply genuine zero-trade 5m bars before the US open.
        # A zero-volume bar adds no weight; carry forward the prior VWAP.
        # A missing WAP on a POSITIVE-volume bar still invalidates the prefix.
        valid = (minute.eq(expected) & volume.ge(0)
                 & (volume.eq(0) | wap.gt(0)))
        valid_prefix = valid.cummin().astype(bool)
        weighted = (wap.where(volume.gt(0), 0).fillna(0) * volume).cumsum()
        total = volume.cumsum()
        ready = valid_prefix & total.gt(0)
        joined.loc[part.index, "vwap"] = (
            weighted / total.where(total.gt(0))).where(ready)
        joined.loc[part.index, "vwap_ready"] = ready.to_numpy()
    return joined

def evaluate(raw,root,day,now=None):
    if raw is None or raw.empty:
        return [],{"state":"NO_BARS"}
    f,_=build_scanner_features(raw,now=now)
    if f.empty:
        return [],{"state":"NO_COMPLETED_BARS"}
    source=durable_reference_path(root)
    if not source.is_file():
        return [],{"state":"NO_REFERENCE"}
    ref=pd.read_csv(source)
    v=calculate(f[["ticker","datetime","volume"]].copy(),ref,trading_day=str(day))
    if v.empty:
        return [],{"state":"NO_CURRENT_SESSION"}
    frame=f.drop(columns=["session","session_date_et","vwap","vwap_ready"],errors="ignore").copy()
    frame["timestamp_et"]=pd.to_datetime(frame["datetime"],utc=True).dt.tz_convert(ET)
    frame=frame.merge(v[["ticker","timestamp_et","session_date_et","rvol5",
                         "rvol5_ready","minute","session"]],on=["ticker","timestamp_et"],
                      how="inner",validate="one_to_one")
    frame=_exact_segment_vwap(frame)
    # Require newest completed 5m bar for each ticker. Never replay an old
    # matching bar after the setup ceases to hold.
    newest = frame.sort_values("timestamp_et").groupby("ticker").tail(1)
    if now is None:
        clock = pd.Timestamp.now(tz="UTC")
    else:
        clock = pd.Timestamp(now)
        if clock.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        clock = clock.tz_convert("UTC")
    # IBKR timestamps denote candle START, not close. Evaluate only a
    # completed bar, and reject results older than the normal Chakra cadence.
    age = (clock - newest["timestamp_et"].dt.tz_convert("UTC")).dt.total_seconds()
    latest = newest.loc[age.between(300, 900, inclusive="both")].copy()
    vwap_ready = latest["vwap_ready"].fillna(False)
    ema_ready = latest["ema9_ready"].fillna(False)
    volume_ready = pd.to_numeric(latest["volume"], errors="coerce").gt(0)
    ready = vwap_ready & ema_ready & volume_ready
    matches = candidates(latest.loc[ready])
    events = []
    for _, x in matches.iterrows():
        ts = pd.Timestamp(x["timestamp_et"])
        events.append({"ticker": str(x["ticker"]), "bar_et": ts.isoformat(),
                       "uk_time": ts.tz_convert(UK).strftime("%H:%M"),
                       "rv5": round(float(x["rvol5"]), 2)})
    if events:
        state = "MATCHES"
    elif latest.empty:
        state = "NO_FRESH_COMPLETED_BAR"
    elif not vwap_ready.any():
        state = "WAP_MISSING_OR_SEGMENT_GAP"
    elif not latest["rvol5_ready"].any():
        state = "RVOL5_NOT_READY"
    else:
        state = "NO_SIGNALS"
    return events, {
        "state": state,
        "count": len(events),
        "asof_utc": clock.isoformat(),
        "latest_seen": len(newest),
        "newest_bar_et": (newest["timestamp_et"].max().isoformat()
                          if not newest.empty else None),
        "latest_completed": len(latest),
        "rejected_stale_or_not_closed": len(newest) - len(latest),
        "latest_rvol_ready": int(latest["rvol5_ready"].sum()),
        "latest_vwap_ready": int(vwap_ready.sum()),
        "latest_ema9_ready": int(ema_ready.sum()),
        "latest_positive_volume": int(volume_ready.sum()),
    }
def fresh_for_dispatch(events, *, now=None, max_age_seconds=900):
    """Fail closed before Chakra Discord formatting if the pipeline was slow.

    Event candle times are starts. A valid alert is already completed and
    no older than the same 15-minute freshness rule used during evaluation.
    """
    if now is None:
        clock = pd.Timestamp.now(tz="UTC")
    else:
        clock = pd.Timestamp(now)
        if clock.tzinfo is None:
            raise ValueError("Dispatch time must be timezone-aware")
        clock = clock.tz_convert("UTC")
    fresh = []
    for event in events or []:
        try:
            stamp = pd.Timestamp(event["bar_et"])
            if stamp.tzinfo is None:
                continue
            age = (clock - stamp.tz_convert("UTC")).total_seconds()
            if 300 <= age <= max_age_seconds:
                fresh.append(event)
        except (KeyError, ValueError, TypeError):
            continue
    return fresh


def prepare(events,root):
    """Reserve unsent keys; persist pending; only acknowledge after Discord success."""
    state=Path(root)/"ASJR_Analyst/state/rudra_premarket_delivery.json"
    try:obj=json.loads(state.read_text())
    except (OSError,ValueError):obj={"sent":[]}
    done=set(obj.get("sent",[]))
    fresh=[e for e in events if e["ticker"]+"|"+e["bar_et"] not in done]
    if not fresh:return ""
    lines=["RUDRA-PREMARKET"]
    for e in fresh:
        lines.append(f'{e["ticker"]} | {e["uk_time"]} | BUY WATCH | Price > EMA9 > VWAP | RV5 {e["rv5"]:.2f}x')
    return "\n".join(lines)
def acknowledge(events,root):
    state=Path(root)/"ASJR_Analyst/state/rudra_premarket_delivery.json"
    try:obj=json.loads(state.read_text())
    except (OSError,ValueError):obj={"sent":[]}
    keys=[e["ticker"]+"|"+e["bar_et"] for e in events]
    obj["sent"]=list(dict.fromkeys((obj.get("sent",[])+keys)))[-3000:]
    state.parent.mkdir(parents=True,exist_ok=True)
    temp=state.with_suffix(".tmp")
    temp.write_text(json.dumps(obj))
    os.replace(temp,state)
