# ASJR Gann Ideas — TradingView Pine Script v6

**Status:** v0.1 research build • created 2026-11-15 (UK) • **not yet compiled inside TradingView Pine Editor**.

This is the standalone **ASJR Gann Ideas** overlay for **5m, 15m, 1H, 4H, and Daily** charts. It follows the user's reference screenshot: candlesticks, thin horizontal price lines, right-edge colour-coded method/angle/price labels, and two dashed vertical cycle families. It is not the proprietary AmiBroker "ASHOK GANN SUPER STUDIO" implementation.

## V16 — Square-of-9 levels cover the visible candle range (2026-11-23)

**New test release:** [ASJR Gann Ideas V16 Pine v6](ASJR_Gann_Ideas_V16.pine)

**AMD 15m bug in V6:** the old Square-of-9 level generator stopped after eight +/-45-degree rotations (up to +/-360 degrees) around the selected anchor. On a strong move from a higher swing anchor, the bottom level could sit far above current price: the indicator therefore looked broken on AMD although it still showed levels on COHR. This is a **range-generation limitation**, not a symbol-specific failure.

**V16 fix:** keep the same square-root Gann equation, but derive the relevant positive/negative angle indices directly from the **high and low of all currently visible candles**, with the existing 5% default padding and minimum +/-20% close-price coverage. This includes angles past +/-360 degrees where needed, regardless of ticker, price scale, or timeframe. As you scroll or zoom the indicator recalculates the horizontal coverage. Gann price source timeframe, static/dynamic price anchors, all ten feature switches and the V15 historical time-cycle logic remain available.

When the chart spans an extremely large price region, the finite `Square of 9 max levels per family` and `Maximum horizontal lines` budgets mean **not every single angle can be plotted**. Instead, V16 uses a larger integer-angle stride to distribute exact Gann grid levels across the *entire* candle range. It does not fabricate non-Gann levels. With a normal visible range the stride is one and all eligible angles are drawn. Yearly high/low references and other individual price families keep their original semantics; this V16 change specifically repairs the Square-of-9 families (Static, Dynamic H, Dynamic C).

**Chart check:** open AMD 15m with Dynamic H enabled, then pan back to include the older high and the subsequent lower candles. Gann S9 H lines should now appear around the low, middle and upper portions of those candles rather than stopping near the old anchor. Repeat on COHR, 5m, 1H, 4H and Daily; check scroll/zoom coverage and the line-count cap. **Pine Editor compilation and TradingView chart behaviour require user validation; only source-level invariants have been checked here.**

## V15 — Historical pivot cycles survive forward/backward scrolling (2026-11-22)

**Latest test release:** [ASJR Gann Ideas V15 Pine v6](ASJR_Gann_Ideas_V15.pine)

### Bug fixed
V14 selected the largest confirmed HIGH / smallest confirmed LOW **within the currently visible chart** and deleted/rebuilt the cycle lines each time the visible range changed. That moved point 0 and erased previous cycles when scrolling forward. V15 moves all cycle **anchor selection and historical line generation** into a history-driven, confirmed-bar pass that does not use the visible window. The chart may re-execute on scrolling, but the previously identified historical anchor phases and cycle positions are reconstructed deterministically from available OHLC history instead of resetting according to the viewport.

### Anchor modes and UTC start date

| Cycle starting point | How it works |
| --- | --- |
| **Pivot LOW** (default) | Track successively **lower confirmed pivot lows**, using the existing `pivotLen` confirmation (default 3 left/right candles); a new record low starts a new cycle *from its original candle*. Older completed cycle lines are **not deleted** merely because a stronger low is confirmed later |
| **Pivot HIGH** | Mirror rule: successively **higher confirmed pivot highs** |
| **Manual UTC** | **Fixed exact date/time** from the existing `Shared cycle anchor (UTC)` field; `bars` start at the first chart candle at/after that timestamp; clock/calendar units use the timestamp itself |

In **Pivot HIGH/LOW**, the `Shared cycle anchor (UTC)` field acts as the **earliest pivot search date**, initially **2026-01-01 00:00 UTC**. For example, set it to **2026-11-01** to examine the main COHR November swing without earlier 2026 lows/highs dominating your pivot selection. In **Manual UTC**, the same field defines bar 0 directly. The field's new tooltip explains the two behaviours.

