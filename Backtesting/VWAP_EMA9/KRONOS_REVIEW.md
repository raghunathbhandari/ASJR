# Kronos signal review

Optional offline research on the existing BUY signal points. Does not enable live alerts or replace the baseline.

Install the official model source outside ASJR and pin the reviewed revision:

```bash
git clone https://github.com/shiyu-coder/Kronos.git ../Kronos
git -C ../Kronos checkout 67b630e67f6a18c9e9be918d9b4337c960db1e9a
python -m pip install -r Backtesting/VWAP_EMA9/requirements_kronos.txt
```

From the ASJR repository root:

```bash
python Backtesting/VWAP_EMA9/kronos_signal_review.py --csv Backtesting/BacktestData/IBKR/MarketData24h/5m/MU_5m.csv --kronos-root ../Kronos --month 2026-09 --output Backtesting/VWAP_EMA9/research_results/kronos_2026_09
```

Model weights download on first run. CPU supported; pass `--device cuda:0` for compatible GPU. Only load `--features` pickles you generated and trust; CSV is the normal input route.

Entry: completed close-cross above EMA9 or first qualifying of the next two candles; above VWAP and EMA9; both five-point ATR14-scaled angles 15–65°; net five-point price change >0.20%. One position and one entry per cross. Exit at completed close <= EMA9 × 1.0001 or RTH end. No gap/pullback or oscillator filter.

Forecast: 128 past 24h OHLC points, five separately seeded paths, next three 5-minute candles. No volume input. At least three paths must end >0.10% above entry and every predicted close must stay above recursively projected EMA9 plus 0.01%. Fixed baseline trades are vetoed; rejected trades do not generate replacements. Forecast votes are not calibrated probabilities. Candle body/wick measurements are exported as descriptions, not extra rules.

September test: baseline 19 trades, 9 winners, 10 losers, 47.37% success, +1.1548% gross compounded. Kronos gate rejected all 19, including all winners. This gate is unsuitable as tested; baseline remains unchanged. Exact TradingView alignment is unresolved (continuous 24h EMA9, provisional midnight UTC VWAP). Signal-close fills and illustrative 0.10% roundtrip cost. No untouched holdout or model-training-overlap audit.

Outputs: signal_review.csv and summary.json. Model and tokenizer revisions are pinned in the script. Input-cutoff/prefix checks passed; original baseline count reproduced.
