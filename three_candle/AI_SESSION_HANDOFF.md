## 2026-10-30 — v2.3.2 minimum-size filter; SELL setup identified for separate research

- User observed that the second BUY (C2 16:30 UK on NQ 29 Oct) is invalid because C1 and C2 are too small. Added **configurable provisional minimum whole-candle (High-Low) ranges**, as percentages of each candle's closing price: `minC1RangePct=0.20`, `minC2RangePct=0.25`. Both must pass. Function parameters in `check_signals` and helpers; existing notebook method names kept. These defaults are initial research choices, **not optimised/validated thresholds**.
- Exact 29 Oct examples: 14:30 C1 range 0.315%; 14:45 C2 range 0.465% => original BUY candidate remains. 16:15 C1 range 0.156%; 16:30 C2 range 0.181% => second BUY rejected.
- User's operational BUY entry is **intrabar during C3** upon crossing above the higher of C2 open/close. The historical `check_signals` target-touch method still uses an older ex-post reference; do **not** represent it as executable entry P&L until replaced and intrabar stop ordering verified using 5m/1m data.
- User also proposed a **separate SELL model** where **C3 is the sweep candle and entry triggers on the next red candle**. This is a research direction, **not yet implemented**; decide exact prior high swept, entry price threshold and confirmation timing before reporting a sell performance.
- Version: `2.3.2-20261030`. No change to chart colours/signals UI or SELL backtest yet.

## 2026-10-30 — v2.3.1 relaxed bullish C2 / green C3 confirmation

- Requested: allow bearish **or** bullish C2 sweep, but C3 must be **green** for a BUY signal. C2 no longer has to close above C1 low. The existing C2 lower wick > absolute C2 body and C2 low < C1 low checks remain.
- Function: `is_bullish_three_candle_sweep()`; `checkVol=False` default remains unchanged, optional volume-on mode remains available; still requires C3 close > C2 close. This is a pattern-detection change, **not** proof of a profitable entry or a filled trade.
- 29 Oct NQ 15m user-identified sequence: C1 14:30 low 29531.75, C2 14:45 red (O29577.00 L29449.00 C29526.00; lower wick 77 > body 51), C3 15:00 green (O29525.75 C29613.00). This case now passes the BUY predicate with volume OFF. Since C3 opens 15:00, confirmation occurs at **15:15 UK**, not at the start of 15:00.
- Printed version increased to `2.3.1-20261030`. Existing `check_signals()`, `show_chart()` API unchanged; chart still shows swing lines only.
- Only the supplied example's Boolean predicate was checked during the change; full 29/30 October scanner regression and data feed retrieval have not been rerun.

## Developer review guide — function map and execution flow (v2.3.0)

The source of truth is `main/three_candle/three_candle.py`.
The user will review and edit Python personally. Keep method names descriptive and retain
the public notebook interface. On every future code change, **increment `__version__`**
and print it on import and when `check_signals()` runs.

### Notebook calls

```python
import importlib, three_candle
importlib.reload(three_candle)
three_candle.show_method_flow()  # prints this processing sequence

test = three_candle.check_signals(
    "NQ=F", "15min", "2026-10-30", "2026-10-30",
    r=0.20, checkVol=False, session="extended",
    swingLeft=3, swingRight=3, swingProximity=0.25,
    nearSwingOnly=False
)
three_candle.show_chart(test)  # all swing price lines; signals hidden
```

### Exact order of execution

1. `check_signals()` parses ticker/date/timeframe/session, validates `checkVol`.
2. `get_timeframe_minutes()` converts requested timeframe into numeric minutes.
3. `download_candles_from_yahoo()` gets raw 5m OHLCV **or** `load_candles_from_csv()` loads research data.
   - `clean_downloaded_candles()` normalizes columns/time/index.
   - `find_missing_regular_hours_candles()` detects US RTH gaps for retry and reporting.
   - `remove_suspicious_nq_candles()` quarantines extreme/invalid NQ bars.
4. `build_regular_market_candles()` aggregates RTH only, or `build_extended_nq_candles()` aggregates NQ's extended futures session. `build_extended_nq_4hour_candles()` handles the special 4H grouping.
   - Only complete consecutive 5m groups form higher timeframe bars. No synthetic prices.
   - `get_trading_session_dates()` keeps pattern sequences inside the correct session.
