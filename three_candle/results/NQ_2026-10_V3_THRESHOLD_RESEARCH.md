# Rudra ThreeCandl-V3 — October 2026 Threshold Research

Source: `three_candle/results/NQ_2026-10_V3_MASTER_ALL_SIGNALS.csv` (311 NQ V3 core candidates, 305 evaluable independent trial positions). Generated 2026-11-03.

## Important methodology
- NQ risk 1R = 0.20% of first following 5-minute bar open, 0.25-point tick-rounded stop/target, moving stop to BE at +1R, +1R at +2R, TP +3R. No fees/slippage.
- Enter at next 5-minute open after C3 (not the V3's potential intrabar C2-body break entry).
- Independent-signal analysis overlaps positions. Daily-limited illustration permits one position at a time, max 4/day, stop after 2 consecutive losses. These are NOT account returns.
- First/second halves were used as a *descriptive stability check*, not true unseen holdout because the whole month was inspected to select ranges.
- The original six filters remain unchanged; all new thresholds below are hypotheses.

## Independent signals: performance

| Subset | Count | Positive | Breakeven | Negative | TP3R | Net R | Average R |
|---|---:|---:|---:|---:|---:|---:|---:|
| All core | 305 | 83 | 67 | 155 | 32 | -11.76 | -0.039 |
| SELL | 157 | 49 | 38 | 70 | 19 | +16.56 | +0.105 |
| BUY | 148 | 34 | 29 | 85 | 13 | -28.32 | -0.191 |
| All 6 V3 filters | 14 | 1 | 1 | 12 | 1 | -8.03 | -0.573 |
| C3 body 0.05–0.10% | 85 | 31 | 16 | 38 | 13 | +17.14 | +0.202 |
| C3 body >= 0.10% | 106 | 17 | 28 | 61 | 6 | -30.53 | -0.288 |
| C2 RVOL20 0.5–0.8 | 97 | 34 | 20 | 43 | 11 | +8.11 | +0.084 |
| SELL & C3 body 0.05–0.10% | 52 | 19 | 11 | 22 | 9 | +15.29 | +0.294 |
| SELL & C3 body <0.10% | 108 | 40 | 25 | 43 | 16 | +26.23 | +0.243 |
| BUY RSI14 <25 | 7 | 2 | 2 | 3 | 2 | +3.00 | +0.429 |

## Chronological halves (independent positions; average R)

| Rule | Oct 1-15 | Oct 16-30 |
|---|---:|---:|
| All core | +0.018 (157) | -0.099 (148) |
| SELL | +0.129 (79) | +0.082 (78) |
| RVOL20 0.5–0.8 | +0.056 (49) | +0.112 (48) |
| C3 body 0.05–0.10% | +0.070 (41) | +0.325 (44) |
| SELL & C3 body 0.05–0.10% | +0.204 (26) | +0.384 (26) |
| All 6 V3 | -0.254 (8) | -1.000 (6) |

## Position/daily-limited hypothetical replay

| Rule | Taken | Positive | BE | Negative | TP3 | Net R | Average R |
|---|---:|---:|---:|---:|---:|---:|---:|
| All core | 73 | 24 | 15 | 34 | 12 | +13.91 | +0.191 |
| SELL | 76 | 25 | 18 | 33 | 11 | +14.65 | +0.193 |
| SELL & C3 body <0.10% | 64 | 23 | 15 | 26 | 9 | +14.16 | +0.221 |
| SELL & C3 body 0.05–0.10% | 44 | 18 | 8 | 18 | 9 | +19.06 | +0.433 |
| RVOL20 0.5–0.8 | 60 | 20 | 14 | 26 | 8 | +8.79 | +0.146 |
| Six-filter pass | 14 | 1 | 1 | 12 | 1 | -8.03 | -0.573 |

Caveat: these rule-specific selections choose different positions and exclude skipped/overlapping signals. The first position after C3 is assumed entered, without full intrabar execution model.

## Decision

**Research priority 1:** test SELL with C3 body between 0.05% and 0.10% as a provisional *alternative candidate profile*, alongside the original six flags, NOT as a replacement to core matching or a live trading rule. Small C3 bodies were more promising than larger ones under the tested setup.

**Research priority 2:** separately track C2 RVOL20 0.50–0.80, which showed a moderately positive mean R across both October halves; do not require C2 RVOL >=1.2 globally.

**Research priority 3:** retain an extreme-oversold BUY research profile but don't present it as validated. BUY RSI <25 had 7 independent signals (+3R aggregate), and only one matched the originally overly strict multi-condition profile.

**Next:** repeat all locked hypotheses unchanged on September 2026 (or later untouched data) before enabling hard Pass Candidate thresholds. Verify 5-minute intrabar C3 execution, and include commission/slippage before production deployment.
