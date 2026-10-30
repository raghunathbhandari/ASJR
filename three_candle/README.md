# Rudra Three-Candle — NQ=F 15-minute research

Readable, modular signal discovery. **This is not a profit backtest or an order executor.**

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

This starter focuses on **long** setups and does not implement actual trade
fills, R-multiple exits, trailing stops, commissions, or shorts. Candle 2
open is printed as a *reference* stop, not a validated fill/stop placement.
The user should visually verify and adjust each filter before adding execution
logic. In particular, a Candle 2 close entry cannot use future Candle 3 volume.

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
