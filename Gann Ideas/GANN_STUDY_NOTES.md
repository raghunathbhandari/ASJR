# ASJR Gann Ideas — Gann Learning & Research Notes
**Prepared:** 2026-11-15 (UK)  |  **Status:** Working research notes from this conversation, slide photographs and mathematical examples.  
**Source distinction:** "Slide says" means text visible in the user's seminar slides. "ASJR interpretation" means our implementation design; **neither is automatically authenticated as an original W. D. Gann formula.**

## 1. Aim
A multi-timeframe TradingView overlay (`5m / 15m / 1H / 4H / Daily`) for MES, MNQ, liquid stocks and indexes that combines:
1. **Eight independent price-level families** shown in a Gann Super Studio menu photographed by the user.
2. **Two independent vertical time-cycle switches** fixed to **12** and **90**, each with a unit dropdown `bars / mi / hh / day / m / y`.
3. Right-edge labels formatted **method, angle or percent, numerical price**, matching the provided dark-chart example.
4. Time + price **confluence** as a research condition, not an automatic trade entry.

The 12/90 lengths are **not years** except when unit `y` is explicitly selected. Earlier ideas of an automatic 12-year and 90-year checkbox were rejected as unsuitable for intraday charts.

## 2. Seminar menu: the eight tool names (transcribed)
1. GANN FACTOR OF 8
2. GANN YEARLY HIGHS & LOWS
3. GANN POWER OF SQUARES
4. GANN POWER OF CUBES
5. GANN SQUARE OF 9 (STATIC)
6. GANN SQUARE OF 9 (DYNAMIC H)
7. GANN SQUARE OF 9 (DYNAMIC C)
8. GANN SQUARE OF 360

These names were visible in the AmiBroker demonstration. **Names alone cannot disclose exact proprietary formulas or settings.** Especially *H*, *C*, Power of Cubes and Square of 360 require original documentation or code to certify a match.

## 3. Gann Square of Nine geometry and price arithmetic
- A spiral of positive integers around central **1**; completed odd-number squares at 9=3², 25=5², 49=7², 81=9², etc.
- The **cardinal** cross uses conventional angular labels 0°, 90°, 180°, 270°.
- The **ordinal/diagonal** cross uses 45°, 135°, 225°, 315°.
- In the studied square-root price convention, one 360° turn corresponds to a **change of 2 in the price square root**.
- A common price projection is:

  `Upper(P,θ) = (sqrt(P) + θ/180)^2`  
  `Lower(P,θ) = (sqrt(P) - θ/180)^2` (valid for positive inner root).

- Corresponding root increments: 45°=0.25, 90°=0.5, 135°=0.75, 180°=1.0, 270°=1.5, 360°=2.0.
- Gann diagrams may label an *absolute spatial direction* (e.g. 225° diagonal). This is different from a *relative rotation* of 360° from square root 13 to 15; do not conflate them.

### 3a. Slide example: 169 to 225
The photographed "Navigating on the Square of 9" slide uses 169 and 225 with sqrt=13 and sqrt=15 and +0.25 root increments.

| Root | Exact square | Slide's displayed ~ whole-number label |
|---:|---:|---:|
| 13.00 | 169.0000 | 169 |
| 13.25 | 175.5625 | 176 |
| 13.50 | 182.2500 | 183 |
| 13.75 | 189.0625 | 190 |
| 14.00 | 196.0000 | 196 |
| 14.25 | 203.0625 | 204 |
| 14.50 | 210.2500 | 211 |
| 14.75 | 217.5625 | 218 |
| 15.00 | 225.0000 | 225 |

**Correction:** 182.25→183, 189.0625→190, etc. are **ceiling-style** labels, not ordinary nearest-integer rounding. Our indicator **keeps exact mathematical calculations then rounds to the traded symbol's tick size**.

### 3b. Earlier 529 anchor test
sqrt(529)=23. Upper 45°=540.5625, 90°=552.25, 135°=564.0625, 180°=576, 360°=625.00. Lower 45°=517.5625, 90°=506.25, 135°=495.0625, 180°=484, 360°=441.

The difference between levels widens as prices become larger; a "90-degree" move is not a constant percentage or constant number of dollars.

## 4. Gann Factor of 8 from seminar
The sample displayed screenshot levels:
- 50% = 132
- 62.5% = 165
- "66%" = 176
- 75% = 198

Those numbers correspond arithmetically to a 0–264 reference range: 132/264=0.5; 165/264=0.625; 176/264=2/3; 198/264=0.75. **This inference does not prove that the actual indicator anchored its range at 0**, only that the displayed four values fit this scale.

Eight equal divisions yield levels every 12.5% (0,12.5,...,100). The *2/3 = 66.666...%* level is **not one of those eighths**. Our v0.1 implementation draws the 2/3 line separately, tagged `66.67%*`.

## 5. Static vs dynamic Square of Nine
- **Static**: user-entered fixed anchor, e.g. 529. Gann square-root levels remain unchanged when switching chart timeframes.
- **Dynamic H (ASJR working interpretation)**: anchor = **last confirmed pivot HIGH** of chosen source timeframe, prior completed bar. A new confirmed high pivot updates levels.
- **Dynamic C (ASJR working interpretation)**: anchor = **previous confirmed CLOSE** of chosen source timeframe, updating after each completed bar.
- These H/C expansions are **design choices, not verified screenshots/source claims**. We must not call them reproductions of the teacher's proprietary code.

