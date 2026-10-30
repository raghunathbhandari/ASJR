# Rudra Three-Candle — AI session handoff
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

## Notebook compatibility confirmed for user test — 2026-10-30

User is about to run this existing Jupyter cell; preserve the public API:

```python
import importlib, three_candle
importlib.reload(three_candle)

test = three_candle.check_signals("INTC", "2026-10-28", "2026-10-28", r=0.10)
three_candle.show_chart(test)
```

- `check_signals(ticker, start, end, r=..., target_r=2, require_breakout=False)` and `show_chart(test, signal_number=None)` remain unchanged by the historical mode addition. The notebook cell uses **current Yahoo native-15m experimental breakout mode**, NOT historical RTH sweep/reclaim mode.
- This call fetches 15m Yahoo data for **28 October only**. A single-day end boundary leaves signals without next-session continuation; NO_FILL and OPEN must not be counted as losses or wins. Yahoo availability, extended-hours volume, and same-bar OHLC sequencing affect results.
- `r=0.10` is minimum R step size 0.10% of entry, not 0.10% account risk. `target_r=2` defaults to trailing activation at 2R, next bar; 1R lock was a distinct historical hypothesis.
- On any screenshot/result the user supplies, compare the timestamped C1/C2/C3 OHLCV, entry trigger, initial stop, bar-by-bar stop state, fill/exit times, and WIN/LOSS/OPEN/NO_FILL classifications. Be especially alert that same-bar entry-high and stop-low have unknown order.
- Chart conventions remain entry green, profitable trailing exit purple, SL/losing exit red. Do not claim the visual proves an executable fill.
- Historical regression mode is CLI `--historical-csv` and requires an archived 5m file. September IBKR regression was actually run and passed 10 ticker counts and price touches: 83 setups; 83/75/64 1R/2R/3R. It does not alter the notebook's default logic.

**Next action after user test:** inspect their actual notebook output first; do not silently change functions or assume 100% live-trading success. Any proposed rule change must be shown side-by-side and approved or explicitly requested.
