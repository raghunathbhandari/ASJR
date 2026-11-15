# ASJR Gann Ideas — TradingView Pine Script v6

**Status:** v0.1 research build • created 2026-11-15 (UK) • **not yet compiled inside TradingView Pine Editor**.

This is the standalone **ASJR Gann Ideas** overlay for **5m, 15m, 1H, 4H, and Daily** charts. It follows the user's reference screenshot: candlesticks, thin horizontal price lines, right-edge colour-coded method/angle/price labels, and two dashed vertical cycle families. It is not the proprietary AmiBroker "ASHOK GANN SUPER STUDIO" implementation.

## V5 — Clean UI, future-right price labels (2026-11-15)

**Latest release:** `ASJR_Gann_Ideas_V5_Clean_UI.pine`, TradingView name **ASJR Gann Ideas V5 Clean UI**.

This fixes the screenshot concern where labelled price levels occupied the same horizontal area as forming candles. V5 adds a user-adjustable **right-side label rail** in `04 — Appearance`:

| Setting | V5 default | What it does |
|---|---:|---|
| `Price labels to the right (bars)` | **35** | Positions all horizontal-level price labels to the right of the latest candle, in blank future chart space |
| `Nearby price-label extra spacing (bars)` | **10** | Staggers labels horizontally when levels are close together |
| `Group nearby levels within ATR x` | **0.25** | Sets the price-distance threshold for staggering nearby labels |
| `Gann price label font size` | **Normal** | Keeps V4's larger text |
| `Price-label background transparency` | **82** | Keeps V4's independent label background opacity |

Horizontal price lines now run to the farther-right label anchor, then extend left across the chart. Labels remain **above** the exact level. The 10 method-specific colour pickers preserve **native colour-picker opacity** on lines; label font/colour and price calculations have not changed.

**TradingView chart spacing:** Pine can draw labels into future bars but cannot guarantee your viewport displays all that blank space. If labels appear outside the right-hand edge, increase the chart's **right margin** (or move the visible price action left), or reduce `Price labels to the right (bars)`. Drawing x-coordinates remain capped to **480 future bars** (below TradingView's 500-bar limit).

**V4 and prior versions remain available**; upgrading requires copying V5 code into a **new Pine script** and adding that script to the chart. Not yet compiled inside the TradingView Pine Editor.

## V4 — price-label placement and font size (2026-11-15)

**Prior release:** `ASJR_Gann_Ideas_V4_Labels.pine` (new TradingView title: **ASJR Gann Ideas V4 Labels**).

The screenshot feedback for V3 was that horizontal price lines crossed the text inside right-side labels. V4 fixes this **without shifting the mathematical price levels**:

- Every horizontal line **ends at its right-side label's anchor** and extends to the **left** only, so it cannot run beneath the label text.
- Price labels use `label.style_label_up`: the label **floats above the price level**, with a pointer anchored exactly on the price line.
- New **Settings → Inputs → 04 — Appearance → Gann price label font size** dropdown: `Tiny / Small / Normal / Large`, default **Normal** (previously Tiny).
- Retains all **10 method colour pickers and native picker-opacity behaviour** from V3.
- **Label background opacity** is **unchanged**, continuing to use `Price-label background transparency`. Label text is kept fully opaque for readability.
- Existing vertical-cycle label font/size/background and all price/time calculations remain unchanged.

**Important:** Original V1, V2 and V3 files remain in the folder. Select V4 specifically in Pine Editor. GitHub source presence does not mean TradingView auto-updates an indicator already loaded.

## Files
- `ASJR_Gann_Ideas.pine` — indicator source.
- `GANN_STUDY_NOTES.md` — mathematical research, image-slide examples, historical context and limitations.
- `tests/test_reference_math.py` — standard-library unit tests for independent numerical examples (not Pine runtime tests).

## Exactly 10 independent checkbox options

