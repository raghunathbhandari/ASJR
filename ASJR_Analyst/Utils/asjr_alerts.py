"""Five-minute EMA20 and long-lower-wick events with compact Discord formatting."""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from Utils.asjr_day import session_date


ET = ZoneInfo("America/New_York")
STATE_FILE = Path(__file__).resolve().parents[1] / "alert_state.json"
CODE_FENCE = chr(96) * 3

# Selective defaults so ordinary 5-minute candle noise does not flood Discord.
# A LONG-WICK alert must be visually/materially significant, not merely a
# large percentage of a tiny candle.  The old 0.20% range rule incorrectly
# flagged candles such as IOVA 2026-09-29 15:50 ET (only 0.31% price wick).
WICK_MIN_RANGE_PCT = 0.50
WICK_MIN_PRICE_PCT = 0.35
WICK_MIN_RANGE_SHARE = 0.50
WICK_MIN_BODY_MULTIPLE = 1.50
WICK_MIN_PRIOR_MEDIAN_RANGE_MULTIPLE = 0.50


def _volume_context(prior, volume):
    baseline = pd.to_numeric(prior["volume"], errors="coerce").dropna()
    baseline = baseline[baseline > 0]
    volume_x = volume / baseline.median() if len(baseline) >= 5 else None
    return round(volume_x, 2) if pd.notna(volume_x) else None


def _long_lower_wick_event(ticker, frame, idx):
    row = frame.iloc[idx]

    open_price = float(row["open"])
    high = float(row["high"])
    low = float(row["low"])
    close = float(row["close"])
    ema = float(row["ema20"])
    volume = float(row["volume"])

    candle_range = high - low
    if candle_range <= 0 or close <= 0:
        return None

    body = abs(close - open_price)
    lower_wick = min(open_price, close) - low
    range_pct = candle_range / close * 100.0
    wick_share = lower_wick / candle_range
    wick_price_pct = lower_wick / close * 100.0

    prior = frame.iloc[max(0, idx - 12):idx]
    prior_ranges = (
        pd.to_numeric(prior["high"], errors="coerce")
        - pd.to_numeric(prior["low"], errors="coerce")
    ).dropna()
    prior_ranges = prior_ranges[prior_ranges > 0]
    prior_median_range = (
        float(prior_ranges.median()) if len(prior_ranges) >= 5 else None
    )

    # Reject tiny/noisy candles even when the wick is a high percentage of
    # that candle.  Require material size versus price AND recent 5m ranges.
    if range_pct < WICK_MIN_RANGE_PCT:
        return None
    if wick_price_pct < WICK_MIN_PRICE_PCT:
        return None
    if wick_share < WICK_MIN_RANGE_SHARE:
        return None
    if lower_wick < max(body * WICK_MIN_BODY_MULTIPLE, 0.01):
        return None
    if (
        prior_median_range is not None
        and lower_wick
        < prior_median_range * WICK_MIN_PRIOR_MEDIAN_RANGE_MULTIPLE
    ):
        return None

    prior_low = pd.to_numeric(prior["low"], errors="coerce").min()
    swept_prior_low = (
        bool(low < prior_low and close > prior_low)
        if pd.notna(prior_low)
        else False
    )

    next_row = frame.iloc[idx + 1] if idx + 1 < len(frame) else None
    next_holds_low = None
    next_higher_low = None
    if next_row is not None:
        next_low = float(next_row["low"])
        next_holds_low = bool(next_low > low)
        next_higher_low = bool(next_low > low)

    bar_time = row["bar_et"]

    return {
        "type": "LOWER_WICK",
        "ticker": str(ticker),
        "bar_time_et": bar_time.strftime("%Y-%m-%d %H:%M ET"),
        "event": "LONG LOWER WICK",
        "session": (
            "RTH"
            if (9, 30) <= (bar_time.hour, bar_time.minute) < (16, 0)
            else "EXTENDED"
        ),
        "open": open_price,
        "high": high,
        "low": low,
        "price": close,
        "ema20": ema,
        "distance_pct": (close / ema - 1) * 100 if ema else None,
        "volume": volume,
        "volume_x": _volume_context(prior, volume),
        "lower_wick": lower_wick,
        "wick_pct": lower_wick / close * 100.0,
        "wick_share_pct": wick_share * 100.0,
        "range_pct": range_pct,
        "prior_12_low": float(prior_low) if pd.notna(prior_low) else None,
        "swept_prior_low": swept_prior_low,
        "next_holds_low": next_holds_low,
        "next_higher_low": next_higher_low,
    }


