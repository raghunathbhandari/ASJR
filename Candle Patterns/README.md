# ASJR Candle Patterns — TradingView Pine v6

**Version:** v0.2 research build • **Created:** 2026-11-15 (UK)  
**Status:** GitHub source committed; **not yet compiled in the TradingView Pine Editor or backtested on live exchange data.**

A standalone **overlay indicator** that colours **only selected candlestick-pattern signal candles** on the user's real price chart. Use it alongside `ASJR Gann Ideas` for potential **Gann price-level + candle price-action** confluence. It does not place orders or promise reversals.

## Files
- `ASJR_Candle_Patterns.pine` — complete TradingView Pine Script v6 source.
- `tests/test_reference_patterns.py` — independent Python reference tests for the main OHLC definitions.

## Select patterns in Settings → Inputs

The first section has **16 independent on/off ticks** (checkboxes). An enabled pattern is eligible to highlight its **signal candle** when all enabled quality filters pass. Disable a tick to prevent that pattern from highlighting candles.

| # | Checkbox | Bullish condition | Bearish / neutral condition | Default |
|---|---|---|---|---|
| 1 | Bullish Engulfing | Current candle closes above its open and its entire high–low range engulfs previous candle high–low range (at least one boundary strictly exceeded) | — | ON |
| 2 | Bearish Engulfing | — | Current candle closes below its open and its entire high–low range engulfs previous candle high–low range (at least one boundary strictly exceeded) | ON |
| 3 | Hammer | Lower rejection wick ≥ wick multiplier × body, small upper wick; optional preceding decline | — | ON |
| 4 | Shooting Star | — | Upper rejection wick ≥ wick multiplier × body; optional preceding rise | ON |
| 5 | Morning Star | Bearish large candle → small middle candle → bullish recovery above first candle's body midpoint | — | ON |
| 6 | Evening Star | — | Bullish large candle → small middle candle → bearish recovery below first candle's body midpoint | ON |
| 7 | Bullish / Bearish Pin Bar | Large lower wick, close near top | Large upper wick, close near bottom | ON |
| 8 | Inside Bar Breakout | Previous candle inside the candle before; current **close > mother high** | Current close < mother low | ON |
| 9 | Outside Bar Reversal | Current range engulfs prior range, closes near high, prior candle bearish | Mirror, closes near low, prior bullish | ON |
| 10 | Tweezer Top / Bottom | Two nearby matching lows with opposing real-body directions | Two matching highs | OFF |
| 11 | Piercing Line / Dark Cloud | Bullish candle recovers above previous bearish body's midpoint | Bearish close into previous bullish body | OFF |
| 12 | Bullish / Bearish Harami | Smaller bullish real body entirely within previous bearish real body | Mirror | OFF |
| 13 | Doji | — | Neutral if real body ≤ user-selected % of total range | OFF |
| 14 | Marubozu | Bullish, ≥85% real body, both wicks ≤10% range | Mirror | OFF |
| 15 | Three White Soldiers / Black Crows | 3 progressively higher bullish closes | 3 progressively lower bearish closes | OFF |
| 16 | **Gann Level Sweep + Reclaim** | Wick trades ≥1 tick **below Gann level**, closes ≥1 tick **above** | Wick trades ≥1 tick above, closes ≥1 tick below; dual sweep is neutral | ON |

**Default: 10 selected groups (1–9 plus 16).** The #7/#10/#11/#12/#14/#15/#16 checkboxes each cover their named bullish and bearish variants. This keeps the Settings compact and editable.

### Appearance
- **Green:** bullish candle pattern (including a red real-body Hammer).
- **Magenta:** bearish candle pattern.
- **Amber:** Doji or a dual-sided Gann sweep/indecision.
- **Unchanged chart colour:** candle doesn't match an enabled pattern after filtering.
- Optional small directional markers and optional text labels with the primary pattern's name; **both are OFF by default** to avoid clutter.
- Under `confirmedOnly=true` (default), no candle is coloured until its own candle **closes**, including 3-candle patterns which signal at the close of Candle 3.

### Fixed priority for multiple matches on one candle
Only **one primary tag / colour** is produced per candle:
1. Gann sweep/reclaim (neutral when both directions trigger).
2. Engulfing.
3. Morning/Evening Star.
4. Hammer/Shooting Star.
5. Pin Bar.
6. Outside Bar Reversal.
7. Inside Bar Breakout.
8. Tweezer.
9. Piercing/Dark Cloud.
10. Harami.
11. Three Soldiers / Black Crows.
12. Marubozu.
13. Doji.

If a high-priority pattern is disabled, a lower-priority enabled pattern can still colour the candle.

## Gann confluence (important integration detail)
The existing `Gann Ideas/ASJR_Gann_Ideas.pine` draws **line.new() objects**, not exported numerical `plot()` outputs. Another Pine indicator **cannot automatically inspect those drawing lines**.

This script therefore provides an independent **Gann reference method** dropdown:
- **Disabled (default):** all standard candle patterns work on any symbol; **Gann sweep cannot signal** until a reference is selected.
- **Manual:** type one actual Gann support/resistance price. Entering 0 means **no Gann match**.
- **S9 Static:** uses the same **Square of 9 square-root angle convention** as ASJR Gann Ideas: `(sqrt(anchor) ± angle/180)^2` for 45° steps through ±360°. Set the **same fixed anchor** in both indicators.
- **External plot:** select the **numeric PLOT** of another indicator via `input.source` in TradingView's dropdown. **Do not leave the default source of close selected**—that would treat the candle's own close as a Gann level and yield misleading sweep hits. The current Gann Ideas source does **not** provide this plot yet.

