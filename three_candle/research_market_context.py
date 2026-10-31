"""Causal, descriptive NQ 15-minute market-context features.

No signal generation, filtering, outcome labelling or trade execution here.
Each row uses the current and previous completed candles only. Session VWAP
resets at NQ futures trading-date boundary. History with gaps is not filled.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def calculate_market_context(data: pd.DataFrame) -> pd.DataFrame:
    """Return context columns indexed identically to a timezone-aware OHLCV frame."""
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(data.columns):
        raise ValueError("Missing OHLCV columns")
    if data.index.tz is None:
        raise ValueError("Timezone-aware index required")
    x = data.sort_index().copy()
    if x.index.has_duplicates:
        raise ValueError("Duplicate candle index")
    if x.empty:
        return pd.DataFrame(index=x.index)
    result = pd.DataFrame(index=x.index)
    h, l, c, o, vol = (x[k].astype(float) for k in
                        ("High", "Low", "Close", "Open", "Volume"))
    close_prev = c.shift(1)
    et = x.index.tz_convert("America/New_York")
    # NQ trade date: session opens 18:00 ET, ends 17:00 ET next day.
    d = et.normalize() + pd.to_timedelta((et.hour >= 18).astype(int), unit="D")
    session = pd.Series(d.strftime("%Y-%m-%d"), index=x.index)
    result["nq_trade_date_et"] = session
    hour = pd.Series(et.hour, index=x.index)
    result["market_session"] = np.select(
        [(hour >= 18) | (hour < 3), (hour >= 3) & (hour < 9),
         (hour >= 9) & (hour < 16)],
        ["US_OVERNIGHT", "EUROPE", "US_DAY"], default="US_LATE")
    typical = (h + l + c) / 3
    pv = typical * vol
    v_sum = vol.groupby(session).cumsum()
    result["session_vwap"] = pv.groupby(session).cumsum() / v_sum.where(v_sum > 0)
    result["vwap_distance_pct"] = 100 * (c - result.session_vwap) / result.session_vwap
    result["vwap_reclaim_up"] = ((close_prev <= result.session_vwap.shift(1)) &
                                (c > result.session_vwap)).astype(int)
    result["vwap_reclaim_down"] = ((close_prev >= result.session_vwap.shift(1)) &
                                  (c < result.session_vwap)).astype(int)

    m9 = c.ewm(span=9, adjust=False).mean()
    m21 = c.ewm(span=21, adjust=False).mean()
    result["ema9_slope_pct_3bar"] = 100 * (m9 / m9.shift(3) - 1)
    result["ema21_slope_pct_3bar"] = 100 * (m21 / m21.shift(3) - 1)
    result["ema9_distance_pct"] = 100 * (c / m9 - 1)
    result["ema21_distance_pct"] = 100 * (c / m21 - 1)
    diff = c.diff()
    gain = diff.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-diff).clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    rsi = 100 * gain / (gain + loss)
    result["rsi14_change_candle"] = rsi.diff()
    result["rsi14_change_3bar"] = rsi.diff(3)
    tr = pd.concat([(h-l), (h-close_prev).abs(), (l-close_prev).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/14, adjust=False).mean()
    result["candle_range_to_atr14"] = (h-l) / atr.where(atr > 0)
    result["atr14_pct"] = 100 * atr / c
    result["atr_percentile_100bar"] = result.atr14_pct.rolling(100, min_periods=100).apply(
        lambda v: 100 * np.mean(v <= v[-1]), raw=True)

    basis = c.rolling(20, min_periods=20).mean()
    dev = c.rolling(20, min_periods=20).std(ddof=0)
    upper, lower = basis + 2*dev, basis - 2*dev
    width = 100 * (upper-lower) / basis.where(basis != 0)
    result["bb20_width_pct"] = width
    result["bb20_width_percentile_100bar"] = width.rolling(100, min_periods=100).apply(
        lambda v: 100 * np.mean(v <= v[-1]), raw=True)
    result["bb20_position"] = (c-lower) / (upper-lower).where((upper-lower) != 0)
    result["compression_to_expansion"] = (
        (result.bb20_width_percentile_100bar.shift(1) <= 25) &
        (result.candle_range_to_atr14 > 1.3)
    ).astype(int)

    prior_high = h.shift(1).rolling(20, min_periods=20).max()
    prior_low = l.shift(1).rolling(20, min_periods=20).min()
    result["prior_20bar_high"] = prior_high
    result["prior_20bar_low"] = prior_low
    result["liquidity_sweep_high_pct"] = (100 * (h-prior_high)/c).where(
        (h > prior_high) & (c < prior_high), 0.0)
    result["liquidity_sweep_low_pct"] = (100 * (prior_low-l)/c).where(
        (l < prior_low) & (c > prior_low), 0.0)
    result["break_of_structure_up"] = (c > prior_high).astype(int)
    result["break_of_structure_down"] = (c < prior_low).astype(int)
    result["structure_shift_up"] = (
        (result.break_of_structure_up == 1) &
        (result.break_of_structure_down.shift(1).rolling(20, min_periods=1).max() == 1)
    ).astype(int)
    result["structure_shift_down"] = (
        (result.break_of_structure_down == 1) &
        (result.break_of_structure_up.shift(1).rolling(20, min_periods=1).max() == 1)
    ).astype(int)

    # Previous completed futures trade-date highs/lows: no partial current-day lookahead.
    day_hi = h.groupby(session).max()
    day_lo = l.groupby(session).min()
    full_hi = day_hi.shift(1)
    full_lo = day_lo.shift(1)
    result["previous_trade_day_high"] = session.map(full_hi)
    result["previous_trade_day_low"] = session.map(full_lo)
    result["distance_prev_day_high_pct"] = 100 * (c/result.previous_trade_day_high - 1)
    result["distance_prev_day_low_pct"] = 100 * (c/result.previous_trade_day_low - 1)

    trend_up = (c > m21) & (result.ema9_slope_pct_3bar > 0) & (m9 > m21)
    trend_down = (c < m21) & (result.ema9_slope_pct_3bar < 0) & (m9 < m21)
    compressed = result.bb20_width_percentile_100bar <= 25
    result["market_regime"] = np.select(
        [compressed, trend_up, trend_down],
        ["COMPRESSION", "UPTREND", "DOWNTREND"], default="RANGE_OR_MIXED")
    # Unconfirmed warmup cannot confidently classify a regime.
    result.loc[result.bb20_width_percentile_100bar.isna(), "market_regime"] = "UNKNOWN_WARMUP"
    result["range_position_20bar"] = (c-prior_low) / (prior_high-prior_low).where(
        (prior_high-prior_low) > 0)
    return result
