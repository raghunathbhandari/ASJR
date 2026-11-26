# Refinement plan — proposed research, not adopted rules

Goal: improve the original US equity reversal pattern while preserving every original candidate.

1. Reproduce all 83 September ex-post setups with ticker, UK and UTC timestamps, C1/C2/C3 OHLCV, entry/SL/R and price touches.
2. Compare two causal entry models separately: (A) C2-close-known setup with subsequent C2 body-top trigger, without future C3 filters; (B) completed C3 confirmation with next eligible entry. Neither replaces the frozen baseline.
3. Reconstruct stop/target ordering using 1-minute or tick data where possible; flag ambiguous bars rather than crediting wins.
4. Evaluate C2 sweep depth, wick/body ratio, C3 relative volume and body confirmation, session, trend and proximity to support as experimental features, not pre-approved mandatory filters.
5. Report signals, fills, wins/losses/BE, ambiguities, average R, gross and net P&L, maximum drawdown, costs and non-overlapping portfolio assumptions.
6. Use October and further independent dates for validation with frozen rules; avoid tuning on the validation sample.
7. Keep raw price data in its existing archive, do not duplicate into main. Do not modify shared notebooks or live bots.

No new backtest or live deployment was performed when creating this archive.
