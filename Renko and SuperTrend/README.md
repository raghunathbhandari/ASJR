# ASJR Renko and SuperTrend V4 — Current Test Release

**Current Pine Script v6:** [V4 — continuous SuperTrend](ASJR_Renko_and_SuperTrend_V4.pine) | [V3](ASJR_Renko_and_SuperTrend_V3.pine) | [V2](ASJR_Renko_and_SuperTrend_V2.pine) | [V1](ASJR_Renko_and_SuperTrend_v1.pine) | [ASJR home](../README.md)

## Release and TradingView version rule

- Every **new release** gets a new numbered `.pine` file, a matching `indicator()` title and short title, and a matching version in the chart status panel.
- Earlier versioned files remain untouched, so builds can be compared or rolled back.
- **V4** draws the SuperTrend as a **continuous connected line by default**, including across bullish/bearish flips. Set *Continuous SuperTrend line* to off to intentionally break at a reversal. The visual connection across a flip may make a steep diagonal; the line is a display, not a trade fill.
- **V3** connected adjacent SuperTrend levels but defaulted to a reversal gap. This could still look broken.
- **V2** preserved the V4-style contiguous brick display but drew SuperTrend as separate horizontal dashes; **V1** is also preserved.
- Pasting a new version into the Pine Editor and adding it to the chart is necessary: changing a GitHub filename does **not** automatically refresh an indicator already saved on TradingView. Remove the old chart indicator to avoid mixed output.
- Source-level checks are not equivalent to Pine Editor compilation; validate in TradingView before relying on displayed chart results.

## What it displays

- Green and red Renko bricks, calculated from **confirmed ordinary chart closes**.
- A conventional SuperTrend on **synthetic completed Renko brick prices**. Wilder ATR is updated once for each new brick. **V4 connects all valid SuperTrend levels between adjacent brick centres by default**, including reversals.
- **V4-style contiguous blocks:** completed Renko bricks are packed into adjacent synthetic horizontal slots at the visible chart's right edge. The horizontal placement is for display **and is not the original brick formation timestamp**.
- Scrolling/zooming rebuilds the brick and SuperTrend display using up to 1800 confirmed source candles ending at the visible right edge. Earlier loaded candles beyond that replay limit are not used.
- Optional hidden ordinary bars, trend flip labels, status panel and colours.

## Settings

**Renko brick engine:** **Source = Close** by default (editable). Default **Box size assignment method = Traditional** and **Box size = 8.33** fixed instrument-price units (8.33 Nifty index points becomes **8.35** when the symbol's minimum tick is 0.05; this is not a percentage or ATR divisor). Other optional methods are ATR (ATR length 14 × multiplier 0.50) and Percentage (0.50% by default). The 8.33 value is a user-selected fixed box size.

**SuperTrend:** enabled by default with **ATR Length = 14 synthetic bricks** and **Base Factor = 3**. **Continuous SuperTrend line = ON** by default and **line width = 2**. Optional Choppy Filter (ADX) defaults OFF, threshold 15; its ordinary-candle ADX filters optional flip labels only, not the SuperTrend line. Wilder ATR seeds from the first 14 synthetic-brick true ranges.

**Display:** up to 400 completed bricks by default, width 2 visible chart bars per synthetic brick, 0 opacity, no flip labels by default. **Compact status panel OFF** by default for a cleaner chart. Ordinary price candles are made transparent by default; hide the chart's symbol with its eye icon if they remain visible. Both brick boxes and SuperTrend segments use the **same synthetic slots**.

## Accuracy & limitations

1. **Price source:** historical closes, not tick data or wick-path sequencing. Sharp intrabar highs/lows can be missing, and confirmation waits for the source candle close.
2. **Renko mechanics:** continuation uses one brick-size threshold; a reversal uses two brick sizes and skips one box at the turning point. Prices rounded to the instrument tick.
3. **Sizing:** Traditional (fixed 8.33 default) uses a constant price-unit box size. ATR and percentage options use a **single snapshot at the visible right edge** throughout the replay, which is not TradingView's native ATR Renko history. Changing the replay window's first candle can change the initial anchor and downstream bricks.
4. **SuperTrend:** conventional trailing upper/lower bands calculated from generated brick OHLC. In V4, connected diagonal/flat segments align with **synthetically packed boxes**, not historical formation timestamps. Continuous joining across a trend change is a visual choice; the actual SuperTrend level can jump on reversal. ADX optionally gates flip labels; no automatic trade entries are included.
5. **400-box cap:** boxes refer to **completed synthetic bricks**, not 400 source candles. If a giant single-candle move exceeds the per-bar limit, the status panel shows a capped candle count.
6. **TradingView visible-window behaviour:** after replaying confirmed source closes through the visible right edge, the latest bricks are drawn as a **continuous staircase** fitted to the visible bar count. Scrolling rebuilds the display but the brick's synthetic X position **must never be interpreted as its real formation time**.
7. **Validation status:** V4 connector logic reviewed in source; Pine Editor compilation and live TradingView visuals **not yet confirmed**. The previous nine numerical unit tests cover brick maths/ATR and not the packed display. No real-time alerts or broker execution are provided in this display-first build. Do not use synthetic X positions for trade timing.

## Checks in TradingView

1. Run this indicator on a regular **AMD 15-minute candle chart**; keep the candles visible initially.
2. Start with **Source Close / Traditional 8.33**; for Nifty's 0.05 tick the effective brick size should display **8.35**. On AMD, 8.33 means **$8.33 per brick**, so relatively few bricks may form. For a denser AMD 15-minute comparison, temporarily try Traditional 2.00 (not the default).
3. Scroll back to Nov 17–20, 2026. The contiguous staircase should reconstruct within the visible window and the SuperTrend should appear **connected across consecutive valid levels**, with green/red changes at direction flips. A leading section before ATR(14) is ready may have no line.
4. Use SuperTrend defaults **ATR length 14, Base Factor 3**. The line must run along the packed bricks. Compare its price levels with ordinary-candle SuperTrend and native Renko, but not their synthetic X positions.
5. Confirm **8.33 is a fixed brick price distance**, not 8.33% or ATR / 8.33. Native Renko may still differ because its source/anchor construction and historical data can differ.


## Reference visual comparison

The reference screenshot used a **Nifty 50 Traditional box size 8.35** (8.33 rounded to a 0.05 tick). On AMD, 8.33 represents **$8.33 per brick**, a much larger percentage of its price than 8.35 Nifty points. Therefore brick counts and trends are not visually comparable between the two symbols without normalising box size. For a denser AMD test, consider Traditional 1.00 or 2.00; keep 8.33 as the requested default.

## Numerical reference checks

Run `python test_traditional_renko_v1.py`. The independent Python reference covers nine cases: tick rounding at 0.05 and 0.01, 1-brick continuation, exact 2-brick reversal, multiple bricks per source candle, ignored wicks, source-candle brick cap, Wilder ATR warm-up after 14 synthetic bricks, and reversal-gap true range. **All 9 corresponding local mathematical checks passed on 22 November 2026.** This does **not** prove Pine compilation, perfect TradingView native-Renko parity, or market accuracy.

[Open the numerical test code](test_traditional_renko_v1.py).

Older [ASJR Renko V1–V4](../Renko/) are preserved.

*Research only. Not investment advice or a broker execution model.*