| # | Checkbox | v0.1 calculation | Validation status |
|---|---|---|---|
| 1 | Gann Factor of 8 | Previous *completed source timeframe* range (highest high to lowest low in N bars), steps of 1/8, plus separately labelled 2/3 line | Defined locally; screenshot exact range settings unknown |
| 2 | Gann Yearly Highs & Lows | **Previous completed 12-month exchange period** high and low | Defined; not current running-year levels |
| 3 | Gann Power of Squares | Nearby positive integer squares n² | Mathematical interpretation; exact vendor method unknown |
| 4 | Gann Power of Cubes | Nearby positive integer cubes n³ | Mathematical interpretation; exact vendor method unknown |
| 5 | Gann Square of 9 (Static) | Fixed manual price anchor; sqrt-angle offsets ±45° through ±360° | Reproducible math; scaling convention stated |
| 6 | Gann Square of 9 (Dynamic H) | **WORKING** interpretation: same angle formula from latest **confirmed pivot high** of selected source TF | Proprietary H meaning not verified |
| 7 | Gann Square of 9 (Dynamic C) | **WORKING** interpretation: same angle formula from **previous confirmed close** of selected source TF | Proprietary C meaning not verified |
| 8 | Gann Square of 360 | **WORKING linear 360° price circle**: anchor + angle / 360 × user-specified full-turn price span | Not a verified historical/vendor formula |
| 9 | Vertical cycle **12** | One unit dropdown `bars / mi / hh / day / m / y`; repeated cycle every 12 selected units | Final user-defined requirement |
| 10 | Vertical cycle **90** | Independent unit dropdown; repeated cycle every 90 selected units | Final user-defined requirement |

**12 and 90 are lengths, not years unless `y` is selected.** No permanent 90-year cycle is imposed. Examples: `12 bars` or `12 mi`, `90 hh`, `90 day`, etc. Both use a shared editable UTC anchor.

### Unit meanings
- `bars` = **chart candles**, counted from first loaded candle at/after anchor timestamp (not projected wall-clock bars).
- `mi` = elapsed minutes (60,000 ms each).
- `hh` = elapsed hours (3,600,000 ms each).
- `day` = elapsed 24-hour days. These are **not** exchange-session days.
- `m` = **calendar months**, advancing same UTC day-of-month, clamped to month end for e.g. January 31 → February 28/29.
- `y` = **calendar years**, same UTC anniversary, clamped for February 29.

On session-gapped assets, a cycle boundary that falls during market closure is drawn at **the first existing candle on or after that boundary**. Multiple boundaries in one gap are collapsed to one drawn marker. On a Daily chart, 12-minute intervals are below chart resolution; the script cannot show every minute-line correctly on Daily OHLC history.

Historical vertical markers are limited to latest 48/cycle by default, plus the next projected future marker. Bar-projected future x-coordinates use TradingView bar indices; actual calendar/elapsed-time projections use Unix timestamps. **Future bar-count positions are projections, not assured timestamps.**

## Multi-timeframe anchor architecture
- Select **Gann price source timeframe**: `5`, `15`, `60`, `240`, or `D`.
- **Source timeframe must be >= chart timeframe**. Choosing an unavailable lower source TF throws a clear runtime error instead of silently returning a mismatched sampling.
- The default source is **Daily** to ensure the same confirmed Gann reference across 5m, 15m, 1H, 4H, and Daily.
- The latest confirmed swing high/low is a pivot with user-set left/right bars; it is known only after the right-hand confirmation candles. It uses prior **completed source bar** values.
- Previous completed source close and prior N-bar High/Low are similarly offset one source bar with `lookahead_on`, an established non-lookahead HTF pattern.
- The static Square of 9 anchor is **a separate manual number**, so it never moves when the source timeframe or chart timeframe changes.
- **Dynamic H** changes only when a new source-timeframe pivot high is confirmed. **Dynamic C** updates after each source candle completes.

