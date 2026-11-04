# THREE-CANDLE — SHARED STANDARD AND NEXT-SESSION HANDOFF

Updated 2026-11-04 (UK). **Applies to EVERY Three-Candle strategy:** MES, MNQ, NQ, GC, INTC, and future instruments/versions. This is a cross-strategy user-approved contract, not MES-specific.

## 1. LOCKED PUBLIC METHODS AND CALL FLOW

```python
result = three_candle_signal(tiker, datefrom, dateTo)
plot_candidates(result)
plot_signal_passed(result)
```

**Do not rename these public functions, change their input conventions, or swap the chart types in a future version without explicit user approval.** New versions may provide their own implementations, but preserve this interface. The `result` must retain everything both plotters need (all core candidates, GOOD/WAIT classification, metadata, and historical candles).

## 2. LOCKED NINE METHOD STAGES

Ordered internal analysis methods:

1. `candle_detect_core()` — C1/C2/C3 BUY and SELL hypotheses independently, C2 liquidity sweep and C3 confirmation. Keep ALL CORE-TRUE results even if filters later reject them.
2. `market_structure()` — confirmed swing HH/HL/LH/LL, bullish/bearish/range context, no future data.
3. `swing_sr_lines()` — confirmed swing support/resistance and nearby price levels.
4. `volume_detect()` — volume, relative volume and confirmation participation.
5. `wicks_detect()` — C2 rejection wick and last-five-candle wick congestion.
6. `daily_range_check()` — developing futures session range, previous completed session and directional room to go.
7. `display_other_metrics()` — diagnostic candle and technical indicator measurements for analysis.
8. `higher_timeframe_support()` — confirm higher-timeframe contextual direction using only closed candles.
9. `Liquidity_area_detect()` — identify historical liquidity/sweep areas, without treating OHLC as actual institution order data.

The scanner processes candles in chronological `for` loops and evaluates BUY/SELL separately. Market structure must inform direction and quality; a wick pattern alone is not proof of trend.

## 3. LOCKED CHART DESIGN

- `plot_candidates(result)`: **ONE full-range dark candlestick chart** of ALL CORE-TRUE candidates with **PURPLE dots on their C2 sweep candles** (below BUY C2, above SELL C2). Green/red candles; confirmed swing S/R; **EMA20 in gold**, **EMA200 in lavender/purple**; UK date/time. Do NOT turn this into one chart per candidate.
- `plot_signal_passed(result)`: **ONE focused detailed chart PER GOOD candidate**, clearly label C1/C2/C3, C2 highlighted, **ENTRY blue**, **SL red**, **TP purple**, numeric prices, confirmed swing S/R, **EMA20 gold / EMA200 lavender**, UK time and surrounding price action. Multiple pages may be exported as a PDF.
- Reference prices and simulated fills must be explicitly distinguished. The charts do not by themselves prove trade profitability.
- Keep these visual rules consistent between instruments and versions unless changed by explicit instruction.

## 4. DATA AND WARM-UP

Use instrument-appropriate available local CSV data (IBKR 5-minute CSV preferred where available), merge monthly history by timestamp, resample only complete 15-minute candles, use UTC for processing and Europe/London for labels. **Read earlier historical CSV bars BEFORE filtering to the requested dates**. Calculate EMA20/EMA200 and other indicators on full chronological history, never on only visible chart candles. EMA200 is unavailable until 200 bars have closed; show N/A rather than an inaccurate immediate value. Do not add Yahoo/IBKR network dependencies without a specific need and approval.

## 5. USER-REQUIRED SIGNAL PRINTING

`three_candle_signal()` prints each signal regardless of GOOD or WEAK/WAIT:
- signal number, UK date/time, BUY/SELL, price, GOOD/WEAK/WAIT;
- true/false and required/informational status for **each of the nine methods**;
- separate candle quality checks; clear rejection reasons;
- **ALL available metrics / indicators**, as in original `three_candle_learing.py` learning approach;
- study-only versus mandatory filters are clearly distinguished.

Diagnostic inventory from first learning version: C1/C2/C3 OHLC+volume, candle range/body/wicks %, sweep in ticks/points, C3/C2 volume ratio, RVOL20, EMA20/EMA200 distance and EMA20 slope, RSI14, ATR14, BB20 width, session VWAP/distance, prior20 high/low and sweep, rolling 10/20 range, price approach/recovery, confirmed S/R room, session time classification, current/previous futures-session range. More ideas can be discussed, but should not become mandatory checks automatically.

## 6. CODE WRITING STANDARD — MANDATORY ACROSS STRATEGIES

