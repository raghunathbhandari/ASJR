# Rudra ThreeCandl-V3 — September + October raw candidate audit and broad-filter research

Prepared 2026-11-03, from IBKR NQZ2026 5m September and October CSVs and retained original V3 15m candidate/result files.

## Files
- Complete **584-row** unified master: `three_candle/results/NQ_2026-09_10_V3_RAW_CANDIDATES_UNIFIED_MASTER.csv`
- September raw 5m: `three_candle/data/NQZ2026_IBKR_5m_2026-09.csv` (6,024 rows)
- October raw 5m: `three_candle/data/NQZ2026_IBKR_5m_2026-10.csv` (6,048 rows)
- September research: `three_candle/results/NQ_2026-09_V3_FULL_METRICS_MASTER.csv` (273 candidate rows)
- October research: `three_candle/results/NQ_2026-10_V3_MASTER_ALL_SIGNALS.csv` (311 rows)

**Preserve ALL 584 core candidate rows regardless of filter outcome.** Unified file normalizes six filter values, risk and direction; carries raw bar-quality flags and independent trading outcomes. This is a research master, not a live signal file.

## Data audit

- 12,072 unique 5m records, no duplicate timestamps, no invalid OHLC ordering, and 4,024 complete aligned 15m bars.
- 43 expected/non-contiguous timestamp gaps across both months (34 sixty-five-minute gaps, 8 weekend gaps, one holiday-shortened 305-minute gap). Verify exchange holiday calendar and vendor coverage before execution claims.
- September has **459 zero-volume 5m bars** and **792 flat 5m bars**; October has none of these in the combined files.
- **49 September core candidates** have at least one zero-volume 5m bar in their C2 or C3; **75 across both months** have C2 or C3 15m volume <=20. These remain in the master with flags, not silently discarded.
- The source master C2 times can precede C3's local date; the Oct 23 cross-midnight C2 (Oct 22 23:45 UK) was explicitly resolved from its correct previous-day 5m bars.
- Indicator warmup for September is incomplete because August IBKR CSV was not available. Longer EMA readings near start of month are provisional.

## Independent per-candidate backtest

Entries at next 5-minute open after confirmed C3, NQ initial 1R=0.20% of entry, 3R target, trailing stops. No commissions/slippage; candidates may overlap; **sum of R is not an account return**. OHLC intrabar order and gap fills can bias results. This is a retrospective study and does not validate prospective win rate.

| Group | Sep candidates | Sep +3R | Sep positive exits | Sep mean R | Oct candidates | Oct +3R | Oct positive exits | Oct mean R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| All raw core | 273 | 38 | 94/271 | +0.159 | 311 | 32 | 83/305 | -0.039 |
| C3 body <0.10% (BUY & SELL) | 214 | 34 | 82/212 | +0.266 | 204 | 26 | 66/200 | +0.094 |
| C3 body 0.05–0.10% (BUY & SELL) | 72 | 10 | 27/71 | +0.262 | 84 | 13 | 31/83 | +0.231 |
| C3 body <0.10% + RVOL20 0.5–1.2 | 86 | 19 | 41/86 | +0.529 | 113 | 15 | 45/113 | +0.160 |
| C3 body <0.10% + wick/body >=0.5 | 125 | 23 | 49/124 | +0.348 | 127 | 20 | 47/123 | +0.266 |
| C3 body <0.10% + wick/body 1–10 | 72 | 14 | 30/71 | +0.441 | 83 | 16 | 32/81 | +0.383 |
| Original six filters pass | 10 | 2 | 3/10 | +0.190 | 14 | 1 | 1/14 | -0.573 |
| SELL + Body 0.05–0.10% + Wick4to10 | 5 | 0 | 1/5 | -0.404 | 7 | 3 | 6/7 | +1.679 |

## Evidence and recommendations

1. **Highest-coverage common candidate flag:** C3 body <0.10%, BOTH BUY and SELL. Retains **418 of 584** signals (71.6%) and **60 of 70** historical 3R hits (85.7%). Positive exit rate **148/412=35.9%**, mean **+0.182R**, compared with all-core 177/576=30.7%, mean +0.055R.
2. **Moderate extra-confirmation exploratory profile:** body <0.10% plus C2 RVOL20 0.5–1.2. Retains **199 candidates**, 34 of 70 3R target hits, mean +0.320R; positive exits 86/199=43.2%. The lower coverage is a material tradeoff.
3. **Wick alternative:** body <0.10% + directional wick/body 1–10 gives **155 candidates**, 30 of 70 3R hits, mean +0.410R, positive exits 62/152=40.8%. Its zero-body cases and wick/body numerical sensitivity need checking. These are not validated, deployable rules.
4. **Do not require SELL-only**: September BUY core had 23 TP3R; October BUY and SELL differ in month profitability. Keep direction as a separate analysis column.
5. **Do not require all six original V3 checks**: 24 candidates in both months and only 3 of 70 TP3R hits; note F3/SR room logic and daily room differ conceptually from actual price movement, with previous highs/lows not always valid stopping barriers.
6. **Separate liquidity-quality flags from price pattern rules**: zero-volume C2/C3 may indicate stale data or genuine no trading. Flag and verify, do not hide raw candidates.
7. **Do not fit thresholds again to the same two months**. Test September/October rules unchanged on a future untouched sample, preferably a new instrument or November (as data accumulates). Retest with one position at a time, 4 trades/day cap, conservative intrabar stop execution, fees/slippage.

## Master file columns
Month, original signal ID, C1/C2/C3 UK time, BUY/SELL, core and variant flags, F3-F8 pass/raw metrics, C3 body, RSI, EMA20 and EMA200 distances, BB width, ATR, VWAP distance, C2/C3 15m volumes and zero-volume/flat-bar checks, simulated R outcome, exit reason/time, and provenance.

**Status: research only.** No original V3 or experimental filter was changed by this report.
