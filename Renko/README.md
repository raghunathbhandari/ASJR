# ASJR Renko V3 — Contiguous, Brick-Only Chart

**Current:** [ASJR Renko V3 Pine Script](ASJR_Renko_V3.pine) · [V2](ASJR_Renko_V2.pine) · [V1](ASJR_Renko_V1.pine) · [ASJR Home](../README.md)

V3 fixes the 19 November 2026 AMD daily screenshots: V1 showed mostly EMA steps; V2 displayed intermittent price bodies with time gaps. **V3 draws actual contiguous, full rectangular green/red bricks**, not time-spaced indicator candles. No EMA lines, BUY/SELL icons, or strategy alerts are included in this brick-only version.

## Usage

1. Open [ASJR_Renko_V3.pine](ASJR_Renko_V3.pine), copy the entire source to **TradingView Pine Editor** and add it to a **standard time-based** chart.
2. Choose **1m, 5m, 15m, 1H, 4H or 1D** (works with other chart timeframes too).
3. To view **only** Renko, hide the underlying symbol's candles using the symbol **eye** control. V3 also defaults to making original chart bars transparent.
4. V3 draws up to **100 of the latest bricks**. Set **Horizontal brick width (chart bars)** to **2** initially, increase to **3** for wider blocks, or reduce to **1** to fit more across the screen.
5. Default sizing is **ATR snapshot 14 × 0.50**. For a genuinely constant user-chosen brick amount, use **Fixed** (e.g. USD 2 on AMD, as a visibility experiment, **not** a trading parameter). If you see too few bricks, reduce the size.
6. Use **Last bricks to show** to change drawing history (max 400). There are no MA lines, crossover signals, or BUY/SELL triangles to distract from brick construction.

## How it works

V3 stores the last 1,800 **confirmed chart candle closes**, then at the chart's right edge reconstructs price moves using a **single constant brick size for the entire rendering**. It applies an ordinary **two-brick reversal threshold**, with an opposite brick printed one increment away from the prior Renko close and continuing a second increment in the reversal direction. Each completed brick is a full rectangular box and boxes are placed **directly next to each other on a synthetic horizontal sequence**. No blank time-bar columns are inserted.

The horizontal brick positions are **not real timestamps**. The chart's underlying x-axis remains a time axis; V3 uses consecutive time-bar slots purely to give the bricks a uniform visual width. Unlike real Renko chart engines, an overlay cannot replace TradingView's x-axis with a brick-index axis. You may need to zoom to display the number of bricks you prefer.

**Sizing caveat:** ATR snapshot and Percent snapshot modes take the **latest confirmed** ATR or reference price and **replay the whole retained history with that one brick size**. Consequently, past brick shapes can change as new candles arrive and the snapshot size changes. **Fixed** mode avoids that moving brick-size effect (though loaded-history length still affects the initial anchor).

## Limitations

- This is a **close-based reconstruction**, NOT native Renko and NOT tick-based. Price crossings missed inside a 1m/15m/1D candle cannot be recovered from completed closes alone.
- A price movement large enough to create several bricks creates several adjacent rectangles; their visual horizontal positions are synthetic, not their actual formation timestamps.
- The first retained candle anchors the reconstruction. Older chart history, different timeframes or a different source-candle history length can change the start and therefore the reconstructed bricks.
- Drawing uses TradingView boxes (up to 400 visible), re-created on the last chart bar; do not interpret the brick positions as bar-by-bar trade fills, use the chart's actual prices for execution and risk.
- Processing is based on chart closes, so a live partial candle **does not** create an unfinished brick.
- V3 intentionally has **no EMA, signal markers, BUY/SELL icons or alerts**. Keep your other ASJR indicators independent if you need them.

**Validation:** The V3 source and repository links are committed; independent TradingView Pine Editor compilation and AMD chart rendering are **not yet verified**. Confirm visual geometry in TradingView before relying on any part of the visual analysis.

## Repository rule

For every future ASJR TradingView indicator: **dedicated folder + versioned .pine file + folder README + main README link**.

*Educational/research-only tool; not trading advice.*
