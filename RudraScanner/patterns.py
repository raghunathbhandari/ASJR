"""Five symmetric RudraScanner patterns on completed 5M candles.

These are transparent DEVELOPMENT rules, not locked user-approved
thresholds. No production alerts are authorised by this module alone.
Every signal requires a supplied index AND sector directional agreement,
actual IBKR WAP VWAP, and a complete RTH bar after the first 30 minutes.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PatternSettings:
    min_relative_volume: float = 1.3  # prior 12-bar median, NOT RVOL20
    breakout_bars: int = 8
    min_ema_slope_pct: float = 0.04
    reclaim_pct: float = 0.3
    overextension_pct: float = 0.75
    retest_tolerance_pct: float = 0.40
    rth_wait_minutes: int = 30
    enabled_for_research: bool = False


PATTERNS = (
    "HITCHHIKER", "BACK$IDE", "RUBBERBAND",
    "SECOND CHANCE", "FASHIONABLY LATE",
)


def _pct(a, b):
    if b is None or pd.isna(b) or float(b) == 0:
        return float("nan")
    return (float(a) / float(b) - 1) * 100


def _technical_patterns(frame, direction, conf):
    """Evaluate only historical preceding bars and current completed close."""
    if len(frame) < max(conf.breakout_bars + 4, 15):
        return []
    current = frame.iloc[-1]
    prev = frame.iloc[-2]
    window = frame.iloc[-(conf.breakout_bars + 1):-1]
    recent = frame.iloc[-4:-1]
    if any(pd.isna(v) for v in (
        current["vwap"], current["ema9"], current["close"],
        current["relative_volume_12bar"], current["ema9_slope5_pct"],
    )):
        return []

    multiplier = 1 if direction == "LONG" else -1
    price = float(current["close"])
    ema = float(current["ema9"])
    vwap = float(current["vwap"])
    slope = float(current["ema9_slope5_pct"]) * multiplier
    volume_ok = (float(current["relative_volume_12bar"]) >=
                 conf.min_relative_volume)
    bullish = price > float(current["open"]) if multiplier > 0 else price < float(current["open"])
    aligned = (price > ema and price > vwap) if multiplier > 0 else (price < ema and price < vwap)
    trend = aligned and slope >= conf.min_ema_slope_pct

    level = float(window["high"].max()) if multiplier > 0 else float(window["low"].min())
    breakout = price > level if multiplier > 0 else price < level
    tight = (
        (recent["close"].max() - recent["close"].min()) /
        max(float(recent["close"].median()), 1e-9) * 100 < 0.8
    )

    # A clean drive, brief consolidation, then the first momentum break.
    hitchhiker = trend and volume_ok and bullish and tight and breakout

    # Price loses the prior trend, forms an incipient reversal, reclaims
    # EMA9 in direction of a VWAP target but has not crossed VWAP yet.
    prev_below = float(prev["close"]) < float(prev["ema9"]) if multiplier > 0 else float(prev["close"]) > float(prev["ema9"])
    reclaim = price > ema if multiplier > 0 else price < ema
    toward_vwap = price <= vwap if multiplier > 0 else price >= vwap
    structure = (price > float(prev["high"]) if multiplier > 0
                 else price < float(prev["low"]))
    backside = prev_below and reclaim and toward_vwap and volume_ok and bullish and structure

    # Snapback from objectively extended prior close relative to EMA9.
    prev_extension = (_pct(float(prev["ema9"]), float(prev["close"]))
                      if multiplier > 0 else _pct(float(prev["close"]), float(prev["ema9"])))
    rubberband = (
        prev_extension >= conf.overextension_pct and bullish and volume_ok
        and structure and reclaim
    )

    # Break -> one-bar pullback to old level -> renewed departure.
    earlier = frame.iloc[-(conf.breakout_bars + 3):-3]
    prior_level = (float(earlier["high"].max()) if multiplier > 0
                   else float(earlier["low"].min()))
    breakout_bar = frame.iloc[-3]
    retest_bar = frame.iloc[-2]
    broke = (float(breakout_bar["close"]) > prior_level if multiplier > 0
             else float(breakout_bar["close"]) < prior_level)
    retest_distance = abs(_pct(
        float(retest_bar["low"] if multiplier > 0 else retest_bar["high"]),
        prior_level))
    held = (float(retest_bar["close"]) >= prior_level if multiplier > 0
            else float(retest_bar["close"]) <= prior_level)
    renewed = (price > float(retest_bar["high"]) if multiplier > 0
               else price < float(retest_bar["low"]))
    second_chance = trend and volume_ok and broke and held and (
        retest_distance <= conf.retest_tolerance_pct) and renewed

    # EMA/VWAP cross confirmed on a completed bar, not merely touch.
    cross = (
        (float(prev["ema9"]) <= float(prev["vwap"])
         and float(current["ema9"]) > vwap)
        if multiplier > 0 else
        (float(prev["ema9"]) >= float(prev["vwap"])
         and float(current["ema9"]) < vwap)
    ) if bool(prev.get("vwap_ready", False)) else False
    fashionably_late = trend and volume_ok and bullish and cross

    found = []
    for name, condition in (
        ("HITCHHIKER", hitchhiker),
        ("BACK$IDE", backside),
        ("RUBBERBAND", rubberband),
        ("SECOND CHANCE", second_chance),
        ("FASHIONABLY LATE", fashionably_late),
    ):
        if condition:
            found.append(name)
    return found


def detect_five_patterns(features, *, index_bias="WAIT", sector_bias_by_ticker=None,
                         settings=None):
    """Return (events, health), using sector-first top-down matching.

    Development signals are disabled unless enabled_for_research=True.
    There are no autotrades or Discord calls. Multiple patterns may
    share a bar; delivery dedup uses ticker+pattern+direction+bar.
    """
    conf = settings or PatternSettings()
    health = {"state": "DISABLED", "tickers": 0,
              "emitted": 0, "blocked_context": 0,
              "blocked_data": 0, "blocked_session": 0,
              "mode": "RESEARCH_ONLY"}
    if not conf.enabled_for_research:
        return [], health
    health["state"] = "OK"
    if features is None or features.empty:
        health["state"] = "DATA_NOT_READY"
        return [], health
    events = []
    sector = sector_bias_by_ticker or {}
    for ticker, all_bars in features.groupby("ticker", sort=False):
        health["tickers"] += 1
        bars = all_bars.sort_values("datetime")
        current = bars.iloc[-1]
        if (str(current["session"]) != "RTH" or
                int(current["minutes_into_rth"]) < conf.rth_wait_minutes):
            health["blocked_session"] += 1
            continue
        if not bool(current["ema9_ready"]) or not bool(current["vwap_ready"]):
            health["blocked_data"] += 1
            continue
        tick_sector_bias = str(sector.get(ticker, "WAIT")).upper()
        if index_bias not in ("LONG", "SHORT") or tick_sector_bias != index_bias:
            health["blocked_context"] += 1
            continue
        # Keep only current US RTH session for pattern lookback; EMA9 stays
        # continuous because it's computed upstream across the day boundary.
        active = bars[(bars["session"] == "RTH") &
                      (bars["session_date_et"] == current["session_date_et"])]
        if len(active) < max(conf.breakout_bars + 4, 15):
            health["blocked_data"] += 1
            continue
        for name in _technical_patterns(active, index_bias, conf):
            events.append({
                "ticker": str(ticker), "pattern": name,
                "direction": index_bias, "bar_start_utc":
                    pd.Timestamp(current["datetime"]).isoformat(),
                "bar_time_uk": str(current["bar_time_uk"]),
                "price": float(current["close"]),
                "ema9": float(current["ema9"]),
                "vwap": float(current["vwap"]),
                "volume_vs_12bar_median": float(current["relative_volume_12bar"]),
                "rvol20": float(current["rvol20"]) if
                    bool(current["rvol20_ready"]) else None,
                "status": "EXPERIMENTAL_RESEARCH",
            })
    health["emitted"] = len(events)
    return events, health
