# RudraEMA5 V2 — COHR 5-minute reversal after oversold decline

**Current rules as of 2026-11-27 19:44 UK:** **C2 5%-of-C1 range filter REMOVED.** RSI threshold raised from `<30` to **Wilder RSI(14) <36 at completed C1**. Keep swing-down >=2%. Read-only strategy research; no live order placement.

## Data
- Ticker: **COHR**, IBKR Gateway historical `TRADES`, `useRTH=False` (available extended hours).
- Raw [5-minute OHLCV CSV](../three_candle/data/ibkr_bridge/research-1795805412345/COHR_2026-11-01_2026-11-27_5min_UTC.csv); IBKR bridge job `research-1795805412345` succeeded with **3,572 bars** and no reported broker errors.
- Analyse data from 2026-11-01 inclusive to **2026-11-27 18:00 UK**, excluding any later bars. Actual first available bar is 2026-11-02 09:00 UTC; 3,564 bars precede cutoff. In November, UK time is GMT/UTC.
- Warm up indicators using all *prior available* bars rather than resetting on each test day. Market closures create real timestamp gaps.

## Current executable-intent LONG rules

1. Use **EMA5 of 5-minute closes**. By the end of C1, `100*(EMA5(C1)/EMA5(3 bars earlier) - 1) <= -0.15` (0.15% decline over 15 minutes). Require those four bars to have contiguous 5-minute timestamps.
2. **Filter 1 (still active):** price declined at least **2%** from the highest high of the **24 completed bars preceding C1** to **C1 low**. This is an operational two-hour rolling-high proxy, not yet a formal pivot/swing definition.
3. **C1:** complete 5-minute candle; entire high-to-low range below its completed EMA5, with `C1_high < EMA5(C1)`. **RSI filter:** Wilder RSI(14) on 5-minute closes is strictly **below 36 at C1 close**; RSI equal to 36 fails.
4. **C2:** must be the immediately following 5-minute candle. Buy intrabar if price trades at or above `max(ceil_to_cent(C1_close*1.002), ceil_to_cent(C1_high+$0.02))`. The two price conditions are retained from user instructions; if the candle gaps above the threshold, simulate entry at C2 open. Do NOT wait for C2 close or use final C2 RSI/low to decide whether entry occurred.
5. **Initial stop:** 1% below fill price (1R). If price reaches entry +1%, do NOT take full profit; retain full position, activate trailing stop at **0.2% below highest price attained**. Move trail only upwards.
6. **Positions:** at most one at a time. A 25-Nov day-only replay closes any remaining position at the last 5-minute close to make day comparisons; all simulated fills are before commissions, spread/slippage and borrow costs.

**Removed filter:** The previous `C2_low >= C1_high - 0.05*(C1_high-C1_low)` constraint is **not checked anywhere in V2**. Its full-candle definition was too restrictive and risked look-ahead. Historical V1 screening remains in [the archived 25 November report](results/COHR_2026-11-25_5min_filter_comparison.md), not the active strategy.

## V2 preliminary backtest comparisons (25 Nov 2026)

| RSI at C1 (with >=2% swing) | Trades | Winning | Losing | Gross summed R |
|---|---:|---:|---:|---:|
| Below 30 | 1 | 0 | 1 | -1.00R |
| **Below 36 (active V2)** | **4** | **3** | **1** | **+2.66078R** |
| Below 40 (comparison only) | 7 | 4 | 3 | +1.55517R |

For 27 Nov up to **18:00 UK**, RSI below 36 produces **1 trade, 0 wins, -1.00R**. A favorable single day does **not** validate an RSI threshold; avoid hindsight optimization, test across more dates and tick/1m sequencing.

Detailed [V2 Nov 25/27 trade log and assumptions](results/COHR_2026-11-25_RSI36_V2.md).

## Reproducible Python

```bash
python RudraEMA5/filter_audit.py --date 2026-11-25 --rsi-threshold 36
python RudraEMA5/backtest.py --date 2026-11-25 --rsi-threshold 36
python RudraEMA5/backtest.py --date 2026-11-25 --rsi-threshold 30
python RudraEMA5/backtest.py --date 2026-11-27 --rsi-threshold 36
```

[Filter audit source](filter_audit.py) and [backtest source](backtest.py). Both read the GitHub-exported CSV in its original path; they do not download new data or place orders.

### Backtest limitations

Historical 5-minute OHLC does not reveal the exact order of highs and lows. An initial stop reached within an entry bar is assumed hit conservatively. A currently active stop is checked before any same-bar trail update. A new trail from that candle's high may execute in that same candle only if its *close* crosses that trail. Other ambiguous intrabar movement remains unverified. Stops can slip across gaps. No trading fees, spread, commissions or market impact are modeled. Results are research hypotheses, not verified live performance.