5. `find_confirmed_swing_levels()` collects confirmed local support/resistance pivots, using configured `swingLeft` and `swingRight` candles; a level is only available after the right-hand confirming candle has closed.
6. `find_three_candle_setups()` iterates contiguous C1/C2/C3 and calls `is_bullish_three_candle_sweep()`. Volume comparison is OFF with `checkVol=False`.
7. `find_nearest_swing_for_setup()` tests each C2 wick against already-confirmed supports/resistances using `swingProximity`. `nearSwingOnly=True` filters results; default False does not.
8. `count_future_target_touches()` and `sum_hypothetical_target_returns()` produce **ex-post** research metrics only; these are not executable P&L or win rates.
9. `check_signals()` prints summary/details and returns a dictionary containing `data`, `signals`, `swing_levels`, `swing_matches`, `touches`, `potential_gains_pct`, and settings.
10. `show_chart(test)` plots full-period candlesticks/volume plus **all** confirmed swing support and resistance price lines. It currently intentionally does NOT plot signal entry, stop, or targets.

### Code edit guide

| What Raghu wants to change | Edit method |
| --- | --- |
| Yahoo download/data range | `download_candles_from_yahoo()` |
| Missing bars or abnormal NQ candles | `find_missing_regular_hours_candles()`, `remove_suspicious_nq_candles()` |
| RTH versus overnight candle aggregation | `build_regular_market_candles()`, `build_extended_nq_candles()` |
| C2 wick/sweep and C3 confirmation conditions | `is_bullish_three_candle_sweep()` |
| Pivot support/resistance sensitivity | `find_confirmed_swing_levels()`; knobs `swingLeft`, `swingRight` |
| Proximity of Three-Candle C2 to a prior level | `find_nearest_swing_for_setup()`; knob `swingProximity` |
| Historical target-hit research | `count_future_target_touches()`, `sum_hypothetical_target_returns()` |
| Print layout and public parameters | `check_signals()` |
| Chart candle/volume/swing line styling | `show_chart()` |

**Compatibility:** Previous internal function identifiers remain as aliases in the Python file;
`check_signals()` and `show_chart()` are unchanged public entry points. The Python
code is version `2.3.0-20261030`. This guide is documentation-only; no code change,
version bump or new performance claim accompanies this document update.

---

## 2026-10-30 — v2.3.0: human-readable Python methods for user maintenance

- Renamed internal functions into descriptive verbs (`download_candles_from_yahoo`, `build_extended_nq_candles`, `find_three_candle_setups`, `find_confirmed_swing_levels`, `count_future_target_touches`, etc.).
- Grouped code under numbered comment sections from inputs through data download, resampling, pattern, swings, ex-post research, public `check_signals` and chart.
- New `three_candle.show_method_flow()` prints the complete main call sequence.
- Preserved external notebook API `check_signals(...)` and `show_chart(test)`, current session, `checkVol=False`, all-swing chart behavior and default settings. Old internal names are kept as backwards-compatible aliases.
- Display version increments and prints `2.3.0-20261030`.
- Python syntax parse and runtime import/alias/helper checks succeeded on the prior unsectioned v2.3 content; final sectioned version passed Python syntax parsing. Trading performance was not re-backtested; this is intended as a naming/documentation refactor only.

## 2026-10-30 — v2.2.1 all swing lines first

- `show_chart(test)` now plots **one full-range candle chart** with **all** confirmed swing support (turquoise dashed) and resistance (orange dashed) levels; removed nearest-six limit.
- Each horizontal level begins at its confirmation timestamp and extends to the last candle, rather than appearing before it could have been known.
- No Three-Candle signal boxes, entry, SL, 1R/2R/3R or matching overlay are drawn in this version. The pattern research output from `check_signals` is preserved.
- `show_chart(test, signal_number=...)` remains callable, but signal_number is currently ignored in the lines-first display.
- Version prints `2.2.1-20261030` on import and in the scan.

## 2026-10-30 — v2.2.0: confirmed swing price lines + Three-Candle proximity

