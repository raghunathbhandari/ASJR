# Rudra ThreeCandl-V3withBodySize — NQ October 2026

## Variant definition
- Core: unchanged V3 15-minute C1/C2/C3 BUY/SELL scanner.
- `V3withBodySize_pass`: **SELL** candidate with **0.05% <= abs(C3.Close - C3.Open) / C3.Close * 100 < 0.10%**.
- Original `all_filters_pass` (six V3 filters) remains separate and unchanged.
- NQ 1R = 0.20% of simulated entry, initial stop -1R, step trailing to break even at +1R and +1R at +2R, TP at +3R. Simulated entry is the following 5-minute open after C3. Stop/target rounded to 0.25 point.
- This replay uses existing October master rows; C3_body_pct in that CSV is rounded to 3 decimal places. The newly committed Python method uses full-precision OHLC, so boundaries should be revalidated with an end-to-end Python run. The October CSV count is **provisional** until then.

## All October core candidates, independent hypothetical positions

| Subset | Core/selected | Evaluable | Win | BE | Loss | Hit +3R | Net R | Avg R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V3 all core | 311 | 305 | 83 | 67 | 155 | 32 | -11.7547 | -0.0385 |
| V3 original all six filters pass | 14 | 14 | 1 | 1 | 12 | 1 | -8.0254 | -0.5732 |
| **V3withBodySize** | **53** | **52** | **19** | **11** | **22** | **9** | **+15.2859** | **+0.2940** |

- BodySize positive-exit rate = 19/52 = 36.54%. Non-loss rate = 30/52 = 57.69%.
- Exactly 1 selected candidate had no evaluable trade.
- Selected candidates occurred on 20 October dates.
- The reported sum of R is **not an account return**. Independent candidates can overlap, and there is no per-trade fee or slippage allowance.

## Prior daily-limit replay (approximate position scheduling)

Applying one open position at a time, max four per day, stop after two consecutive losses, to SELL candidates with C3 body 0.05–0.10% produced 44 trades: 18 positive, 8 BE, 18 negative, +19.06R combined, +0.433R average, before fees. This is a replay of the already-computed per-candidate outcomes, NOT independently replayed live fills; daily-position scheduling and UTC/UK session boundaries require further validation.

## Month split (unconstrained positions)
- Oct 1–15: 26 evaluable SELL C3 0.05–0.10% candidates, +0.204R average.
- Oct 16–30: 26 candidates, +0.384R average.
- This is an *in-sample stability comparison*, not out-of-sample proof.

## Known limitations
1. Only October was used for threshold selection; must test September with frozen rule next.
2. The C3 entry-at-next-5m-open method may differ from an intrabar C2-body-break entry.
3. Stops/targets assume bar-based high-low sequencing and ideal fills, no commission/slippage.
4. Current instrument code changes were not executed through the VPS Python notebook; GitHub contents were updated and the master dataset was independently analysed.
5. Trading selection with daily limits should be repeated from raw candles, including gap/exchange-session handling.
6. Keep original V3 results and columns intact to allow direct comparisons.

## Files
- `three_candle/results/NQ_2026-10_V3_MASTER_ALL_SIGNALS.csv`
- `three_candle/results/NQ_2026-10_V3withBodySize_MASTER.csv`
- `three_candle/three_candle_learing.py`