- Python must be **human-readable and easy to edit**, not clever/over-abstracted; descriptive variables, simple loops, and clear separation between core/structure/filters/metrics/plotting.
- Comment all major code blocks to explain purpose and reasoning; add docstrings for every named method.
- Group settings/thresholds near top; document units and defaults.
- Preserve audit trail for every candidate including failed ones; no hindsight/lookahead/repainting.
- Do NOT edit original notebooks, source data, old masters, or unrelated strategy versions without authorization.
- Prefer adding an isolated new research version rather than breaking an old one.

## 7. FUTURE SESSIONS — IDEAS FIRST, NOT UNREQUESTED IMPLEMENTATION

**Next session should focus on trading ideas, chart evidence and structure validation** rather than re-discussing the established API and plot formats. Transfer only approved research concepts between strategies. New signal logic, thresholds, files, or plotting changes require explicit user direction. Clearly differentiate implemented, proposed, and runtime-validated functionality. Avoid claiming backtest results without replaying historical data.

## 8. CURRENT MES REFERENCE AND VERIFICATION

Current MES research code:
- `three_candle/mes_relax_pipeline_v1.py`
- `three_candle/mes_relax_structure_first_v1.py`
- Detailed historical working notes: `three_candle/MES_RELAX_V1_CORE_AND_RESEARCH_HANDOFF.md`
- Input MES CSV files: `three_candle/data/MESZ2026_IBKR_5m_2026-09.csv`, `2026-10.csv` (both full filenames start MESZ2026_IBKR_5m_).

Current MES quality hypotheses: C2 directional wick >=2x body; sweep >=2 MES pts; strong C3 directional close; WAIT if >=2 of last 5 candles have excessive both-sided wicks. Independent market structure alignment is in current experimental code. These parameters are NOT validated cross-instrument defaults.

The GitHub changes have been committed. **Python compile/execution and chart generation still require verification** after local/VPS sync:
```bash
cd /root/trading/ASJR
git fetch origin
git merge --ff-only origin/main
python3 -m py_compile three_candle/mes_relax_pipeline_v1.py
python3 three_candle/mes_relax_pipeline_v1.py --date 2026-10-29 --plot-both --show-wait
```


## 9. Confirmed printing split (2026-11-04)

`three_candle_signal(tiker, datefrom, dateTo)` is responsible for printing the **nine named method check results** (True/False, Required/Optional) for every **CORE-TRUE candidate classified WEAK/WAIT**, along with its candle-quality checks, metrics, indicators and rejection reasons. For **GOOD** candidates, print only a concise signal summary: times, prices, direction, key metrics, and “Mandatory filters=PASS”; do not repeat the nine check lines for GOOD. All diagnostic values for GOOD remain available in result and output CSV.

**Important:** GOOD means that all **currently mandatory** checks passed, not necessarily that every one of the nine informational/optional observations is True. In particular, `Liquidity_area_detect()` may be False yet GOOD if disabled as a mandatory check. Printing preference must not modify filtering rules or the two chart formats.

Implemented in MES code commit `4303a4f`. This formatting standard applies across future Three-Candle strategies.


## 10. RUDRA THREE-CANDLE — FINAL SESSION CLOSEOUT / IDEAS-ONLY HANDOFF (2026-11-04 08:37 UK)

**Assistant role:** Rudra Three Strategy. All methodology, names, chart design, metrics, CSV history handling, printing conventions and coding rules above are confirmed. **In the next session, discuss trading ideas, evidence and hypotheses only. Do not change strategy code, settings or plots during an ideas discussion unless the user explicitly requests implementation.**

### Stable public notebook API (all Three-Candle variants)
```python
result = three_candle_signal(tiker, datefrom, dateTo)
plot_candidates(result)
plot_signal_passed(result)
```
- `three_candle_signal`: reads the instrument's existing local CSV history, resamples complete 5m to 15m where appropriate, scans every candle chronologically for independent BUY/SELL C1/C2/C3 patterns, runs the fixed nine analysis methods, prints diagnostics, returns CORE-TRUE rows with GOOD/WAIT statuses and indicators. It is the **main method** and owns all signal printing.
- `plot_candidates`: one entire requested-period dark candle overview (not one chart per candidate). **Purple C2 candidate dots**, confirmed swing S/R, **EMA20 gold**, **EMA200 lavender**, all times UK.
- `plot_signal_passed`: **one detailed chart per GOOD** with C1/C2/C3, entry blue, SL red, TP purple, actual numeric reference levels, EMA20/EMA200, swing S/R and UK time. These levels are study references, **not execution fills**.
- The **nine internal names and order**, retained across all future strategies: `candle_detect_core`, `market_structure`, `swing_sr_lines`, `volume_detect`, `wicks_detect`, `daily_range_check`, `display_other_metrics`, `higher_timeframe_support`, `Liquidity_area_detect`.
- Current supporting methods: `scan`, `evaluate_pipeline`, `calculate_indicators`, `indicator_metrics`, `print_signal_details`. These are internal; avoid exposing them as mandatory notebook calls.

