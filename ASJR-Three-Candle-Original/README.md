# ASJR Three-Candle — Original Equity Strategy (v1.1)

Frozen historical research baseline, 25 October 2026 (UK). Archived separately on 26 November 2026 for further refinement. Not the later NQ, MES, Gold or Relax Mode variants.

## Original bullish pattern

- Completed 15-minute regular US session candles formed from three 5-minute OHLCV bars; sum volume.
- C1: reference candle.
- C2: bullish, lower wick greater than body, low below C1 low, close above C1 low.
- C3: volume greater than C2 volume AND close greater than C2 close.
- Original hypothetical entry: C2 close; initial structural stop: C2 open.
- R step = max(C2 close - C2 open, 0.001 × C2 close).
- Intended trailing: lock +1R at +1R, +2R at +2R, etc.; no fixed target cap.
- Completed C3 confirmation cannot be known at C2 close. Original results are ex-post descriptive screens, not executable trade results.

## September 2026 — 10 instruments, IBKR

| Ticker | Signals | Later 1R touch | Later 2R touch | Later 3R touch |
|---|---:|---:|---:|---:|
| AMAT | 5 | 5 | 4 | 3 |
| GOOG | 8 | 8 | 7 | 3 |
| INTC | 11 | 11 | 9 | 8 |
| LRCX | 10 | 10 | 10 | 10 |
| META | 12 | 12 | 12 | 12 |
| MU | 7 | 7 | 7 | 7 |
| NVDA | 9 | 9 | 9 | 7 |
| PLTR | 11 | 11 | 11 | 10 |
| SPY (ETF) | 4 | 4 | 0 | 0 |
| XOM | 6 | 6 | 6 | 4 |
| **Total** | **83** | **83 (100%)** | **75 (90.4%)** | **64 (77.1%)** |

21 regular sessions. Historical screen was reproduced on 30 October 2026. LRCX, META and MU had all observed setups later touch 3R. Price touches do not establish target-before-stop ordering, win rates, P&L or drawdown.

## October reference

INTC selected examples on 2, 6 and 9 October later touched 2R, 9R and 4R respectively. Same-5m initial stop ambiguity and C3 look-ahead prevent a verified profit claim. Full October ten-instrument test was data-ready as of 25 October but not run in that original study.

## Materials

- [Frozen original strategy specification](STRATEGY.md)
- [September ticker results CSV](September_2026_Results.csv)
- [Original data and results index](DATA_AND_RESULTS_INDEX.md)
- [Original research handoff](AI_SESSION_HANDOFF.md)
- [Refinement plan](REFINEMENT.md)
- [Historical regression](../three_candle/test_historical_reproduction.py) and [historical scanner](../three_candle/three_candle.py) (shared existing files; not changed).
- [Original archive branch](https://github.com/raghunathbhandari/ASJR/tree/rudra-data-results/Rudra-Three-Candle)

Do not modify the frozen baseline or mix results with subsequent variants. New experiments must have separate versions and results.
