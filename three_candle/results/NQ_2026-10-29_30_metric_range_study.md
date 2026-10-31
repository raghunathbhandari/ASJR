# Rudra Three-Candle — exploratory metric ranges (NQ 29–30 October 2026)

**Dataset:** [29 signals / 111-column source CSV](NQ_2026-10-29_30_15m_signals_research.csv). Outcome defined after the fact: GOOD = reached 2R+, WEAK = reached 1R only, BAD = below 1R using 0.20% R floor and conservative bar stop-first assumptions. 8 GOOD / 10 WEAK / 11 BAD (BUY 11, SELL 18).

**NO LIVE FILTERS CHANGED.** All tests are in-sample, post-hoc threshold sweeps, not predictive validation. C3 confirmation is known only after candle close and signal entry may be earlier: historical lookahead risk. Outcomes are not executable profits. ASJR 12-zone results are estimated from OHLCV, not true bid/ask volume delta. RVOL is cumulative over five prior observed sessions.

## C3 empirical distributions (min / 25th-percentile empirical / middle value / 75th / max; small samples)

| Metric | GOOD (8) | WEAK (10) | BAD (11) |
|---|---|---|---|
| C3 RSI14 | 45.137 / 45.208 / 47.932 / 49.741 / 60.091 | 23.383 / 36.826 / 41.640 / 48.109 / 57.355 | 26.532 / 39.061 / 46.925 / 47.932 / 54.224 |
| C3 MA20 distance % | -0.141 / -0.092 / -0.018 / +0.118 / +0.400 | -0.762 / -0.307 / -0.140 / +0.024 / +0.277 | -0.923 / -0.321 / -0.105 / -0.018 / +0.113 |
| C3 ATR % | 0.178 / 0.184 / 0.209 / 0.264 / 0.275 | 0.165 / 0.184 / 0.204 / 0.241 / 0.289 | 0.162 / 0.208 / 0.236 / 0.279 / 0.304 |
| C3 RVOL5 | 1.159 / 1.198 / 1.345 / 1.398 / 1.454 | 1.205 / 1.275 / 1.323 / 1.406 / 1.485 | 1.136 / 1.247 / 1.334 / 1.399 / 1.826 |
| C3 ASJR buy-share % (missing possible) | 43.137 / 63.521 / 72.291 / 72.868 / 83.778 | 30.596 / 37.592 / 53.623 / 55.181 / 67.617 | 30.825 / 49.132 / 65.172 / 76.910 / 83.120 |

## Threshold comparisons (29 signal in-sample)

| C3 rule | GOOD kept / 8 | WEAK kept / 10 | BAD rejected / 11 |
|---|---:|---:|---:|
| MA20 distance >= -0.15% | 8 | 6 | 4 |
| RSI between 45 and 60 (inclusive) | 7 | 5 | 5 |
| ATR percent <= 0.275% | 8 | 9 | 4 |
| MA20 >= -0.15%; RSI >= 45; ATR <= 0.275% | **8** | **4** | **7** |

The combined rule keeps 16/29 total, including 8 GOOD, 4 WEAK and 4 BAD. **This is in-sample selection and must not be presented as out-of-sample success.**

### BUY/SELL split and directionality failure

11 BUY: one GOOD, eight WEAK, two BAD. 18 SELL: seven GOOD, two WEAK, nine BAD. For the combined non-directional rule: BUY 1/1 GOOD kept and 1/2 BAD rejected; SELL 7/7 GOOD kept and 6/9 BAD rejected. Small and asymmetric samples.

When instead requiring BUY MA20 >= -0.15 / RSI >= 45 and SELL MA20 <= +0.15 / RSI <= 55, alongside ATR <=0.275, the directional alternative retains just **4/7 GOOD SELL** and rejects only 3/9 BAD SELL. Therefore the first rule's success appears to be sample-specific and is not a generally directionally sensible filter.

### Next validation

1. Freeze candidate thresholds now; test against September (untouched holdout) and other October dates without retuning.
2. Separate BUY vs SELL and RTH vs extended futures; report confusion matrices, GOOD retention, BAD rejection, sample sizes, and gain % net of execution assumptions.
3. Evaluate comparable feature definitions and correct ex-post entry lookahead before interpreting profitability; don't turn on automatic signal rejection yet.
4. If holdout does not confirm, revisit asymmetric or relative metrics (C2->C3 directional RSI, MA9 reclaim, volume pressure transition), but keep such analyses exploratory.