**Important:** V15 does **not** permanently lock a single screen-selected pivot, because TradingView restarts Pine scripts when the chart's visible range changes, so `var` cannot remember a choice made in a previous scroll session. It uses a deterministic historical sequence of confirmed record pivots after the selected UTC start. If a new stronger pivot is confirmed later, the current cycle phase changes **without retroactively deleting older drawn cycles** (except the configured drawing budget). If the underlying chart loads *additional older data*, reconstruction can legitimately change. For an immutable individual starting point, use **Manual UTC**.

### Cycle lines and historical limits
- Cycle A/B default **12 / 90 bars**; each remains independently configurable from 1–500, with `bars / mi / hh / day / m / y` units. On completed candles after the active pivot, markers appear at successive multiples (e.g. +12, +24, +36…).
- The current pivot point is the original price-extreme candle but is only recognised after the right-side confirmation candles; no unconfirmed pivot is used.
- V15 does **not** delete/recreate all history lines inside `barstate.islast` or select a new extreme on every pan. Historical cycle lines are produced as the historical script replay reaches their bars. Future projections are aligned to the latest loaded bar and the last eligible confirmed pivot—not the viewport's right edge.
- **Finite TradingView drawing budget:** `Historical verticals per cycle` remains **48 by default (up to 100)**. Only the most recent 48 (or configured number) line drawings per cycle remain on the chart; the oldest are removed when that cap is exceeded. This is a platform/drawing limit, **not** a viewport reset. To inspect longer history, increase the setting to 100. Not all historic markers can exist simultaneously once the limit is exceeded; for unlimited, reproducible records export the cycle dates/indices to a data-based backtest outside the indicator.
- Up to three upcoming markers per enabled cycle are projected, within TradingView's 500-future-bar index limit. Previous versions including V14 remain intact.
- Eight Gann price families, independent Cycle A/B lengths and units, ten main switches, existing Gann level calculations, monk-colour defaults at 25% opacity and optional label styling are unchanged.

### Testing
On a COHR 4H chart, choose Pivot LOW, `Shared cycle anchor (UTC) = 2026-11-01 00:00`, Cycle A = 12 bars, Cycle B disabled. Observe confirmed pivot low and vertical lines at +12, +24, +36… . Pan backwards and then forwards: the cycle positions for the same loaded history should be unchanged. For a guaranteed fixed pivot chosen manually, switch to Manual UTC and specify the actual swing date/time. If historical lines eventually stop farther back, inspect the **Historical verticals per cycle** cap.

**Verification:** GitHub source and source-invariant checks passed. This code has **not** been compiled/run in TradingView Pine Editor by the assistant.

## V14 — Fix pivot LOW/HIGH cycle starting point and repeated lines (2026-11-22)

**Latest test release:** [ASJR Gann Ideas V14](ASJR_Gann_Ideas_V14.pine)

**Why:** The COHR 4H screenshot with Cycle A = 12 bars and Pivot LOW selected showed the anchor on a recent minor swing and only a small number of verticals. V13 selected the **last confirmed pivot in the visible range**, which was often too near the right edge to generate many 12-bar markers.

**V14 correction:** **Pivot LOW = lowest confirmed pivot low inside the visible chart range. Pivot HIGH = highest confirmed pivot high inside the visible chart range.** The pivot's **original candle** (not its later confirmation candle) is bar 0. Only confirmed pivots are eligible; candidates near the chart's right edge require the configured right-side confirmation bars, and the current unconfirmed low cannot be selected early. If the visible range contains no confirmed pivot, the code falls back to the most recent confirmed pivot before the visible range.

**Repeat interval:** Cycle A = 12 bars creates +12, +24, +36, +48 … from the chosen bar 0; Cycle B = 90 bars creates +90, +180 … . Historical verticals are rebuilt from existing exchange candles in the current viewport; **three upcoming projected markers per enabled cycle** replace V13's single future marker when drawing bounds permit. Bar-index drawings cannot be more than 500 bars ahead of the live script execution or more than approximately 10,000 behind it; extra projections beyond this are silently skipped to avoid TradingView runtime errors.

**Scrolling:** The strongest confirmed pivot is recomputed for the new visible window when you scroll/zoom. This is intentional, view-dependent exploration and not a fixed backtesting reference. The **Manual UTC** option retains prior behaviour for reproducibility, including its single next projected line. Cycle intervals, time-unit choices, colours, the eight horizontal Gann calculations, ten switches, optional labels and historic vertical line caps remain intact.