### Confirmed printing convention
- In `three_candle_signal`, print a numbered header for **every** CORE-TRUE candidate: UK C3 timestamp, direction, close, GOOD or WEAK/WAIT.
- **WEAK/WAIT:** all **nine true/false method observations** (also mark REQUIRED vs INFO/OPTIONAL), separate candle-quality subchecks, **all existing metrics / indicators** and explicit rejection reasons.
- **GOOD:** concise signal header, C1/C2 times, price, structure, sweep, wick/body and key EMA levels; say **all enabled mandatory checks PASS**. Do NOT repeat nine method booleans for GOOD. Full diagnostic values are still kept in result and written to CSV when exported.
- A GOOD candidate **does not mean every informational method returns True**. Optional checks such as `Liquidity_area_detect` can be False. No classification change is implied by print layout.

### Historical CSV / indicator policy
- Read **all earlier available source CSV data** for sufficient warm-up **before** restricting signal dates or visible chart window; for MES 29–30 October 2026 the September and October 5m IBKR CSVs are merged chronologically and resampled to complete 15m bars.
- EMA20/EMA200 are calculated on full historical data and drawn on **both** charts; warm-up is **20 / 200 completed 15m candles** respectively. Where unavailable, show N/A, not a prematurely initialized EMA. RSI14, ATR14, BB20 width, session VWAP, RVOL20, OHLCV, candle anatomy, volume ratios and price-context research fields print as diagnostics; do not silently turn into new filters.
- Use readable variable names, plainly written loops, short documented functions, main-step comments, settings up top with units, and no future lookahead.

### First executed MES validation, important distinctions
- Actual Python 3.11 GitHub Actions public API run for **29–30 October 2026**: https://github.com/raghunathbhandari/ASJR/actions/runs/41793966304
- Confirmation run with corrected **observed** optional check booleans: https://github.com/raghunathbhandari/ASJR/actions/runs/41793966304/artifacts/13304478251
- **29 October: 27 CORE, 0 GOOD, 27 WAIT. 30 October: 24 CORE, 2 GOOD, 22 WAIT. Total 51 CORE, 2 GOOD, 49 WAIT.**
- Both GOOD were SELL on 30 October: C3 **15:00 UK at 7641.75** (2.75pt C2 high sweep, 4.75× rejection wick); C3 **16:45 UK at 7614.00** (3pt C2 high sweep, 2.57× rejection wick).
- Overlapping WAIT reasons: `market_structure=30`, `wick2=29`, `wick_congestion=24`, `sweep2=20`.
- **No trading win rate or P&L established**: only candidate classification and plotted study reference prices, not 5m next-open entry/TP/SL replay.
- After the final public API real run, printing was updated to omit repeated nine-method check rows for GOOD (`4303a4f`); this formatting-only change has **not been separately rerun**. Earlier stale lines in this handoff that say runtime unverified are superseded by the execution results above.
- MES-specific experimental thresholds are **not automatically portable** to NQ, GC, or equities.

### Next session: ideas only
Suggested discussion topics, not instructions to edit: understand why all 29 Oct candidates failed; study two 30 Oct SELL charts; analyse whether market-structure recognition and liquidity level placement match real price action; explore how much room-to-target and previous-session extremes matter; later request 5m execution replay with commissions/slippage when desired. Preserve the existing user notebook, original learning file, existing source CSV and old research master datasets.


## 11. Liquidity area study lines and printing (2026-11-04)

User-approved implementation only: keep Method 9 informational. For each CORE-TRUE candidate, `liquidity_levels_at_signal()` reads **confirmed** swing pivots available through C3 and records the **closest confirmed swing high at or above C3 close** as buy-side liquidity, and **closest confirmed swing low at or below C3 close** as sell-side liquidity. It records exact price and distance in points, or N/A if none; this is a *price-level hypothesis*, not observed resting order volume. `three_candle_signal()` prints these two current areas even for GOOD (but continues to print nine true/false method lines for WEAK/WAIT only). Existing `Liquidity_area_detect()` swing-touch boolean remains separately available and is NOT a new mandatory filter.

On `plot_candidates()`, draw **two dashed current liquidity lines** from the **latest candidate's** C3-known levels (buy-side amber, sell-side teal) to chart end, labelled with prices; selecting only the latest avoids clutter. On each `plot_signal_passed()` page draw those two dashed lines using the corresponding individual GOOD signal's C3-known levels. A line may begin only after its underlying swing is confirmed; no lookahead. Preserve existing short swing S/R lines and EMA20/EMA200. Source change `9dfde8d`.

This change does not alter the core pattern, GOOD/WAIT classification, plotting API, or prior test assumptions. Compare printed levels with actual chart context before considering them as future filters.