`Require Gann touch for all standard patterns` is **OFF** by default, so normal patterns highlight even without a Gann reference. Turn it ON to filter every enabled pattern by a true interaction with the selected level(s).

A Gann touch counts when a candle's `[low,high]` intersects `[level - tolerance, level + tolerance]`. Tolerance = `max(2 ticks, ATR(14) × 0.10)` by default, adjustable in Settings. A sweep demands an **actual wick crossing of 1 tick** plus a close across the level; merely being near it is not enough.

**Research priority:** Run Gann Ideas for price levels and Candle Patterns for price action; compare raw vs Gann-filtered historical outcomes before calling the combination high probability.

## Pattern settings and definitions
- `Only highlight closed candles`: ON. Turning it off may produce **in-progress** signal changes before final candle close.
- `Require preceding trend`: ON for Hammer, Shooting Star and 3-candle Star groups only, with default lookback of 3 closed prior candles.
- **Engulfing V0.2:** current high ≥ prior high, current low ≤ prior low, and at least one edge is strictly exceeded; close > open = bullish, close < open = bearish. **Open/close body containment and previous candle direction are not required.** Doji candles are not labelled Engulfing.
- `Hammer/pin wick/body multiplier`: 2, adjustable.
- `Doji body/range`: 0.10 or less, adjustable.
- `Tweezer matching high/low`: within 3 minimum price ticks, adjustable.
- `Volume filter`: OFF; when enabled, volume ≥ SMA(volume,20) × multiplier. Symbols without volume data may show **no highlights**.
- Piercing/Dark Cloud and Morning/Evening Star definitions are intentionally **continuous-market tolerant**, with relaxed opening gaps appropriate to futures. They are not a literal reproduction of gap-dependent classical Japanese textbook rules.
- "Hammer" is a bullish *contextual* interpretation, not a guarantee; a large wick can occur without a reversal.
- Input timeframes: **5m, 15m, 1H, 4H, Daily**, with conditions calculated on whatever timeframe the TradingView chart currently uses. The script itself does **not** aggregate multiple simultaneous timeframes.

## How to install
1. Open `ASJR_Candle_Patterns.pine` in GitHub and select **Raw / Copy**.
2. In TradingView select **Pine Editor** → paste → **Save** → **Add to chart**. Use `ASJR Candle Patterns` as the title.
3. On MES 5m or 15m, start with only **Bullish Engulfing** and **Bearish Engulfing** ON to verify their colours.
4. Turn on Hammer, Shooting Star, Pin Bar, Inside and Outside Breakout one by one; review highlighted historical candles.
5. Turn on **Show primary pattern name** to audit why each highlighted candle was selected.
6. Add the independent **ASJR Gann Ideas** overlay. Set Candle Patterns `Gann reference method` to `Manual` with a displayed Gann level, or `S9 Static` with exactly the same anchor used in Gann Ideas.
7. Switch `Require Gann touch` ON, compare nearby highlighting, then independently test Sweep/Reclaim.
8. Try 1H, 4H, Daily and liquid stocks; adjust wick and tolerance thresholds. Review closed-bar signals to avoid misleading future information.
9. Use the built-in alertconditions for **Bullish**, **Bearish**, **Neutral**, **Any**, **Gann Sweep Bullish/Bearish**. They provide direction, ticker, timeframe and close; they do **not** include a dynamic primary pattern name (alertcondition message is static).
10. If Pine reports a compilation error, capture the **line number and exact message**. We did not have an authenticated TradingView Pine Editor/compiler in this environment; syntax has been source-reviewed but not TV-compiled.

## Current limitations and future validation
- No execution signals, broker connection, stop/target, profitability claims or statistical win-rate estimates.
- The Gann connection is **manual or S9 formula sharing**, not automatic introspection of all eight Gann line families.
- Large candle + multiple matching patterns uses the fixed priority above, rather than colouring individual constituent candles.
- Historical pattern scans use confirmed closes, but a Gann **source selected from another indicator** could itself repaint; choose a nonrepainting source.
- Reference Python tests are **unit checks of independent mathematics and candle fixtures**, not Pine compiler tests.
- Proposed next research: export selected numeric levels from Gann Ideas via `plot(display=display.none)` or a shared Pine library, then validate Gann confluence on MES/MNQ and stocks with out-of-sample studies.

## TradingView documentation
- [Bar coloring / barcolor](https://www.tradingview.com/pine-script-docs/visuals/bar-coloring/)
- [Input.source and external indicator plot selection](https://www.tradingview.com/pine-script-docs/concepts/inputs/)
- [Visual labels and markers](https://www.tradingview.com/pine-script-docs/visuals/text-and-shapes/)
- [Alerts](https://www.tradingview.com/pine-script-docs/concepts/alerts/)

## Repository safety
The script is in a new folder `Candle Patterns/` and does not modify `Gann/`, `Gann Ideas/`, `three_candle/`, production DataLake or other bots. Do not force-push or run `git reset --hard` on the VPS; use safe fast-forward sync.
