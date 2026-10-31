# September 2026 NQ holdout — frozen October research thresholds

**Run 31 October 2026.** Independent JavaScript reimplementation of the existing three-candle retrospective BUY-C3 / SELL-C4 15-minute extended-session rules, applied to September 2026 NQ 5m archived data. All signal-size filters remain zero (broad research settings). This was **not** a verified native Python strategy run; small implementation differences are possible. September archive has known missing coverage and some partial sessions; incomplete 15m bars were excluded. 5,654 raw 5m bars -> 1,872 complete extended 15m bars -> **401 candidate signals**. Last signal's excursion observed only until the available dataset stops.

Outcome label: GOOD if max_r_before_stop >=2R, WEAK if exactly 1R, BAD if <1R. R floor = max(actual stop distance, 0.20% of underlying NQ price). Conservative SL-first OHLC on the breakout candle; green C3/red C4 hindsight confirmation carries look-ahead bias. These are price-target touches, not realized fills / net gain %.

| Holdout group | Baseline GOOD | Baseline WEAK | Baseline BAD |
|---|---:|---:|---:|
| All | 80 | 70 | 251 |
| BUY | 39 | 31 | 107 |
| SELL | 41 | 39 | 144 |

The **October-frozen** rules were evaluated *without retuning thresholds*.

| Candidate rule | Signals kept | GOOD retained | WEAK retained | BAD retained | BAD rejected |
|---|---:|---:|---:|---:|---:|
| C3 upper-wick >= 0.04% of price | 161 | 39/80 (48.8%) | 35/70 | 87/251 | 164/251 (65.3%) |
| C3 signed MA20 distance >= -0.15% | 343 | 64/80 (80.0%) | 58/70 | 221/251 | 30/251 (12.0%) |
| **Both upper-wick and MA20** | **130** | **30/80 (37.5%)** | **25/70** | **75/251** | **176/251 (70.1%)** |
| Prior Oct RSI>=45 + MA20>=-0.15 + ATR%<=0.275 | 305 | 57/80 (71.3%) | 52/70 | 196/251 | 55/251 (21.9%) |

## Direction-aware result for preferred wick + MA20 rule

| Direction | GOOD kept | WEAK kept | BAD kept | BAD rejected |
|---|---:|---:|---:|---:|
| BUY | 13/39 (33.3%) | 6/31 | 23/107 | 84/107 |
| SELL | 17/41 (41.5%) | 19/39 | 52/144 | 92/144 |

**Conclusion: reject promotion of these filters.** In October 29–30 the same combined rule retained all 8 GOOD signals and removed 9/11 BAD signals; in September holdout it rejected **50 of 80 GOOD signals**. Its apparent October strength did not generalize. No live signal logic changed. C3 wick threshold likely overly restrictive; MA20 alone is less destructive but low-selectivity. Absolute RVOL / ASJR profiles remain unvalidated, and ASJR true bid/ask order-flow delta was not measured.

### Next research protocol

1. Document September coverage gaps and evaluate only sessions with expected 5m bar completeness, reducing false absence / early cutoff.
2. Evaluate explanatory metrics by BUY/SELL and time of day with training/holdout split. Don't tune against September and then call September out-of-sample.
3. Test C2-to-C3 *directional changes* in RSI, MA9/20 distance, ASJR B/S zones, relative candle body/wick, and normalized ATR/R. After exploratory tuning, freeze against **another unseen period**.
4. Address hindsight C3/C4 entry timing and fill sequence with 5-minute reconstruction before assessing trading profitability.

Full per-signal CSV: [NQ September holdout results](NQ_2026-09_holdout_frozen_filters.csv).
