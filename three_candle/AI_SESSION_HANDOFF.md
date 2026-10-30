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