- Kept existing notebook API, default `checkVol=False`, `session="extended"` for NQ; version printed as `2.2.0-20261030`.
- New kwargs: `swingLeft=3`, `swingRight=3`, `swingProximity=0.25` (percent), `nearSwingOnly=False`.
- Causal pivot detection: price is a strict local minimum (SUPPORT) or maximum (RESISTANCE) versus `swingLeft` prior candles and `swingRight` subsequent candles. Pivot is known only after last confirming candle closes. Pivot neighbours must be contiguous in the same US session, including NQ extended futures trade-date grouping.
- Match a Three-Candle C2 sweep to *already-confirmed* price levels: measure C2 low distance to support and C2 high distance to resistance; choose the closest and report `NEAR`/ `FAR` with wick distance percent and pivot timestamp. This is a proximity research metric, **not** yet statistical evidence of signal edge.
- Console summary prints total confirmed swings and near-swing signal count. Details print the nearest swing price line.
- `show_chart(test)` overlays the three closest confirmed support prices below the proposed entry and three closest resistance prices above it, turquoise/orange dashed horizontal lines, based only on levels known at C2 close.
- `nearSwingOnly=True` optionally filters reported signals to those within `swingProximity`. OFF by default so old signal counts and touches remain unchanged. No executed trade P&L model added.
- Test: synthetic consecutive 15-minute prices produce three pivot levels, all with `confirmed_at > pivot_time`; Python syntax and pivot code executed. A full live Yahoo download and September regression was **not** rerun.

## 2026-10-30 — v2.1.4 NQ extended session (5m / 15m / 30m / 1h / 4h)

- Added `session="extended"` to `check_signals` (default `"RTH"` preserves all older calls).
- Exact notebook call: `check_signals("NQ=F", "15min", "2026-10-30", "2026-10-30", r=0.20, checkVol=False, session="extended")`; `show_chart(test)` remains unchanged.
- Extended is currently NQ=F-only; RTH existing behavior remains unchanged; 4h continues using futures trading hours.
- 5m-source bars are anchored to 18:00 US Eastern futures-session open, 17:00–18:00 ET exchange break omitted. Start/end refer to US futures *trade dates*. Candles are complete 5m-group aggregates only; no fabricated Yahoo candles, including missing 30 October 18:55 UK bar.
- NQ overnight 30 October 01:45 UK C2 has long lower wick and reclaims the 01:30 C1 low. Its 02:00 C3 closes higher but has lower volume (3683 vs 4852); `checkVol=False` allows this pattern. A synthetic 5m resampling/logic unit test using the user's **15m OHLC values** verified the 01:45 C2 is detected with volume OFF, excluded with volume ON. **This is not a claim that Yahoo's genuine underlying 5m download has been independently validated**.
- All signal reports remain **ex-post C2-close hypotheses**, not causal execution backtests. Stop/target order and fees aren't simulated. Separate 01:45 entry at 02:00 with C2-open stop may hit SL before reaching profit targets.
- Version printed on import and every check: `2.1.4-20261030`. Display labels show session.

# Rudra Three-Candle — AI session handoff

## Highest-priority update: V2.0.0 rewritten 2026-10-30

The user explicitly requested **completely new code, retaining only calling
functions**. `three_candle.py` was rebuilt around the archived RTH strategy.
`check_signals(ticker,start,end,r=0.10)` and `show_chart(test)` stay callable.
Console version `2.0.0-20261030`, model `RTH_C2_SWEEP_EXPOST`. All previous
breakout default / 2R-trailing references below are **historical only** and
must not be interpreted as describing the new runtime.

New implementation uses Yahoo 5m data, RTH resampling to completed 15m candles,
C2 lower-wick sweep/reclaim of C1 low, C3 greater volume and greater close.
C2-close/SL=C2-open are **hypothetical ex-post levels**, not causal live fills,
because C3 volume cannot be known at C2 close. Output is 1R/2R/3R future
price-touch counts only; it no longer fabricates a 0%/100% executed win rate.
Charts: green C2-close hypothesis, red SL, purple R references (not realised TP).

Tests passed on archived September IBKR 5m ten-ticker data: 83 total setups,
83/75/64 price touches. `check_signals` and `show_chart` also tested locally
against archived INTC CSV: 11 INTC signals; 11/9/8 touches. Yahoo retrieval of
28 October still needs user-side confirmation. Accept old unused
`target_r` and `require_breakout` notebook keyword arguments for compatibility
but they do not change the historical pattern.
Updated: 2026-10-30 (UK). Canonical documentation folder: `main/three_candle/`.

