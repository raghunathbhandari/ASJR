# Rudra Three-Candle Strategy — Research workspace

**Primary home:** `main/three_candle/` • Updated 2026-10-30 (UK).

This is an exploratory **signal scanner and hypothetical OHLC backtest**, not a live order executor or validated fee-adjusted strategy.

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
