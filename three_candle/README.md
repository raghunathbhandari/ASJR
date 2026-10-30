# Rudra Three-Candle — NQ=F 15-minute research

Readable, modular signal discovery and an exploratory **2R stepped-trailing backtest**.
This is not an order executor or a fee-adjusted performance estimate.

## Install

```bash
python -m pip install yfinance pandas matplotlib ipykernel notebook
```

## Run one UK calendar day

```bash
python three_candle/three_candle.py --start 2026-10-29 --end 2026-10-29 --limit 3
```

## Run one month

```bash
python three_candle/three_candle.py --start 2026-10-01 --end 2026-10-30 --no-charts
```

Open `three_candle/test_three_candle.ipynb` for visual step-by-step testing.

## Definitions (initial editable research hypothesis)

1. Candle 2 bullish (`Close > Open`).
2. At least one Candle 2 wick is longer than its absolute body.
3. Candle 3 volume strictly exceeds Candle 2 volume, both valid and nonzero.
4. Optional `--require-breakout`: Candle 3 high exceeds Candle 2 high.

The three candles are consecutive completed 15m NQ=F bars. A setup is
reported at Candle 3 completion, never at Candle 2 completion. The output
prints all three OHLCV rows; `plot_signal` shows surrounding candlesticks.

This starter focuses on **long** setups. The paper entry is a C2-high
stop-buy, eligible only on bars after C3 completes; initial stop is C2 open.
Risk 1R = entry minus C2 open. At 2R reached, stop moves to +2R on the **next**
bar; at 3R, to +3R; at 4R, to +4R, etc. There is no fixed profit-taking
order. On a candle that both reaches the existing stop and a new higher R
milestone, the stop wins (conservative OHLC assumption). Results are WIN (exit
at >=2R), LOSS, OPEN, NO_FILL or INVALID. The printed win rate divides wins
by *closed* wins plus losses, excluding all unresolved signals. A single-day
dataset typically leaves trades unresolved; use more following dates for an
honest summary. Signals may overlap as independent paper trades.

This does not model fees, slippage, gaps through stops, capital allocation or
short trades. Review individual setups before relying on results. In
particular, a C2 close entry cannot use future C3 volume.

Yahoo Finance may only provide approximately the most recent 60 days of 15m
data. The availability window, missing futures bars, and reported NQ volume
must be checked before drawing conclusions. Overnight sessions are included;
timestamps and date boundaries use `Europe/London` (BST/GMT automatically).

## VPS update

```bash
cd /root/trading/ASJR
git pull --ff-only origin main
```

Run Jupyter from the repository root or insert the `three_candle` folder in
your notebook's Python path as the first notebook cell does.