**New validation:** historical CSV mode and archived-data unit test added 2026-10-30. Ten September 2026 tickers exactly reproduce setup counts 5,8,11,10,12,7,9,11,4,6 (total 83), and price touches 83/75/64 at 1R/2R/3R. Executed-trade result is **not** established. See README for the regression command; the original Yahoo post-C3 C2-high breakout logic remains separate.

## Read first
1. [STRATEGY.md](STRATEGY.md) distinguishes the archived C2-close/1R model from the new code's post-C3 C2-high/2R model.
2. [three_candle.py](three_candle.py) is the operational source for current Python behaviour. Read function bodies, not only README defaults.
3. [README.md](README.md) has the run examples and research warnings.
4. Historical research: [2026-10-25 handoff](https://github.com/raghunathbhandari/ASJR/blob/rudra-data-results/Rudra-Three-Candle/AI_SESSION_HANDOFF.md), [2026-10-25 strategy](https://github.com/raghunathbhandari/ASJR/blob/rudra-data-results/Rudra-Three-Candle/STRATEGY.md).

## User intentions and visual conventions
- Project: **Rudra Three-Candle Strategy**. Primary historical focus INTC; multi-ticker research AMAT GOOG INTC LRCX META MU NVDA PLTR SPY XOM.
- Price chart legend: **entry green**, **profit-taking / winning trailing exit purple**, **stop-loss red**. Do not portray a hypothetical/unfilled entry as an actual fill.
- UK date/time labels, including BST/GMT. The US/UK DST mismatch week must be handled explicitly.
- Experiments include 0.10% and 0.20% minimum R; trailing from 1R versus from 2R; 15m/30m/1h; $10k and $20k allocation; IBKR tiered fees/slippage. Each scenario requires its own reproducible backtest; previous rough results are not interchangeable.
- The user has cited 100% success on 83 September signals. That refers to a historical *price-touch* observation and is **not a verified execution win rate**. Explain carefully and investigate the event ordering.

## Current exact implementation (main)
- Yahoo native 15m `prepost=True`, date boundaries UK, default INTC.
- C2 green and either wick > body; C3 volume > C2 volume; C1 is present but has no liquidity sweep filter; optional C3 high > C2 high.
- After C3, entry trigger C2 high; initial SL C2 open; risk=max(entry−SL, entry×0.10% by default).
- Trail starts at 2R by default, advancing on the next bar. Existing stop checked first. Unfilled/open signals excluded from completed-trade success denominator.
- Caveat: same bar used for entry fill may also be used to hit SL, and exact intrabar ordering is not known. No fees or gaps modeled.

## Previously observed, NOT validated executed P&L
- September historical 10-ticker: 83 ex-post setups; subsequent 1R/2R/3R price touches = 83/75/64, respectively.
- September INTC: Yahoo 8 qualifying patterns vs IBKR 11; audit discrepancy.
- October first three INTC: later highs 2R, 9R, 4R; C3 timing and initial SL ambiguity. Do not assert 3 verified winners.
- Older quoted +8.30%, +15.00%, +19.20% theoretical fixed-step totals and subsequent net-gain discussions must not be treated as audited fee-adjusted realized results.

## Data provenance and next action
Data stored on `rudra-data-results` branch (see STRATEGY.md for explicit paths); do not silently copy large exports to live `main`.
First reconcile filters and session alignment, then generate an event-by-event execution ledger with ambiguous bars, SL-before-target, no-fill/open, and costs. Only then report audited success rate and capital returns. No trading orders are authorized by this handoff.

## Change management
Before changing Python or claiming an improved success rate, record the model version, exact filter diff, data date span/source, fees, same-bar assumption, and test commands. Preserve old research counts as historical rather than rewriting them.

## Timeframe support — V2.1.0 (2026-10-30)
The notebook now accepts either `check_signals("INTC","2026-09-01","2026-09-30",r=.10)` (old, defaults 15min) or `check_signals("NQ=F","15min","2026-09-01","2026-09-30",r=.20)` (new timeframe argument). Supported: `5min`, `15min`, `30min`, `1h` (aliases 5m/15m/30m/60m). All use complete 5m source bars grouped from 09:30 ET RTH, never bridging sessions; the incomplete final 30-minute block is omitted for 1h. C3 confirmation label adds selected timeframe minutes. Tested locally for all four intervals on archived IBKR INTC, and old 15min API still reproduces 11/9/8 1R/2R/3R touches across 11 signals. Results are ex-post price touches, not executed P&L. Do not compare raw signal counts across different timeframes as though filters operated on equivalent candles.

## NQ extended 4H — V2.1.1 (2026-10-30)
User chose extended futures hours for `check_signals("NQ=F","4h","2026-09-01","2026-09-30",r=.20)`. Implementation: fetch 5m Yahoo futures from one calendar day before the first requested trading date; group futures trading sessions beginning 18:00 ET previous calendar day, ending at 17:00 ET trade date; omit 17:00–18:00 ET maintenance and incomplete 14:00–17:00 ET final three-hour segment. Five complete 4H bars (18–22, 22–02, 02–06, 06–10, 10–14 ET) per full session, when 5m data are complete. Three-candle patterns must stay within one futures session. The `1h` and shorter intervals retain the existing 09:30–16:00 ET RTH treatment. 4H is restricted to `NQ=F`; other symbols raise a clear error. Model banner prints `NQ_EXTENDED_C2_SWEEP_EXPOST` and version `2.1.1-20261030`.

Validation: synthetic 5m overnight data produced 5 correctly anchored complete 4h bars per session; local archived INTC 15min regression remained 11/9/8 touches over 11 signals, and 1h call succeeded. Real Yahoo NQ 4h September retrieval and resulting signals remain **unverified** until user runs the notebook. 4h ex-post target touches still do not represent executable wins.

## Yahoo NQ data integrity fix — V2.1.2 (2026-10-30)
The 30-Oct-2026 NQ=F 5m Yahoo export contained 155/156 RTH candles, missing **18:55 GMT**, plus anomalous **19:00 GMT** OHLC (O/H 29562, L 28283.25, C 28307.25; 1278.75-point range). The old resampler omitted incomplete 18:45 15m bar and its scanner incorrectly joined nonadjacent 18:30 and 19:00 as C2/C3, manufacturing a 1R/2R/3R target-touch signal from the anomalous high. This is **not** valid performance.

V2.1.2 now: normalizes/deduplicates Yahoo 5m, checks expected 09:30–15:55 ET 5m timestamps for observed RTH dates, retries missing-date downloads once, prints unresolved timestamps in UK time, quarantines NQ 5m bars whose high-low exceeds 2% of previous close (or violate OHLC envelope) for manual verification, rejects incomplete aggregation groups, and enforces exact adjacent C1/C2/C3 timeframe spacing. Does **not** invent missing candles or claim the Yahoo source is repaired; 2% NQ threshold is a conservative quarantine heuristic, not proof a legitimate extreme move is impossible. The source file may still remain incomplete pending alternate vendor/IBKR confirmation.

Validation on user-uploaded 30-Oct NQ CSV: 19:00 suspect bar quarantined; 24 complete 15m RTH bars remained, **0 qualifying signals**, eliminating the false positive. September archived IBKR INTC 15m regression remained 11 signals with 11/9/8 target touches. No live Yahoo retry could be validated in this isolated test; user should observe console warnings. Do not interpret the zero as proof no real 18:55 overnight setup existed: the 18:55 RTH candle remains missing.

## Optional C3 volume filter — V2.1.3 (2026-10-30)
User requested `checkVol=False` by default in `check_signals(..., checkVol=False)`; `checkVol=True` restores the original C3 Volume > C2 Volume predicate (with nonzero C2). C3 bullish-close filter, C2 sweep/reclaim, source integrity and candle continuity are unchanged. Console prints version/timeframe/checkVol flag; signal details identify whether volume is on. Tests confirmed the user-provided 30-Oct NQ overnight C1 01:30/C2 01:45/C3 02:00 pattern fails checkVol=True (C3/C2=0.759×) and passes False, and historic Sept IBKR INTC scan with volume ON still gives 11 signals. **Important:** 15min still scans RTH only; this overnight setup is not yet automatically discoverable by `check_signals("NQ=F","15min",...)`. 4h uses NQ extended session. Prior historical signal counts were with volume ON and must not be compared to new default-off counts as equivalent tests.
