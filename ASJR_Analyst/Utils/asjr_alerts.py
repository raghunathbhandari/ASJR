"""Five-minute EMA20 events and compact Discord formatting."""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from Utils.asjr_day import session_date


ET = ZoneInfo("America/New_York")
STATE_FILE = Path(__file__).resolve().parents[1] / "alert_state.json"


def build_ema20_alerts(intraday, trade_date=None, now=None):
    """Return fresh crosses on completed 5m candles, without another fetch.

    The previous two completed bars are checked so a slightly late Chakra run
    does not miss an event. The formatter deduplicates by ticker/bar/direction.
    """
    if intraday is None or intraday.empty:
        return []

    now_et = pd.Timestamp(now if now is not None else datetime.now(ET))
    now_et = now_et.tz_localize(ET) if now_et.tzinfo is None else now_et.tz_convert(ET)
    day = str(trade_date)[:10] if trade_date is not None else now_et.date().isoformat()
    events = []

    for ticker, frame in intraday.groupby("ticker"):
        frame = frame.sort_values("datetime").copy()
        dates = pd.to_datetime(frame["datetime"], utc=True).dt.tz_convert(ET)
        frame["bar_et"] = dates
        frame = frame[(dates.map(session_date).astype(str) == day) &
                      (dates + pd.Timedelta(minutes=5) <= now_et)].copy()
        if frame.empty:
            continue

        for idx in range(max(0, len(frame) - 2), len(frame)):
            row = frame.iloc[idx]
            up, down = bool(row["cross_up"]), bool(row["cross_down"])
            if not (up or down):
                continue
            bar_time = row["bar_et"]
            # Only current events: suppress yesterday's/earlier stale candles.
            if now_et - (bar_time + pd.Timedelta(minutes=5)) > pd.Timedelta(minutes=11):
                continue
            prior = frame.iloc[max(0, idx - 12):idx]
            vol = float(row["volume"])
            baseline = pd.to_numeric(prior["volume"], errors="coerce").dropna()
            baseline = baseline[baseline > 0]
            volume_x = vol / baseline.median() if len(baseline) >= 5 else None
            ema = float(row["ema20"])
            close = float(row["close"])
            prior_high = pd.to_numeric(prior["high"], errors="coerce").max()
            event = {
                "ticker": str(ticker),
                "bar_time_et": bar_time.strftime("%Y-%m-%d %H:%M ET"),
                "event": "CROSSED ABOVE" if up else "CROSSED BELOW",
                "price": close,
                "ema20": ema,
                "distance_pct": (close / ema - 1) * 100 if ema else None,
                "volume": vol,
                "volume_x": round(volume_x, 2) if pd.notna(volume_x) else None,
                "ema_rising": bool(ema > float(frame.iloc[idx - 1]["ema20"])) if idx else None,
                "prior_12_high_break": bool(close > prior_high) if pd.notna(prior_high) else None,
                "session": "RTH" if (9, 30) <= (bar_time.hour, bar_time.minute) < (16, 0) else "EXTENDED",
            }
            events.append(event)

    return sorted(events, key=lambda e: (e["bar_time_et"], e["ticker"]))


def prepare_alert(result, state_file=STATE_FILE):
    """Return a single Discord code block and remember the included events."""
    events = result.get("alert_data", []) if result else []
    if not events:
        return ""
    state_file = Path(state_file)
    try:
        sent = json.loads(state_file.read_text(encoding="utf-8"))
        if not isinstance(sent, dict):
            sent = {}
    except (OSError, ValueError):
        sent = {}

    header = "ASJR 5M EMA20 | candle times ET\n"
    blocks = []
    added = []
    for e in events:
        ticker = e["ticker"]
        key = f'{ticker}|{e["bar_time_et"]}|{e["event"]}'
        if key in sent:
            continue
        volume = f'{e["volume_x"]:.1f}x prior 12-bar median' if e["volume_x"] is not None else 'comparison unavailable'
        slope = 'rising' if e["ema_rising"] else 'flat/falling' if e["ema_rising"] is not None else 'unavailable'
        distance = f'{e["distance_pct"]:+.2f}%' if e["distance_pct"] is not None else 'n/a'
        breakout = ' | 12-bar high break' if e["prior_12_high_break"] else ''
        block = (f'\n{ticker} [{e["session"]}] {e["bar_time_et"]}\n'
                 f'EMA20: {e["event"]} | Close ${e["price"]:.2f} | EMA ${e["ema20"]:.2f} ({distance})\n'
                 f'Vol: {e["volume"]:,.0f} ({volume}) | EMA: {slope}{breakout}\n')
        if len('```\n' + header + ''.join(blocks) + block + '```') > 1900:
            break
        blocks.append(block)
        added.append(key)

    if not blocks:
        return ""
    message = '```\n' + header + ''.join(blocks) + '```'
    for key in added:
        sent[key] = True
    # The last few sessions suffice; keep the local state small.
    sent = dict(list(sent.items())[-2000:])
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temp = state_file.with_suffix('.tmp')
    temp.write_text(json.dumps(sent, indent=2), encoding='utf-8')
    os.replace(temp, state_file)
    return message