**Test:** On a COHR 4H chart, select Pivot LOW, Cycle A = 12 bars and scroll to include the older major low. You should see the gold zero marker on the lowest confirmed low and multiple dashed 12-bar intervals to the right, plus additional future markers. Switch to Pivot HIGH to choose the highest confirmed swing high. Repeat on 15m and when scrolling to a different window. Please provide a screenshot if the live Pine indicator differs: GitHub source/logic checks passed, but it has **not been compiled or run in TradingView** by the assistant.

## V13 — New numbered release (2026-11-22)

**Latest release:** [ASJR Gann Ideas V13 Pine v6](ASJR_Gann_Ideas_V13.pine).

V13 is a **new, separately named source file**, deliberately preserving the V12 implementation of scroll-aware confirmed **Pivot HIGH / Pivot LOW** starting points and the **Manual UTC** alternative. All eight price methods, configurable Cycle A/B lengths and units, monk colours (25% default opacity), and optional labels are unchanged.

**Release convention:** Every subsequent ASJR Gann release gets a new version number and a new Pine Script filename. Previously published versions remain available unchanged. V12 can remain on existing TradingView charts while V13 is tested separately.

V13 was verified against V12 by comparing the sources after removing only the version title and the new release-note comments. **TradingView compilation, runtime and scrolling behaviour are not independently verified.**

## V12 — Scroll-aware Gann time-cycle anchor (2026-11-22)

**Latest source:** [ASJR Gann Ideas V12 Pine v6](ASJR_Gann_Ideas_V12.pine).

### Starting-point selector

Added **one dropdown** in `02 — Vertical time cycles`: **Cycle starting point**.

| Setting | Meaning |
| --- | --- |
| **Pivot LOW** (default) | Use the latest **confirmed chart-timeframe swing LOW** whose pivot candle is within the visible window |
| **Pivot HIGH** | Use the latest **confirmed chart-timeframe swing HIGH** whose pivot candle is within the visible window |
| **Manual UTC** | Keep V11's manually selected date and time as the fixed reference |

When there is no confirmed pivot *within* the visible range, automatic mode uses the most recent confirmed pivot **before** the left edge. If no qualifying confirmed pivot is available in the loaded price history, no automatic cycle/0 marker is drawn. This is safer than inventing an anchor.

The selection uses the **existing** `Confirmed swing pivot left/right bars` input (**3** by default) in the price-anchor group; it **does not** change the Dynamic H / C price anchors. Automatic cycle pivot detection uses the **chart timeframe**, while `Gann price source timeframe` still applies to price-level families.

### The bar-zero rule and scrolling

A pivot requires `pivotLen` future bars to confirm. **The actual high/low pivot candle becomes bar 0**, but it is not selectable until the right-side confirmation candles close. This distinction is important when reviewing historical examples; it avoids treating an unconfirmed high or low as a known trading signal.

For Cycle A length = **12 bars** and Cycle B length = **90 bars**, historical lines appear at pivot +12, +24, +36… and +90, +180… chart candles. The two cycle lengths remain independently editable from **1–500**, with independent `bars / mi / hh / day / m / y` units.

Moving the chart horizontally updates TradingView's `chart.left_visible_bar_time` / `chart.right_visible_bar_time`, which triggers a script recalculation. In automatic Pivot HIGH/LOW modes, the algorithm selects the newest confirmed pivot **in the displayed historical window**, rebuilding the historical lines accordingly. This is *view-dependent*, so it is for visual studies—not a stable backtest anchor. For reproducible testing, choose **Manual UTC**.

In pivot mode the selected pivot is indicated by a **subtle, solid gold vertical zero line**. Turning on the existing `Show line labels` option displays its `0 · Pivot HIGH/LOW` label; the default remains OFF. Cycle lines remain dashed and use the existing per-method monk-friendly colours (25% default opacity).

For calendar/clock units, a boundary that falls in a market closure is shown on the **first available candle after it**, rather than drawing a line in an empty session gap. The next projected cycle marker is based on the **right edge of the visible window**, not necessarily the most recent live candle. TradingView prevents `bar_index` drawings beyond 10,000 bars into the past or 500 bars into the future; when scrolling very far backwards, a far-away **future bar-count projection may be omitted** while actual historical cycle lines remain plotted. Historical visible samples are capped to the latest 6,000 candles for drawing-performance reasons; older markers may be omitted in an exceptionally wide view. The existing `Historical verticals per cycle` input still caps each family (48 by default, 100 maximum).

