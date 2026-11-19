# ASJR Renko V4 — Scroll-Aware Contiguous Bricks

**Current:** [ASJR Renko V4 Pine Script](ASJR_Renko_V4.pine) · [V3](ASJR_Renko_V3.pine) · [V2](ASJR_Renko_V2.pine) · [V1](ASJR_Renko_V1.pine) · [ASJR Home](../README.md)

**V4 fixes the historical scrolling issue:** V3 drew bricks in synthetic slots anchored to the **latest chart candle**, so scrolling backward left the bricks behind. V4 uses TradingView's `chart.left_visible_bar_time` / `chart.right_visible_bar_time` values, which **recalculate when scrolling or zooming**. It reconstructs bricks only from source candles at or before the currently visible **right edge** and packs bricks inside the displayed chart window. Using **time-based drawing coordinates** avoids Pine's limit on drawing more than 9999 bars away from the current bar.

## How to use

1. Copy [ASJR_Renko_V4.pine](ASJR_Renko_V4.pine) into TradingView Pine Editor; remove earlier Renko versions from the chart.
2. Keep the underlying chart type **Candles**, then choose any timeframe such as **1m / 5m / 15m / 1H / 4H / 1D**.
3. To see only blocks, hide the original price series with TradingView's **eye control**. V4 tries to make ordinary candles transparent by default.
4. Default sizing: **ATR snapshot 14 × 0.50**, drawing last **100 bricks**, width **2 visible chart bars** per brick. Fixed-size brick mode is more stable for historical comparisons.
5. Scroll back to an earlier date: the Renko block sequence should **rebuild using prices available by the visible right edge**, not continue showing today's most recent bricks. Zooming in/out changes how many blocks can fit in the visible width.
6. No EMA lines, buy/sell icons or alerts — this is a **brick-only chart**.

## What the blocks mean

- **Continuation:** one completed brick-size move in the same direction.
- **Reversal:** a two-brick-size threshold before drawing the next opposite-direction block.
- **Equal-height rectangles:** each displayed brick has the selected price height, boxes touch horizontally.
- **Synthetic x-axis:** the horizontal positions are packed into available visible chart bars for readability; they **are not exact trading timestamps**. Scrolling or zooming therefore rebuilds the displayed sequence, **not** a timestamp-aligned historical plot.
- **Price source:** confirmed chart closes, **not tick-by-tick data**. Intrabar swings cannot be inferred.
- **ATR snapshot mode:** sizes are calculated from ATR at the visible right edge, then applied as a single constant brick size to all replayed candles. This means moving the right edge can change older brick patterns. Use **Fixed** to compare periods with the same brick size.
- **Replay history:** up to last 1800 *closed source candles* before the visible right edge, subject to TradingView's loaded chart history. Changing the start of that replay can affect the Renko anchor and thus the brick sequence.
- **Performance:** Pine needs to reconstruct the brick sequence each time the visible range changes, which may slow extensive scrolling/zooming on low timeframes.
- **Drawing cap:** up to 400 contiguous brick boxes, constrained further by the number of chart bars visible and chosen brick width.

**Limitations:** This is a synthetic close-based price-brick display, not TradingView native/tick Renko. Underlying date axis remains a normal time axis even though bricks are packed left-to-right for visual readability. Do not use the synthetic x position or historical brick touch as a trade fill. Actual market candles and prices are required for entries and stop-loss placement.

**Validation status:** Source and GitHub links are verified; TradingView Pine Editor compilation and the user's scroll test are **not yet independently verified**.

## ASJR repository rule

For every new TradingView indicator: **dedicated folder + versioned Pine Script + folder README + main README link**.

*Educational / research use only.*
