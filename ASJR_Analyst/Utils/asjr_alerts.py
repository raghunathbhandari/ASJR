"""Five-minute upper/lower wick alerts with compact Discord formatting."""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from Utils.asjr_day import session_date


ET = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")
STATE_FILE = Path(__file__).resolve().parents[1] / "alert_state.json"
CODE_FENCE = chr(96) * 3

# Wick-only alert policy. Keep thresholds selective enough to reject ordinary
# 5-minute noise while allowing delayed IBKR historical bars to be detected.
WICK_MIN_RANGE_PCT = 1.50
WICK_MIN_PRICE_PCT = 0.35
WICK_MIN_RANGE_SHARE = 0.50
WICK_MIN_BODY_MULTIPLE = 1.50
WICK_MIN_PRIOR_MEDIAN_RANGE_MULTIPLE = 0.50

# IBKR historical 5m data can trail real time by more than 10 minutes.
# Scan completed bars from the last 60 minutes so a genuine wick is not lost
# merely because the bar arrived late. prepare_alert() handles deduplication.
WICK_LOOKBACK_MINUTES = 60


def _volume_context(prior, volume):
    baseline = pd.to_numeric(prior["volume"], errors="coerce").dropna()
    baseline = baseline[baseline > 0]
    volume_x = volume / baseline.median() if len(baseline) >= 5 else None
    return round(volume_x, 2) if pd.notna(volume_x) else None


def _wick_event(ticker, frame, idx, side):
    row = frame.iloc[idx]

    open_price = float(row["open"])
    high = float(row["high"])
    low = float(row["low"])
    close = float(row["close"])
    volume = float(row["volume"])

    candle_range = high - low
    if candle_range <= 0 or close <= 0:
        return None

    body = abs(close - open_price)
    if side == "LOWER":
        wick = min(open_price, close) - low
    else:
        wick = high - max(open_price, close)

    range_pct = candle_range / close * 100.0
    wick_share = wick / candle_range
    wick_price_pct = wick / close * 100.0

    prior = frame.iloc[max(0, idx - 12):idx]
    prior_ranges = (
        pd.to_numeric(prior["high"], errors="coerce")
        - pd.to_numeric(prior["low"], errors="coerce")
    ).dropna()
    prior_ranges = prior_ranges[prior_ranges > 0]
    prior_median_range = (
        float(prior_ranges.median()) if len(prior_ranges) >= 5 else None
    )

    if range_pct < WICK_MIN_RANGE_PCT:
        return None
    if wick_price_pct < WICK_MIN_PRICE_PCT:
        return None
    if wick_share < WICK_MIN_RANGE_SHARE:
        return None
    if wick < max(body * WICK_MIN_BODY_MULTIPLE, 0.01):
        return None
    if (
        prior_median_range is not None
        and wick < prior_median_range * WICK_MIN_PRIOR_MEDIAN_RANGE_MULTIPLE
    ):
        return None

    prior_low = pd.to_numeric(prior["low"], errors="coerce").min()
    prior_high = pd.to_numeric(prior["high"], errors="coerce").max()

    if side == "LOWER":
        swept_level = (
            bool(low < prior_low and close > prior_low)
            if pd.notna(prior_low)
            else False
        )
        prior_level = float(prior_low) if pd.notna(prior_low) else None
        event_type = "LOWER_WICK"
        event_name = "LONG LOWER WICK"
    else:
        swept_level = (
            bool(high > prior_high and close < prior_high)
            if pd.notna(prior_high)
            else False
        )
        prior_level = float(prior_high) if pd.notna(prior_high) else None
        event_type = "UPPER_WICK"
        event_name = "LONG UPPER WICK"

    next_row = frame.iloc[idx + 1] if idx + 1 < len(frame) else None
    next_confirmed = None
    if next_row is not None:
        if side == "LOWER":
            next_confirmed = bool(float(next_row["low"]) > low)
        else:
            next_confirmed = bool(float(next_row["high"]) < high)

    bar_time = row["bar_et"]

    return {
        "type": event_type,
        "ticker": str(ticker),
        "bar_time_et": bar_time.strftime("%Y-%m-%d %H:%M ET"),
        "event": event_name,
        "session": (
            "RTH"
            if (9, 30) <= (bar_time.hour, bar_time.minute) < (16, 0)
            else "EXTENDED"
        ),
        "open": open_price,
        "high": high,
        "low": low,
        "price": close,
        "volume": volume,
        "volume_x": _volume_context(prior, volume),
        "wick": wick,
        "wick_pct": wick_price_pct,
        "wick_share_pct": wick_share * 100.0,
        "range_pct": range_pct,
        "prior_level": prior_level,
        "swept_reclaimed": swept_level,
        "next_confirmed": next_confirmed,
    }