**Unchanged:** Exactly 10 main switches (8 price / 2 vertical), all eight price-family algorithms, the editable 12/90 defaults and 6 units, manual UTC anchor value, 25%-opacity monk palette, label preferences and existing appearance controls. V11 remains intact.

**Validation:** GitHub file saved and structural invariants checked. TradingView Pine Editor compilation/runtime and scroll-triggered behaviour cannot be directly tested from here; please validate Pivot LOW, Pivot HIGH, Manual UTC and scrolling on MES/COHR before using these lines for research.

## V11 — Monk-friendly colours at 25% opacity (2026-11-21)

**Latest source:** [ASJR Gann Ideas V11 Pine Script](ASJR_Gann_Ideas_V11.pine).

The ten method-specific colour-picker **defaults** now use a calm monastery-inspired palette suitable for dark charts. All have **25% opacity**, represented by `color.new(#HEX, 75)` in Pine Script (75% transparency). The palette keeps every method distinguishable without overpowering price candles.

| Feature | Colour name | Default hex |
| --- | --- | --- |
| 1. Factor of 8 | Monastery ochre | `#D39828` |
| 2. Yearly highs/lows | Sandal gold | `#E3BC73` |
| 3. Power of squares | Terracotta | `#B76B4A` |
| 4. Power of cubes | Oxide red | `#96473F` |
| 5. Square of 9 static | Saffron | `#E88735` |
| 6. Square of 9 dynamic H | Warm vermilion | `#BE4B39` |
| 7. Square of 9 dynamic C | Meditation sage | `#71917B` |
| 8. Square of 360 | Stone linen | `#C9B9A5` |
| 9. Vertical Cycle A | Monk maroon | `#A04758` |
| 10. Vertical Cycle B | Himalayan slate blue | `#7799AE` |

When labels are enabled, **their text uses the configured colour's existing opacity**, rather than overriding it to 100% opacity. Price-label background transparency defaults to **75%** (25% opacity). Existing settings permit changing this independently; default labels remain **off**, as in V10.

**Unchanged:** eight Gann price-level calculations, original line-placement logic, editable Cycle A / B lengths (12 and 90 by default), independent time unit dropdowns, ten feature switches, chart-timeframe handling and default disabled labels. V10 and earlier are preserved. **TradingView compilation not independently verified**; source consistency and GitHub commit checked.

## V10 — Configurable vertical-cycle lengths (2026-11-21)

**Latest release:** [ASJR Gann Ideas V10](ASJR_Gann_Ideas_V10.pine), based on V9 (not V6). The eight horizontal Gann price families, angle-density controls, optional labels and original price calculations are retained.

**The 10 feature checkboxes remain unchanged:** eight price families and two independent vertical time cycles. What changed is that cycle lengths are no longer hard-coded:

| Switch | Numeric length | Unit dropdown | Default |
| --- | --- | --- | --- |
| 9. Cycle A | Editable **1–500** | `bars / mi / hh / day / m / y` | **12 bars** |
| 10. Cycle B | Editable **1–500** | `bars / mi / hh / day / m / y` | **90 bars** (off until enabled) |

Examples: **Cycle A = 10, bars** marks every 10 chart candles; **Cycle B = 100, bars** marks every 100 chart candles from the shared UTC anchor. You can change both independently, or select elapsed/calendar units instead. Both histories and next-future markers use the editable length; optional cycle labels display the selected number and unit.

Cycle B's default unit is now **bars**, matching the V6-style setting shown in the screenshot; V9 had defaulted Cycle B to minutes. All existing Pine files are preserved.

The shared UTC anchor and historical-verticals limit are unchanged. Note that TradingView cannot project a `bar_index` line farther than 500 bars into the future, so the numeric cap is 500. Changing the length/units may change which candles get a vertical marker, but does not change the horizontal Gann level calculations.

**Validation:** source changes and GitHub commit have been verified; direct TradingView compilation and live chart drawing are not independently tested.


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

**V5 colour-picker defaults update:** All 10 method colours now initialise at **25% opacity (75% Pine transparency)**, including vertical cycle lines. Colour-picker opacity remains independently editable for each method. This update **does not alter label font size, label text opacity, or label background transparency**. Existing TradingView instances with stored user inputs may retain old settings; reset the picker to defaults in the newly loaded script if needed.

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
