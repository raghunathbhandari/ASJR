# ThreeCandle relax mode v1 — Configuration & September–October rule-set comparison

Date: 2026-11-03. **Name locked: ThreeCandle relax mode v1** (no V3 prefix).

## Purpose
Preserve all valid raw three-candle signals and add non-destructive relaxed mode flags. Keep BUY and SELL. Do not modify existing V3 scanner or `three_candle/test_three_candle.ipynb`.

## Files
- Executable standalone config/flagger: `three_candle/three_candle_relax_mode_v1.py`
- Raw 584 candidates: `three_candle/results/NQ_2026-09_10_V3_RAW_CANDIDATES_UNIFIED_MASTER.csv`
- **All 584 rows + 13 profile flag columns:** `three_candle/results/NQ_2026-09_10_ThreeCandle_relax_mode_v1_ALL_FLAGS.csv`
- **All 13 rules × Sep/Oct/combined:** `three_candle/results/NQ_2026-09_10_ThreeCandle_relax_mode_v1_RULE_COMPARISON.csv`
- Source September/October IBKR 5-minute CSVs remain untouched.

## Run command (from repository root)

```bash
python three_candle/three_candle_relax_mode_v1.py \
  three_candle/results/NQ_2026-09_10_V3_RAW_CANDIDATES_UNIFIED_MASTER.csv \
  --output three_candle/results/NQ_2026-09_10_ThreeCandle_relax_mode_v1_ALL_FLAGS.csv
```

This config is a stand-alone candidate CSV flagger, NOT an IBKR data loader or order execution system. Existing V3 files and notebooks were not changed. September/October flag outputs were produced from identical column predicates on the original master; use this command to locally reproduce. The GitHub code has not been run end-to-end on the user's VPS.

## Fixed risk assumptions
NQ next 5m-open entry after C3 confirmation; initial distance 0.20% = 1R; 3R target, trailing simulation; intrabar ambiguity, overlapping independent signals and costs not resolved. Profits shown as independent theoretical R sums, NOT an executable portfolio P&L.

## Rule-set findings (both directions; no all-6 gate)

| Rule | Sep signals | Oct signals | Both | Combined wins/evaluable | 3R hits of total 70 | Avg R per evaluated signal | Independent sum R |
|---|---:|---:|---:|---:|---:|---:|---:|
| Raw core | 273 | 311 | 584 | 177/576 | 70 | +0.055 | +31.41 |
| **relax_v1: C3 body <0.10%** | 214 | 204 | **418** | **148/412** | **60** | **+0.182** | **+75.11** |
| C3 body <0.08% | 191 | 184 | 375 | 134/369 | 58 | +0.211 | +77.97 |
| C3 body <0.12% | 232 | 229 | 461 | 156/455 | 61 | +0.135 | +61.20 |
| Body <0.10%; wick >=0.25 | 150 | 152 | 302 | 110/297 | 51 | +0.268 | +79.68 |
| Body <0.10%; wick >=0.5 | 125 | 127 | 252 | 96/247 | 43 | +0.307 | +75.90 |
| Body <0.10%; wick 1–10 | 72 | 83 | 155 | 62/152 | 30 | +0.410 | +62.28 |
| Body <0.10%; RVOL >=0.3 | 174 | 187 | 361 | 135/361 | 57 | +0.239 | +86.37 |
| Body <0.10%; RVOL >=0.5 | 155 | 165 | 320 | 121/320 | 50 | +0.246 | +78.66 |
| Body <0.10%; RVOL 0.5–1.2 | 86 | 113 | 199 | 86/199 | 34 | +0.320 | +63.60 |
| **Body <0.10%; wick >=0.25; RVOL >=0.3** | **129** | **140** | **269** | **103/269** | **48** | **+0.314** | **+84.45** |
| **Body <0.10%; wick >=0.5; RVOL >=0.5** | **95** | **103** | **198** | **81/198** | **34** | **+0.350** | **+69.24** |
| Body <0.10%; no zero volume C2/C3 | 172 | 204 | 376 | 131/370 | 56 | +0.192 | +71.17 |

All thresholds were selected or considered on September and October research and are NOT out-of-sample validated.

## Recommendation (explicit separation of priorities)
1. **Default `relax_v1`**: core + C3 body <0.10%, BOTH directions; preserves 418/584 candidate opportunities and 60/70 +3R successes. This is the minimal practical body-based **broad** candidate flag.
2. **Balanced exploratory high-quality shortlist:** body <0.10%, C2 directional wick/body >=0.25, C2 RVOL20 >=0.30; **269 signals**, 48 +3R target hits, Sep avg +0.421R, Oct avg +0.215R.
3. **Higher-selectivity exploratory shortlist:** body <0.10%, C2 wick/body >=0.5, C2 RVOL20 >=0.5; **198 signals**, 34 +3R target hits, Sep avg +0.416R, Oct avg +0.288R.
4. Record existing F3–F8 values, direction, RSI, EMA, BB, VWAP, sessions, 5m data quality. Do NOT use all six as mandatory gates. Preserve every rejected raw row with `NO` profile flag.
5. Historical independent summed R is not sufficient to pick a winner: next test daily caps (max 4/day, stop 2 consecutive losses), overlapping orders, adverse stop fills, costs, data quality, and a genuinely new month without adjusting cutoffs.
6. Do not treat combined historical positive-exit percentage as a prospective win rate. September has 459 zero-volume 5m bars requiring source verification.

No live strategy has been enabled; this is the frozen research config v1 plus alternatives.
