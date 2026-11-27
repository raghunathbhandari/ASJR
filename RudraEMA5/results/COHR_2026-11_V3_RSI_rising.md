# RudraEMA5 V3 — RSI rising at C1, November COHR quick test

**Status: exploratory candidate, NOT an active replacement for V2.** Calculated 27 November 2026 using IBKR 5-minute COHR data, 2–27 November, **cut off at 18:00 UK on the 27th** (3,564 5-minute bars).

## Only rule changed

Keep existing V2 filters and exits exactly as they were. The new AND condition is:

```python
rsi_c1 < 36 and rsi_c1 > rsi_of_bar_before_c1
```

RSI is Wilder RSI(14) of 5-minute closes, read when the C1 candle **completes**. Thus the filter is causally knowable before intrabar C2 entry. C2 full-bar low filter remains removed.

Remaining rules: EMA5 declines >=0.15% over 3 completed bars, C1 high < C1 EMA5; prior 24-bar high-to-C1-low decline >=2%; entry on immediately next C2 at maximum of C1 close+0.2% and C1 high+$0.02 (rounded upward to cents), SL 1% below entry; after 1% favorable price movement, retain full position and activate a 0.2% trail; one open position at a time and close/mark remaining positions at each UK calendar day's last candle. Includes available extended-hours feed.

## Full-month comparison

| Metric | V2 | V3: RSI rising |
|---|---:|---:|
| Number of trades | 70 | 23 |
| Winners | 30 | 14 |
| Losers | 40 | 9 |
| Win rate | 42.8571% | **60.8696%** |
| Profit factor (gross) | 0.8852 | **1.9605** |
| Avg winner | +1.18027R | +1.26032R |
| Avg loser | -1.00000R | -1.00000R |
| Avg trade / expectancy | -0.06560R | **+0.37585R** |
| Gross sum price-based R | **-4.59185R** | **+8.64448R** |
| First half 2–13 November | -0.99192R | +7.81890R |
| Second half 16–27 November | -3.59993R | +0.82558R |

Only **23 V3 trades**. V3 removes 47 simulated V2 entries, including 31 losing trades and 16 winning trades. The number of tradable opportunities also depends on single-position state; the comparison was rerun end-to-end.

## Daily V3 results (days with at least one trade)

| UK date | Trades | Wins | Gross sum R |
|---|---:|---:|---:|
| Nov 2 | 1 | 0 | -1.00000 |
| Nov 4 | 1 | 1 | +1.56386 |
| Nov 5 | 4 | 3 | +5.18405 |
| Nov 10 | 3 | 1 | -0.88822 |
| Nov 11 | 1 | 1 | +1.21014 |
| Nov 13 | 2 | 2 | +1.74907 |
| Nov 16 | 1 | 0 | -1.00000 |
| Nov 18 | 1 | 0 | -1.00000 |
| Nov 19 | 1 | 1 | +0.22801 |
| Nov 20 | 1 | 0 | -1.00000 |
| Nov 23 | 1 | 1 | +0.87405 |
| Nov 24 | 3 | 2 | +1.17189 |
| Nov 25 | 3 | 2 | +1.55162 |
| Nov 27 | 0 | 0 | 0.00000 |

25 Nov V3 executions: C1 09:50 RSI 29.31 (previous RSI 25.09), -1R; C1 14:50 RSI 33.12 (previous 33.03), +1.15369R; C1 15:25 RSI 35.60 (previous 34.68), +1.39793R. Its former profitable 14:00 C1 RSI 31.60 was not rising, so V3 excludes it. On 27 Nov, V3 makes no trade; the previous -1R V2 entry is removed.

## Caveats

**Do not treat +8.64R as a verified real account return or an independently validated edge.** 1R in this experiment is a 1% *stock-price* movement, not 1% of account equity. Strategies were chosen after inspecting November (in-sample, subject to selection bias). 5-minute OHLC cannot verify whether stops/trails and breakout orders were touched before or after other same-bar extremes, especially with a 0.2% trailing stop. Results exclude spread, slippage, fees and extended-hours fill liquidity; realistic net performance may be materially worse. Validate on untouched earlier or future dates at 1-minute/tick resolution before use.

**Research implementation:** [backtest_rsi_rising.py](../backtest_rsi_rising.py). The active [V2 dashboard](../dashboard/README.md) remains unchanged.
