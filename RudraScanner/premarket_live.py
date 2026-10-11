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
    """Same-session cumulative IBKR WAP x volume / volume, fail closed on gaps."""
    joined=joined.copy()
    joined["vwap"]=float("nan")
    joined["vwap_ready"]=False
    joined=joined.sort_values(["ticker","timestamp_et"])
    starts={"PRE":240,"RTH":570,"POST":960}
    for (ticker,day,session),part in joined.groupby(
            ["ticker","session_date_et","session"],sort=False):
        minute=part["minute"].astype(int).tolist()
        good=(pd.to_numeric(part["wap"],errors="coerce").gt(0)
              & pd.to_numeric(part["volume"],errors="coerce").gt(0))
        prev=None
        for idx,row in part.iterrows():
            m=int(row["minute"])
            contiguous=(m==starts[session]) if prev is None else (m==prev+5)
            if not contiguous or not bool(good.loc[idx]):
                break
            prev=m
            current=joined.loc[part.index[:part.index.get_loc(idx)+1]]
            total=float(current["volume"].sum())
            joined.loc[idx,"vwap"]=float((current["wap"]*current["volume"]).sum())/total
            joined.loc[idx,"vwap_ready"]=True
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
    frame=f.drop(columns=["session"],errors="ignore").copy()
    frame["timestamp_et"]=pd.to_datetime(frame["datetime"],utc=True).dt.tz_convert(ET)
    frame=frame.merge(v[["ticker","timestamp_et","session_date_et","rvol5",
                         "rvol5_ready","minute","session"]],on=["ticker","timestamp_et"],
                      how="inner",validate="one_to_one")
    frame=_exact_segment_vwap(frame)
    # Require newest completed 5m bar for each ticker. Never replay an old
    # matching bar after the setup ceases to hold.
    latest=frame.sort_values("timestamp_et").groupby("ticker").tail(1)
    if now is None:
        clock=pd.Timestamp.now(tz="UTC")
    else:
        clock=pd.Timestamp(now)
        if clock.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        clock=clock.tz_convert("UTC")
    age=(clock-latest["timestamp_et"].dt.tz_convert("UTC")).dt.total_seconds()
    latest=latest[(age>=300)&(age<=900)]
    ready=latest["vwap_ready"].fillna(False)&latest["ema9_ready"].fillna(False)
    matches=candidates(latest[ready])
    events=[]
    for _,x in matches.iterrows():
        ts=pd.Timestamp(x["timestamp_et"])
        events.append({"ticker":str(x["ticker"]),"bar_et":ts.isoformat(),
                       "uk_time":ts.tz_convert(UK).strftime("%H:%M"),
                       "rv5":round(float(x["rvol5"]),2)})
    state="MATCHES" if events else "NO_SIGNALS"
    return events,{"state":state,"count":len(events),
                   "latest_completed":len(latest),
                   "latest_rvol_ready":int(latest["rvol5_ready"].sum()),
                   "latest_vwap_ready":int(latest["vwap_ready"].sum())}
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
