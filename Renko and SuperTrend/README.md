# ASJR Renko and SuperTrend v1

**Original Pine Script v6 research prototype:** [Source](ASJR_Renko_and_SuperTrend_v1.pine) | [ASJR home](../README.md)

## What it displays

- Green and red Renko bricks, calculated from **confirmed ordinary chart closes**.
- A conventional SuperTrend on **synthetic completed Renko brick prices**. Wilder ATR is updated once for each newly formed brick.
- Brick boxes aligned to their original candle timestamps. If several bricks form in one 15-minute candle, their price rectangles stack at the *same* 15-minute candle, not in invented earlier time slots.
- Scrolling/zooming rebuilds visible brick boxes; full loaded prior history still feeds the calculation.
- Optional hidden ordinary bars, trend flip labels, status panel and colours.

## Settings

**Renko brick engine:** ATR × multiplier (default ATR(14) × 0.5), Fixed size, % of price, **ATR / divisor** (default 8.33, **EXPERIMENT ONLY**). The public material examined did not establish Dr Devendra's exact 8.33 equation. This is not his script or a claim that division by 8.33 is his method.

**SuperTrend:** enabled by default, Renko brick ATR length 10 and multiplier 3.0.

**Display:** 400 visible box objects maximum by default, 0 opacity, no flip labels by default. Normal price candles visible by default for testing.

## Accuracy & limitations

1. **Price source:** historical closes, not tick data or wick-path sequencing. Sharp intrabar highs/lows can be missing, and confirmation waits for the source candle close.
2. **Renko mechanics:** continuation uses one brick-size threshold; a reversal uses two brick sizes and skips one box at the turning point. Prices rounded to the instrument tick.
3. **Sizing:** Fixed is best for invariant historical comparison. ATR/percentage sizing here is *adaptive each source bar*, not TradingView's exact ATR Renko feed. Changing loaded history can change the initial anchor and later bricks.
4. **SuperTrend:** standard trailing upper/lower band method, calculated on generated brick OHLC; it is **not** an independently verified proprietary AI SuperTrend algorithm.
5. **400-box cap:** boxes refer to **completed synthetic bricks**, not 400 source candles. If a giant single-candle move exceeds the per-bar limit, the status panel shows a capped candle count.
6. **TradingView visible-window behaviour:** price-aligned boxes are only created for visible candles. Scrolling causes a recalculation, and a single candle may contain several vertically stacked bricks; this is deliberately **not** the visually packed staircase of V3/V4.
7. **Validation status:** source prepared for Pine Editor testing; TradingView compilation, visual comparison and bar-by-bar numerical parity with native Renko are **not yet confirmed**. Do not automate executions with these synthetic prices.

## Checks in TradingView

1. Run this indicator on a regular **AMD 15-minute candle chart**; keep the candles visible initially.
2. Use **Fixed $2.00** to compare across dates, then ATR(14) × 0.5. Confirm every box is timestamp-aligned with the completed candle that caused it.
3. Scroll back to Nov 17–20, 2026. The boxes should move with the candles instead of staying near the live chart.
4. Compare the trend line to ordinary-candle SuperTrend and TradingView's native Renko. Different inputs and bar formation rules can produce different results.
5. Only after numerical verification compare experimental ATR / 8.33 sizing with a properly sourced example.

Older [ASJR Renko V1–V4](../Renko/) are preserved.

*Research only. Not investment advice or a broker execution model.*
