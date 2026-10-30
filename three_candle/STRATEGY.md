# Rudra Three-Candle — Strategy and implementation contract
Updated 2026-10-30 (UK). Research only; no live-execution or verified performance claim.

## Two distinct models — do not mix results

| Rule | Historical research v1.1 (2026-10-25, `rudra-data-results`) | Current `main/three_candle/three_candle.py` |
|---|---|---|
| Market/session | 15m RTH bars resampled from 5m | Native Yahoo 15m, `prepost=True`, includes extended hours |
| C1/C2 sweep | C2 low < C1 low; C2 close > C1 low | No C1 price condition |
| C2 shape | Green, **lower** wick > body | Green, **either** upper or lower wick > body |
| C3 | Volume > C2 and close > C2 close | Volume > C2; C3 price confirmation optional (`--require-breakout` uses C3 high > C2 high) |
| Entry hypothesis | C2 close | Stop-buy at C2 high, first eligible bar **after** C3 |
| Initial SL | C2 open | C2 open |
| R step | max(C2 body, 0.10% of C2 close) | max(C2 high - C2 open, `--r-pct`% of C2 high), default 0.10% |
| Trailing | On first 1R touch, lock 1R; then 2R, 3R... | At 2R high, new stop at 2R becomes active **next bar**; then 3R, 4R... |
| Ambiguous OHLC bar | Record unresolved; require finer sequence | Checks current stop first and credits stop fill at stop level |
| Fees, gaps, capital | Not proven | Not modeled; independent signals can overlap |

**These are incompatible backtests.** Do not combine their signal counts, win rates, R multiples, or P&L.

## Current code: exact interpretation

Source of truth: [three_candle.py](three_candle.py). `find_signals` scans consecutive completed C1/C2/C3 Yahoo 15m bars. C2 must be bullish and have at least one wick longer than its body; C3 volume must strictly exceed positive C2 volume. `--require-breakout` optionally checks C3 high > C2 high. No sweep/reclaim, RTH-only, C3 close > C2 close, or additional C1 validation is enforced by the current script.

`backtest_signal` places a hypothetical C2-high stop-buy on the first bar after C3, with initial SL C2 open. A bar whose high reaches entry is counted filled. **That same bar's low can also trigger the initial stop, even if the low occurred before entry**; chronology is unknown. The original stop is checked before updating a milestone. After observing a new 2R+ high, the stop advances for subsequent bars. A stop exit at >= `target_r` is counted WIN; other stop exits LOSS. Unfilled signals are NO_FILL, filled-but-unclosed signals OPEN, invalid distances INVALID. Its success percentage is WIN/(WIN+LOSS), not wins/all signals.

Important current-code limitations: target_r controls both trailing activation and WIN classification, there is no separate fixed TP order; all candidate trades are independent and may overlap; no costs, slippage, commissions, capital allocation, gaps, partial fills, or 1m intrabar sequence. An unfilled or still-open trade is not a verified win. A dataset ending soon after a setup cannot give reliable closed-trade statistics.

## Historical research: documented findings, NOT executed profitability

Archived source: [old STRATEGY.md](https://github.com/raghunathbhandari/ASJR/blob/rudra-data-results/Rudra-Three-Candle/STRATEGY.md) and [AI handoff](https://github.com/raghunathbhandari/ASJR/blob/rudra-data-results/Rudra-Three-Candle/AI_SESSION_HANDOFF.md).

- September 2026, 10 tickers (AMAT, GOOG, INTC, LRCX, META, MU, NVDA, PLTR, SPY, XOM), 83 ex-post historical patterns: 83 later touched 1R, 75 touched 2R, 64 touched 3R. These are **future price-touch rates (100%, 90.4%, 77.1%)**, not executable win rates.
- September INTC Yahoo 5m: 8 qualifying ex-post setups; 8/8 later 1R touches, 7/8 2R, 6/8 3R. Several first-stop hits or same-bar ordering conflicts prevent a 100% execution conclusion.
- October INTC three selected setups (2, 6, 9 Oct) later reached 2R, 9R, and 4R maximum price excursion respectively. The original stop was also touched in the five-minute C3 bar and C3 volume would not have been known at a C2-close entry.
- The 83/83 1R touches **must not** be labeled 83 closed wins, zero stops, or +8.30% realized return; similarly +15.00% and +19.20% are not verified P&L.
- INTC September source discrepancy: IBKR 11 patterns vs Yahoo 8; audit feed, session boundary, candle rounding, and filter parity.

Historical data references on the `rudra-data-results` branch:
- September INTC Yahoo: `Rudra-DDB/DataBridge/exports/data-2026102520521/INTC.csv`
- October INTC Yahoo: `Rudra-DDB/DataBridge/exports/data-2026102417101/INTC.csv`
- Historical 10-ticker IBKR 5m: `Backtesting/BacktestData/IBKR/MarketData/5m/{TICKER}_5m.csv`
- Nine additional October ticker imports: `data-2026102520591` and `data-2026102520592` under `Rudra-DDB/DataBridge/exports/`; do not assume a complete re-test has occurred.

## Next reproducibility gate

1. Choose and freeze one model with a versioned configuration; do not alter the past results in place.
2. Use matching 5m→15m RTH construction if reproducing the old 83 signals; explicit `America/New_York` RTH boundaries and `Europe/London` output to handle late-October DST.
3. Enforce causal knowledge: C3 volume can only confirm a trade **after C3 closes**. A C2-close entry with C3 volume is ex-post research only.
4. Distinguish signal, eligible entry, actual fill, intrabar ambiguity, initial-stop touch, R milestone, trailing-stop activation, and exit, with timestamped trade log.
5. Test 1m/ticks where stops and milestones are touched in the same 5m/15m bar. Report ambiguous as a separate class or explicit bounded scenarios.
6. Report closed-trade WIN/LOSS/OPEN/NO_FILL/INVALID and ambiguous counts; net performance after IBKR tiered fees, third-party charges, slippage, capital limits and overlapping positions.
7. Check 0.10% and 0.20% minimum R separately; never transfer a win rate between parameter settings without rerunning.
