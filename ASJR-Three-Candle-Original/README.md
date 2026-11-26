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

## R-wise aggregate performance — September 2026

The same 83 historical candidate setups are evaluated at each target; rows are alternative target levels, not 249 separate trades.

| Target | Total candidate trades | Target reached | Not reached | Historical target-touch rate (win-rate proxy only) | Nominal gain % (target credits only) | Verified executed win rate | Verified net gain % |
|---|---:|---:|---:|---:|---:|---|---|
| 1R | 83 | 83 | 0 | 100.0% | +8.30% | Not established | Not established |
| 2R | 83 | 75 | 8 | 90.4% | +15.00% | Not established | Not established |
| 3R | 83 | 64 | 19 | 77.1% | +19.20% | Not established | Not established |

Nominal gain % is the archived illustrative sum of target-hit credits: 83 × 0.10%, 75 × 0.20%, and 64 × 0.30%. This assumes the minimum R step for illustration, ignores losses, earlier stops, C3 look-ahead, larger actual R steps, fees, slippage, overlap and capital allocation. It is NOT a net return, realized trailing-stop gain or account return. Target misses are not verified losses; target touches are not verified wins. The three rows must not be added together. Actual executable trade count, win rate and gain % require a chronological causal replay.

## October reference

INTC selected examples on 2, 6 and 9 October later touched 2R, 9R and 4R respectively. Same-5m initial stop ambiguity and C3 look-ahead prevent a verified profit claim. Full October ten-instrument test was data-ready as of 25 October but not run in that original study.

## Python strategy and tests

- [original_three_candle.py](original_three_candle.py) — standalone original equity C1/C2/C3 research scanner with 1R/2R/3R per-ticker counts.
- [test_original_three_candle.py](test_original_three_candle.py) — small synthetic tests for detection and incomplete 5-minute bars.
- [September_2026_Results.csv](September_2026_Results.csv) — archived benchmark; not a new run.

Requires Python 3 and pandas. From repository root, point to the archived IBKR 5-minute CSV directory from branch `rudra-data-results`:

```bash
python -m pip install pandas
python ASJR-Three-Candle-Original/original_three_candle.py \
  --data-dir /path/to/Backtesting/BacktestData/IBKR/MarketData/5m \
  --start 2026-09-01 --end 2026-09-30 \
  --check-archived-september \
  --save-dir /tmp/asjr-original-three-candle

python -m unittest discover \
  -s ASJR-Three-Candle-Original -p 'test_original_three_candle.py'
```

Full replay requires actual archived OHLCV files. The September regression option checks all ten ticker counts against 83/83/75/64 and exits with an error if different. Tests use synthetic data only. **The newly created standalone file has not yet completed an independently verified September historical replay.**

Nominal target-gain percentage is a sum of individual target-price movements at each setup's actual R distance, not executed net P&L or account returns. The previously reported +8.30%, +15.00%, +19.20% are minimum-step illustrations rather than booked results. C3 look-ahead, stop ordering, trading costs and overlapping positions still require a causal replay.

## Materials

- [Frozen original strategy specification](STRATEGY.md)
- [September ticker results CSV](September_2026_Results.csv)
- [Original data and results index](DATA_AND_RESULTS_INDEX.md)
- [Original research handoff](AI_SESSION_HANDOFF.md)
- [Refinement plan](REFINEMENT.md)
- [Historical regression](../three_candle/test_historical_reproduction.py) and [historical scanner](../three_candle/three_candle.py) (shared existing files; not changed).
- [Original archive branch](https://github.com/raghunathbhandari/ASJR/tree/rudra-data-results/Rudra-Three-Candle)

Do not modify the frozen baseline or mix results with subsequent variants. New experiments must have separate versions and results.
