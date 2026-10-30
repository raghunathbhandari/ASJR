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
