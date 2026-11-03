# ThreeCandle relax mode v1 — MNQ 10-point SL / 20-point TP backtest

Date: 2026-11-03. 1 MNQ = $2/NQ index point. Initial stop 10 points = $20 planned loss; target 20 points = $40 planned gross gain; 1R=10 points, target=2R. Trailing stop moves to breakeven after +10 favourable points.

## Outputs
- `three_candle/results/ThreeCandle_relax_mode_v1_10SL_20TP_2026-09_10_ALL_SIGNALS.csv` — 584 rows with raw candle-level re-simulation and profile flags.
- `three_candle/results/ThreeCandle_relax_mode_v1_10SL_20TP_2026-09_10_SUMMARY.csv` — profile results, each month and combined, both independent and position-capped.
- `three_candle/three_candle_relax_mode_v1.py` — risk constants updated to 10-point SL, 20-point TP and 1 MNQ multiplier. **This script is a CSV profile flagger, not the re-simulation engine.** Legacy 0.20%-risk 3R backtests remain separate.

## Price-path replay method
Read raw IBKR NQZ2026 September/October 5m OHLCV, enter at the next 5m candle OPEN after 15m C3 has completed; stop at 10 NQ points, take profit at 20, move SL to BE after +10 favourable. Stop-first on intra-5m stop/target ambiguity. If a later 5m candle opens beyond the active stop, model stop-market fill at worse OPEN. Target limit fills at target even on favourable gap. Flatten at final 5m candle of UK calendar date, or prior candle at an unexpected data gap. No actual broker execution, fees, spread, commissions or order-queue effects. 
One-position replay: sort signal entries, one active at once, max four/day and stop after two consecutive losses per UK day. Other profile's choices change which signals trade, so replay results cannot be compared by independent R sums. Equity drawdown uses cumulative realized points only, not intratrade floating equity.
**Caveat:** Entry at next 5m open after C3 is a different assumption from an order triggered at C2 body crossing within C3. This test models that fixed entry scheme. Model fills remain hypothetical.

## Capped replay results (1 MNQ)
| Profile | Sep trades | Sep net NQ points | Oct trades | Oct net NQ points | Combined trades | Combined net NQ points | Combined gross USD before fees |
|---|---:|---:|---:|---:|---:|---:|---:|
| No filter raw core | 63 | -117.75 | 69 | -29.25 | 132 | -147.00 | -$294.00 |
| Body <0.10% broad | 62 | -227.50 | 70 | -0.25 | 132 | -227.75 | -$455.50 |
| Body <0.10%; wick>=0.25; RVOL>=0.3 | 53 | -314.75 | 64 | -74.50 | 117 | -389.25 | -$778.50 |
| Body <0.10%; wick>=0.5; RVOL>=0.5 | 55 | -220.75 | 63 | +35.50 | 118 | -185.25 | -$370.50 |
| Body <0.10%; wick>=1, <10 | 52 | -64.25 | 59 | +9.50 | 111 | -54.75 | -$109.50 |

## Selected metrics, both months independent-signal replay (not executable portfolio)
| Profile | Signals evaluated | TP20 hits | Mean R | Net NQ points |
|---|---:|---:|---:|---:|
| Raw | 576 | 140 | -0.131 | -755.25 |
| Broad | 412 | 104 | -0.086 | -355.50 |
| Balanced | 269 | 63 | -0.137 | -367.25 |
| Quality | 198 | 46 | -0.131 | -259.50 |
| Wick 1–10 | 152 | 39 | -0.053 | -81.00 |

## Stop-loss realism
- The 10-point SL is a **planned initial stop distance**, NOT a guarantee of $20 maximum realized risk. In September the 5m data has overnight discontinuities and some gap-through-stop fills.
- The worst modeled raw signal loss was **-37.50 NQ points (-$75 per 1 MNQ)**; this is -3.75R.
- **26** independent raw September+October trades lost more than 10 points, all in September; **zero** in October. Check live tick data and exchange session data before interpreting this as a reliable real-world fill distribution.
- With target 20, stop 10, breakeven trailing, a basic 2:1 payout model needs >33.3% wins if all other outcomes are exactly +2R or -1R and costs are zero. Real gap slippage, BE exits and EOD outcomes alter that condition.
- On this exact replay, all 5 capped profile variants lost money combined across both months, before fees.

## Decision
Do **not** claim previous 60-point-stop gains with the new 10-point SL. Do not enable live execution. A new entry technique and execution/volatility filter would be needed before a credible positive expectancy claim. Preserve all 584 rows and separate profile flags. Further tweaks on Sep/Oct are in-sample and prone to overfitting.