def build_wick_alerts(intraday, trade_date=None, now=None):
    """Return significant upper/lower wick events from recent completed bars."""
    if intraday is None or intraday.empty:
        return []

    now_et = pd.Timestamp(now if now is not None else datetime.now(ET))
    now_et = (
        now_et.tz_localize(ET)
        if now_et.tzinfo is None
        else now_et.tz_convert(ET)
    )
    day = (
        str(trade_date)[:10]
        if trade_date is not None
        else now_et.date().isoformat()
    )
    cutoff = now_et - pd.Timedelta(minutes=WICK_LOOKBACK_MINUTES)
    events = []

    for ticker, frame in intraday.groupby("ticker"):
        frame = frame.sort_values("datetime").copy()
        dates = pd.to_datetime(frame["datetime"], utc=True).dt.tz_convert(ET)
        frame["bar_et"] = dates

        frame = frame[
            (dates.map(session_date).astype(str) == day)
            & (dates + pd.Timedelta(minutes=5) <= now_et)
            & (dates + pd.Timedelta(minutes=5) >= cutoff)
        ].copy()

        if frame.empty:
            continue

        for idx in range(len(frame)):
            lower = _wick_event(ticker, frame, idx, "LOWER")
            if lower is not None:
                events.append(lower)

            upper = _wick_event(ticker, frame, idx, "UPPER")
            if upper is not None:
                events.append(upper)

    return sorted(
        events,
        key=lambda e: (
            e["bar_time_et"],
            e["ticker"],
            e["type"],
        ),
    )


# Backward-compatible callable for any older imports. It is wick-only.
def build_ema20_alerts(intraday, trade_date=None, now=None):
    return build_wick_alerts(intraday, trade_date=trade_date, now=now)


def prepare_alert(result, state_file=STATE_FILE):
    """Return one Discord wick message, or "" when there is no new wick."""
    events = result.get("alert_data", []) if result else []
    events = [
        e for e in events
        if e.get("type") in {"LOWER_WICK", "UPPER_WICK"}
    ]
    if not events:
        return ""

    state_file = Path(state_file)

    try:
        sent = json.loads(state_file.read_text(encoding="utf-8"))
        if not isinstance(sent, dict):
            sent = {}
    except (OSError, ValueError):
        sent = {}

    header = "ASJR 5M WICK ALERTS | candle times UK\n"
    blocks = []
    added = []

    for e in events:
        ticker = e["ticker"]
        event_type = e["type"]
        key = f'{ticker}|{e["bar_time_et"]}|{event_type}|{e["event"]}'

        if key in sent:
            continue

        bar_time_uk = (
            datetime.strptime(e["bar_time_et"], "%Y-%m-%d %H:%M ET")
            .replace(tzinfo=ET)
            .astimezone(UK)
            .strftime("%Y-%m-%d %H:%M %Z")
        )

        volume = (
            f'{e["volume_x"]:.1f}x prior 12-bar median'
            if e.get("volume_x") is not None
            else "comparison unavailable"
        )
        prior_level = (
            f'{e["prior_level"]:.2f}'
            if e.get("prior_level") is not None
            else "n/a"
        )
        sweep = "YES" if e.get("swept_reclaimed") else "NO"

        if event_type == "LOWER_WICK":
            label = "LONG LOWER WICK"
            level_name = "12-bar low"
            next_state = (
                "waiting next candle"
                if e.get("next_confirmed") is None
                else (
                    "held low / higher low"
                    if e.get("next_confirmed")
                    else "low not confirmed"
                )
            )
        else:
            label = "LONG UPPER WICK"
            level_name = "12-bar high"
            next_state = (
                "waiting next candle"
                if e.get("next_confirmed") is None
                else (
                    "held high / lower high"
                    if e.get("next_confirmed")
                    else "high not confirmed"
                )
            )

        block = (
            f'\n{ticker} {label} [{e["session"]}] {bar_time_uk}\n'
            f'O {e["open"]:.2f} H {e["high"]:.2f} L {e["low"]:.2f} C {e["price"]:.2f}\n'
            f'Wick {e["wick"]:.2f} '
            f'({e["wick_pct"]:.2f}% price, {e["wick_share_pct"]:.0f}% candle) | '
            f'{level_name} {prior_level} swept/reclaimed: {sweep}\n'
            f'Vol {e["volume"]:,.0f} ({volume}) | Next: {next_state}\n'
        )

        if len(CODE_FENCE + "\n" + header + "".join(blocks) + block + CODE_FENCE) > 1900:
            break

        blocks.append(block)
        added.append(key)

    if not blocks:
        return ""

    message = CODE_FENCE + "\n" + header + "".join(blocks) + CODE_FENCE

    for key in added:
        sent[key] = True

    sent = dict(list(sent.items())[-2000:])
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temp = state_file.with_suffix(".tmp")
    temp.write_text(json.dumps(sent, indent=2), encoding="utf-8")
    os.replace(temp, state_file)

    return message