## 6. Power of Squares, Power of Cubes and Square of 360
- **Power of Squares v0.1**: pure positive integer-square reference prices n² around current market price.
- **Power of Cubes v0.1**: pure integer-cube reference prices n³ around current market price.
- **Square of 360 v0.1**: a *parameterized linear angle-to-price circle*, `Price = Anchor + FullTurnPriceSpan × (Angle/360)`, angle steps ±45° to ±360°. This is an explicit research placeholder; a genuinely documented square-of-360 algorithm may be materially different.
- These are **not statistical price support/resistance proofs**.

## 7. Eight seasonal Gann dates from seminar slide
| Date printed in slide | Seminar category |
|---|---|
| February 4 | Minor, winter–spring midpoint |
| **March 21** | **Major**, spring equinox window |
| May 6 | Minor, spring–summer midpoint |
| **June 22** | **Major**, summer solstice window |
| August 8 | Minor, summer–autumn midpoint |
| **September 23** | **Major**, autumn equinox window |
| November 7 | Minor, autumn–winter midpoint |
| **December 22** | **Major**, winter solstice window |

These are traditional **date reference windows**, **not exact astronomical instants every year**. Proposed research: compare market turning-point frequency in ±3 trading sessions to matched non-event dates. They are study notes, **not an eleventh checkbox**.

## 8. Long historical cycle slides: research, NOT fixed indicator switches
- Seminar 90-year slide: **1839 → 1929 → 2019**.
- Seminar 12-year slide: **2007 → 2019**.
- Verify events carefully: "**1839 world's first recession**" is historically inaccurate. The American Great Depression started in 1929. 2019 experienced global economic slowdown, while the COVID-related global recession is generally dated 2020. The Nifty's major pre-crisis high was January 2008, not 2007.
- The slides supply **hypotheses**. A few matched dates do not establish forecasting skill.
- Per final instruction the indicator has **12 and 90 selectable units**, meaning 12 minutes, 12 bars, 90 hours etc. when selected; *nothing* automatically draws a 90-year cycle.

## 9. Time-cycle calculation details
There are exactly **2 cycle switches**, with fixed lengths **12** and **90** and separate unit dropdowns.

| Unit | Defined meaning |
|---|---|
| `bars` | chart bar count since first available bar at/after selected anchor |
| `mi` | integer minute count from absolute UTC anchor |
| `hh` | integer hour count from absolute UTC anchor |
| `day` | elapsed 24-hour day count |
| `m` | UTC calendar month anniversary |
| `y` | UTC calendar year anniversary |

Calendar handling clamps nonexistent dates to month end; e.g. 2024-01-31 + 1m = 2024-02-29; 2024-02-29 + 1y = 2025-02-28. Note that independent offsets are computed relative to the **original** date, not by repeatedly adding a shortened date (avoids end-of-month drift).

**Bars ≠ minutes:** 12 bars on 5m is 60 elapsed *trading-bar* minutes with session gaps; 12 mi is 12 wall-clock minutes. For a Daily chart, selecting 12 mi is allowed but under-resolved and coalesced; for 5m use mi/hh/bars; for 1H,4H,Daily consider day/m/y as appropriate.

### Missing bars and market holidays
For a timestamp due between sessions, we project to the first observed opening candle after that boundary for historical line placement. If a gap crosses multiple cycle boundaries, only one line is drawn, and its meaning is "boundary crossed before this candle". A next *future* time line can be plotted at an exact UTC timestamp even if the market will be closed.

## 10. Source timeframe, repainting and stability
- The selected source must be >= the chart timeframe.
- `request.security(..., expression[1], lookahead=barmerge.lookahead_on)` supplies prior **confirmed** HTF calculations. For a 5m chart reading Daily source, daily levels do not use today's unfinished daily candle.
- A confirmed pivot requires `pivotLen` candles on **both** sides before it is known. No claim is made that a pivot could be known at its historical high/low time.
- A source timeframe changed by the user can legitimately change dynamic levels. Fixed `S9 Static` manual-anchor levels do not.

## 11. Proposed Rudra Gann Analyst test protocol
1. Make an inventory for MESZ2026/MNZ or relevant continuous MES/MNQ and liquid stocks: OHLCV with true UK timestamps (store original exchange timezone), session labels, and corporate action adjustments for stocks.
2. For each method, record every real-time-observable **touch** within 1–2 minimum ticks of a level. Do **not** look ahead to choose the anchor.
3. Score next 3/6/12/24 candles' MFE/MAE, continuation vs reversal, 1R/2R reach, reaction size, and maximum drawdown.
4. Compare against random **non-Gann placebo levels** at equal price density and account for spread, commissions, latency and slippage.
5. Test price/time confluence (both vertical-cycle switches independently), across 5m/15m/1H/4H/Daily. Keep train/test periods separated.
6. Avoid claiming an edge until statistically credible **out-of-sample** results are recorded.
7. Keep screenshots of strong *and failed* examples, not only selected winners.

## 12. Scope and provenance
The user's screenshots are seminar slides and AmiBroker demos, not original Gann book pages or original source code. Historical quotations and exact vendor algorithms would require verified primary-source reading. Existing book-translation files in `Gann/` are a **separate** project and are not modified here. The v0.1 implementation is intended as an honest, inspectable ASJR research base.
