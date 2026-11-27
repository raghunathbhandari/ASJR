# RudraEMA5 — 5-minute RSI reversal strategy, V3

**Current research variant:** **V3** (RSI below 36 **and rising at completed C1**). V2 is retained separately for comparison. **No evidence yet of a reliable positive net trading edge across stocks.** No live order placement.

## Frozen entry setup (LONG)

1. **EMA5 slope:** the 5-period exponential moving average of **5-minute closes** declined at least **0.15% over the three completed bars preceding C1**.
2. **Swing:** a decline of at least **2%** from the highest high among **24 bars preceding C1** to C1 low. This is an operational rolling-high proxy, not a formal swing-pivot definition.
3. **C1:** entire high-to-low range is below EMA5 at C1 close: `C1_high < EMA5(C1)`.
4. **RSI14:** Wilder RSI of closing prices at completed C1 must be **strictly below 36**.
5. **V3 reversal filter:** `RSI14(C1) > RSI14(previous completed candle)`. **V2** omits this condition; it does not change other rules.
6. **BUY:** in the next immediate 5-minute candle (C2), when price reaches `max(ceil_to_cent(C1_close*1.002), ceil_to_cent(C1_high+0.02))`. Both breakout requirements are retained. C2's eventual low is NOT consulted before entry.

## Exit / risk

- Initial stop loss **1% below the actual entry price** (1R share-price movement).
- Once price rises **1% above entry**, keep the entire position (no partial or fixed TP); arm a **0.2% trail** below the highest achieved price, ratcheting upwards only.
- Only **one concurrent position**; backtests mark out any open position at the final available candle of each **Europe/London** calendar date.
- Include available extended-hours data (not necessarily liquid or reliably executable).
- **Removed filter:** the former C2 pullback guard of 5% of C1 candle range is *not* part of V2 or V3.
- Trading research only; candles have incomplete intra-bar sequencing, and simulations exclude trading costs.

## Historical research

- **First sample COHR November 2–27:** V2 70 trades, 30 wins, **−4.59R**; V3 23 trades, 14 wins, **+8.64R**. V3 was selected after looking at these results; **in-sample**.
- **Six additional stocks (AAPL, AMD, INTC, NVDA, PLTR, TSLA), September–November 2026 (18 stock-months, 70,272 native five-minute candles):**
  - V2 **405 trades**, 164 wins, **−46.10R gross**.
  - V3 **196 trades**, 89 wins (**45.41%**), **−0.55R gross**.
  - V3 month totals **September +12.12R**, **October −7.82R**, **November −4.85R**.
  - **Main conclusion:** V3 is substantially less negative than V2 but has **no demonstrated net edge** across these other stocks before spreads, commissions, slippage and intrabar order uncertainty.

[Full six-stock research report](results/RudraEMA5_6stocks_3months_RESEARCH_REPORT.md) · [Machine-readable day-by-day ledger](results/RudraEMA5_6stocks_3months_V2_V3.json).

## Dashboard

**[Interactive RudraEMA5 dashboard](https://raghunathbhandari.github.io/ASJR/RudraEMA5/dashboard/)** — select **ticker, month, UK date, timeframe and strategy V2 or V3**, inspect candlesticks/EMA5/RSI14 and simulated BUY/EXIT markers, and download daily results as CSV.

**[Self-contained offline dashboard HTML](dashboard-offline.html)** — GitHub Download raw, then open it locally; no server needed.

[Dashboard instructions](dashboard/README.md) · [Backtest engine](dashboard/engine.js) · [Original V2 Python](backtest.py) · [V3 Python variant](backtest_rsi_rising.py).

### Data provenance

Six-stock historical OHLCV: [Sep](../ASJR-Three-Candle-Original/data/2026-09/), [Oct](../ASJR-Three-Candle-Original/data/2026-10/), [Nov](../ASJR-Three-Candle-Original/data/2026-11/). COHR Nov IBKR bridge [raw CSV](../three_candle/data/ibkr_bridge/research-1795805412345/COHR_2026-11-01_2026-11-27_5min_UTC.csv), clipped at **27 November 2026 18:00 UK**. Manifests reported no errors but `verified_complete: false`; source OHLC consistency checked but original data availability and adjusted prices are not independently certified.

**Important:** 1R means **1% of entry stock price**, NOT necessarily 1% of trading capital. All outcomes are simulated and gross. The 0.2% trailing stop especially requires finer-resolution price data and realistic execution modelling.