def build_ema20_alerts(intraday, trade_date=None, now=None):
    """Return fresh EMA20 crosses and significant lower-wick events.

    The previous two completed 5-minute bars are checked so a slightly late
    Chakra run does not miss an event. Discord formatting deduplicates by
    ticker, bar time and event type.
    """
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
    events = []

    for ticker, frame in intraday.groupby("ticker"):
        frame = frame.sort_values("datetime").copy()
        dates = pd.to_datetime(frame["datetime"], utc=True).dt.tz_convert(ET)
        frame["bar_et"] = dates
        frame = frame[
            (dates.map(session_date).astype(str) == day)
            & (dates + pd.Timedelta(minutes=5) <= now_et)
        ].copy()

        if frame.empty:
            continue

        for idx in range(max(0, len(frame) - 2), len(frame)):
            row = frame.iloc[idx]
            bar_time = row["bar_et"]

            if (
                now_et - (bar_time + pd.Timedelta(minutes=5))
                > pd.Timedelta(minutes=11)
            ):
                continue

            prior = frame.iloc[max(0, idx - 12):idx]
            vol = float(row["volume"])

            up = bool(row["cross_up"])
            down = bool(row["cross_down"])

            if up or down:
                ema = float(row["ema20"])
                close = float(row["close"])
                prior_high = pd.to_numeric(
                    prior["high"],
                    errors="coerce",
                ).max()

                events.append({
                    "type": "EMA20",
                    "ticker": str(ticker),
                    "bar_time_et": bar_time.strftime("%Y-%m-%d %H:%M ET"),
                    "event": "CROSSED ABOVE" if up else "CROSSED BELOW",
                    "price": close,
                    "ema20": ema,
                    "distance_pct": (
                        (close / ema - 1) * 100
                        if ema
                        else None
                    ),
                    "volume": vol,
                    "volume_x": _volume_context(prior, vol),
                    "ema_rising": (
                        bool(ema > float(frame.iloc[idx - 1]["ema20"]))
                        if idx
                        else None
                    ),
                    "prior_12_high_break": (
                        bool(close > prior_high)
                        if pd.notna(prior_high)
                        else None
                    ),
                    "session": (
                        "RTH"
                        if (9, 30) <= (bar_time.hour, bar_time.minute) < (16, 0)
                        else "EXTENDED"
                    ),
                })

            wick_event = _long_lower_wick_event(ticker, frame, idx)
            if wick_event is not None:
                events.append(wick_event)

    return sorted(
        events,
        key=lambda e: (
            e["bar_time_et"],
            e["ticker"],
            e.get("type", ""),
        ),
    )


def prepare_alert(result, state_file=STATE_FILE):
    """Return one compact Discord code block and remember included events."""
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

    header = "ASJR 5M ALERTS | candle times ET\n"
    blocks = []
    added = []

    for e in events:
        ticker = e["ticker"]
        event_type = e.get("type", "EMA20")
        key = f'{ticker}|{e["bar_time_et"]}|{event_type}|{e["event"]}'

        if key in sent:
            continue

        volume = (
            f'{e["volume_x"]:.1f}x prior 12-bar median'
            if e.get("volume_x") is not None
            else "comparison unavailable"
        )
        distance = (
            f'{e["distance_pct"]:+.2f}%'
            if e.get("distance_pct") is not None
            else "n/a"
        )

        if event_type == "LOWER_WICK":
            sweep = "YES" if e.get("swept_prior_low") else "NO"
            prior_low = (
                f'{e["prior_12_low"]:.2f}'
                if e.get("prior_12_low") is not None
                else "n/a"
            )

            next_state = "waiting next candle"
            if e.get("next_holds_low") is not None:
                next_state = (
                    "held low / higher low"
                    if e.get("next_higher_low")
                    else "low not confirmed"
                )

            block = (
                f'\n{ticker} LONG-WICK REVIEW [{e["session"]}] {e["bar_time_et"]}\n'
                f'O {e["open"]:.2f} H {e["high"]:.2f} L {e["low"]:.2f} C {e["price"]:.2f}\n'
                f'Lower wick {e["lower_wick"]:.2f} '
                f'({e["wick_pct"]:.2f}% price, {e["wick_share_pct"]:.0f}% candle) | '
                f'12-bar low {prior_low} swept/reclaimed: {sweep}\n'
                f'EMA20 {e["ema20"]:.2f} ({distance}) | '
                f'Vol {e["volume"]:,.0f} ({volume}) | Next: {next_state}\n'
            )

        else:
            slope = (
                "rising"
                if e.get("ema_rising")
                else (
                    "flat/falling"
                    if e.get("ema_rising") is not None
                    else "unavailable"
                )
            )
            breakout = (
                " | 12-bar high break"
                if e.get("prior_12_high_break")
                else ""
            )
            block = (
                f'\n{ticker} [{e["session"]}] {e["bar_time_et"]}\n'
                f'EMA20: {e["event"]} | Close {e["price"]:.2f} | '
                f'EMA {e["ema20"]:.2f} ({distance})\n'
                f'Vol: {e["volume"]:,.0f} ({volume}) | EMA: {slope}{breakout}\n'
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