## Horizontal line rendering
- Each enabled family draws independently on the **price scale**, with a different colour and a label:
  `F8 62.5% 165.00`, `S9 STATIC +90° 552.25`, `S360* -45° 517.75`, etc.
- Values are rounded to `syminfo.mintick` for actual chart price placement.
- The **Draw levels within ±% of last price** input (20% default) filters far-away levels to prevent clutter; increase it to reveal more.
- Duplicate-price labels are shifted horizontally instead of being falsely assigned another y-coordinate.
- Lines are redrawn on the last bar; historical time markers are stored in capped arrays.
- Eight toggles do not guarantee eight **visible** lines: a family may have zero levels near market price, missing historical data, or an unavailable confirmed pivot.


### Line and label colours (2026-11-15 update)
Open **ASJR Gann Ideas → Settings → Inputs → 05 — Method line / label colours**.

There are **10 independent colour pickers**, one for each of the eight horizontal price families and one for each vertical cycle (12, 90). Each colour applies to all horizontal lines of its family **and its matching right-edge numerical labels**, or to the corresponding dashed vertical lines and their cycle labels.

The **04 — Appearance** section now also offers:
- **Horizontal line transparency (0=solid)**, default 22. Reduce towards 0 to make the coloured price lines more visible.
- **Price-label background transparency**, default 82. Reduce towards 0 for a more filled label background.

These are visual settings only. They **do not change the Gann price calculations, anchors, 12/90 cycle lengths, dropdown units or 10 feature checkboxes**.

## Install and validate in TradingView
1. Open TradingView chart of **MES, MNQ, INTC, COHR**, or another symbol.
2. Open **Pine Editor**; paste the entire `ASJR_Gann_Ideas.pine` text; click **Save** and **Add to chart**.
3. Check Pine Editor output. If any compilation error appears, capture **exact line and text**; this file has **not** been TradingView-compiled in the connected environment.
4. Select **Daily** price anchor source and test chart switching **5m → 15m → 1H → 4H → Daily**. Check stable S9 Static and confirmed Daily pivots.
5. Test only one checkbox at a time before switching several on.
6. Set `Cycle 12` to `bars` on 5m (interval 12 × 5m = 60m trading bars), then `mi` (12 real minutes) to see the difference at session boundaries.
7. Set `Cycle 90` to `hh`, `m` and `y` separately; check next projected marker versus anchor UTC.
8. Test weekend/holiday gaps, leap year Jan 31/Feb 29 edge cases, new symbols and first bars without pivot history.
9. Check overlap labels and TradingView object budget on 5m MES. For a very dense chart, reduce vertical history or visible level window.

## Known limitations / follow-up research
- Exact proprietary **Dynamic H, Dynamic C, Factor of 8, Power of Squares/Cubes, Square of 360** implementation details **cannot be recovered from menu screenshots alone**. Current versions are explicit mathematical **working alternatives**.
- No claim of 60% win rate, predictive power, high-probability reversal, or proven S/R level has been established.
- This is an overlay **indicator**, not a strategy or order-execution bot.
- It has not been smoke-tested by a live Pine compiler or against exchange-level market data in this release. The Python reference tests check mathematics only.
- Labels may be crowded when all eight families are checked, and rendered lines are limited by TradingView object constraints.
- The two vertical settings have one shared time anchor, changeable in Settings. For a future release, separate anchors can be added without adding checkboxes.

## TradingView Pine v6 technical references
- [Pine script inputs](https://www.tradingview.com/pine-script-docs/concepts/inputs/)
- [Higher timeframe data and repainting](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/)
- [Lines and boxes](https://www.tradingview.com/pine-script-docs/visuals/lines-and-boxes/)
- [Future x positions and limitations](https://www.tradingview.com/pine-script-docs/faq/techniques/)
- [Time / calendars](https://www.tradingview.com/pine-script-docs/concepts/time/)

**Commit safety:** The new folder is separate from existing `Gann/`, `three_candle/`, DataLake and production bot code. Do not force-push or reset live working trees.
