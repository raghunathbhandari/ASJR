# Rudra Three-Candle Strategy — Research workspace

## Current implementation — V2.0.0 (2026-10-30)

**Important: the Python module was completely rewritten.** Existing Jupyter calls
`check_signals("INTC", "2026-10-28", "2026-10-28", r=0.10)` and
`show_chart(test)` are preserved, but now use **only the original historical
RTH sweep/reclaim model**. The former experimental breakout execution simulator
was removed. The console must say `LOADED v2.0.0-20261030 |
MODEL=RTH_C2_SWEEP_EXPOST`.

Data is downloaded as 5m Yahoo OHLCV (or use `source_csv=...` for archived data),
converted to New York 09:30–16:00 RTH, then grouped into completed 15m candles.
C2 must be bullish with lower wick longer than body, sweep C1 low and close
above C1 low; C3 volume > C2 volume and C3 close > C2 close.

Green entry reference = **C2 close hypothesis**, red = C2 open initial SL,
purple = 1R/2R/3R *reference levels*, **not filled exits**. C3 volume is not
known at the C2-close hypothesis time. Only ex-post price-touch counts are
shown; stop ordering and executable win rate remain unverified.

The archived September ten-ticker regression was rerun successfully:
**83 setups, 83/75/64 touches at 1R/2R/3R**. Notebook call and chart were
also exercised using archived INTC data. Live Yahoo retrieval for 28 October
has not been verified in this environment.

**Note:** Some older sections below describe superseded experimental versions;
the V2 description above and `three_candle.py` take precedence.

**Primary home:** `main/three_candle/` • Updated 2026-10-30 (UK).

This is an exploratory **signal scanner and hypothetical OHLC backtest**, not a live order executor or validated fee-adjusted strategy.

## Verified historical reproduction (2026-10-30)

The Python module now contains a **separate** `--historical-csv` research mode implementing the archived 2026-10-25 RTH sweep/reclaim setup. Using the archived September 2026 IBKR 5m files on `rudra-data-results`, its regression test reproduces **83 historical setups** and same-session price-touch counts **83 / 75 / 64** at 1R / 2R / 3R. This is **not** an executed-trade win rate. Current default Yahoo 15m breakout mode remains an independent experiment.

```bash
python three_candle/three_candle.py --start 2026-09-01 --end 2026-09-30 --historical-csv /path/to/INTC_5m.csv
ASJR_5M_DIR=/path/to/Backtesting/BacktestData/IBKR/MarketData/5m python -m unittest discover -s three_candle -p test_historical_reproduction.py
```

The historical mode anchors each 15m RTH candle to 09:30 ET, aggregates exact groups of three 5m candles, resets at the US session boundary, and displays UK times. `historical_target_touches` scans future highs **from C3 onward through that day's close**, irrespective of earlier stop touches. It intentionally makes no trade execution/P&L claim.

## Start here

- [STRATEGY.md](STRATEGY.md) — side-by-side comparison of the original historical strategy and the **different** current Python implementation, data provenance, and outcome limitations.
- [AI_SESSION_HANDOFF.md](AI_SESSION_HANDOFF.md) — reproducibility notes, prior research, next tests, and user chart preferences.
- [three_candle.py](three_candle.py) — current executable signal/backtest logic.
- [test_three_candle.ipynb](test_three_candle.ipynb) — interactive notebook.

**Warning:** historical 83/83 1R touches in September were **not 83 verified closed trade wins**. The original research requires C1 liquidity sweep/reclaim, C3 close confirmation, C2-close hypothetical entry, and 1R trailing; the current Python script does not implement those identical rules. Do not merge their win rates. See [STRATEGY.md](STRATEGY.md).

## Install

```bash
python -m pip install yfinance pandas matplotlib ipykernel notebook
```

## Current Python implementation

Defaults: INTC, Yahoo native 15m with extended sessions, C2 bullish, **either** C2 wick > body, C3 volume > C2 volume, no C1 sweep condition. Optional `--require-breakout` requires C3 high > C2 high. Setup known only when C3 has completed.

A hypothetical C2-high stop-buy is eligible **after** C3. Initial SL=C2 open. Step size `R=max(C2 high − C2 open, entry×r_pct/100)` (default `r_pct=0.10`). At 2R by default, the trailing stop moves to that level **for the next bar**, and advances at later whole-R milestones. No fixed TP order. Same-bar OHLC path is unknown; entry and stop may both appear in the same bar. No modeled commissions, slippage, gaps, partial fills, or position/capital limits. Multiple signals are tested independently, potentially overlapping.

### Commands (from repository root)

```bash
python three_candle/three_candle.py --start 2026-10-29 --end 2026-10-30 --symbol INTC --limit 3
python three_candle/three_candle.py --start 2026-10-01 --end 2026-10-30 --symbol INTC --no-charts
python three_candle/three_candle.py --start 2026-10-29 --end 2026-10-30 --symbol INTC --r-pct 0.20 --target-r 2 --no-charts
```

Dates are inclusive UK calendar dates, and output labels convert to `Europe/London`. Yahoo 15m history is usually limited to approximately the recent 60 days; availability and missing extended-hours volume must be validated. Running a very short period may leave most trades OPEN/NO_FILL, so the completed-trade win rate can be misleading. A `--target-r 1` run changes the stop progression but does **not** reproduce the older C2-close strategy.

## Visual conventions

Entry = **green**; winning TP/trailing exit = **purple**; initial SL and losing exit = **red**. A setup is not an executed fill. Use UK time for all charts and ledgers.

## VPS update

```bash
cd /root/trading/ASJR
git pull --ff-only origin main
```

Research-only changes to the code require a separate validated scenario and documented assumptions. Do not promote preliminary price-touch rates to trading P&L.
