# RudraEMA5 — Interactive November 2026 Dashboard

The dashboard is a static HTML/JavaScript research app. It has **no order placement, no paid market-data API, and no external charting libraries**. All 3,564 accepted COHR 5m bars from the IBKR export are frozen into `data.js`; the latest historical candle is **27 November 2026, 17:55 GMT**.

## Open the dashboard

- **Single-file offline:** [Download the self-contained `dashboard-offline.html`](../dashboard-offline.html) using GitHub's **Raw / Download raw file** control, then open the saved HTML in Chrome, Edge, or another modern browser. The market data is embedded. This does not require GitHub Pages, Wi-Fi, Python or a server.
- **GitHub Pages (when enabled and deployed):** https://raghunathbhandari.github.io/ASJR/RudraEMA5/dashboard/
- **Editable site source:** [index.html](index.html), [app.js](app.js) and [data.js](data.js) all live in this directory.

**If the Pages link does not load:** In the repository's **Settings → Pages → Build and deployment**, select **GitHub Actions** as the deployment source; then open the [RudraEMA5 Dashboard Pages workflow](../../.github/workflows/rudraema5-dashboard.yml) under Actions and manually **Run workflow** if needed. The site URL is not guaranteed available until GitHub shows a successful deployment. The offline HTML is available immediately from the repo without Pages.

## What you can do

- Select **any UK date from 1 to 27 November 2026**, click a day in the full month table or click its performance bar.
- Switch the **strategy timeframe** between **5-minute original data, 15-minute, 30-minute and 1-hour**. Higher timeframes are built only from **complete** 5m source blocks (3, 6 or 12 bars per candle). Indicators and entries are **recomputed** on that timeframe; this is not just a visual zoom. Higher-timeframe simulations have greater intrabar path ambiguity.
- Change **RSI14 threshold** (default <36), **minimum swing-down** (default >=2%) and **EMA5 drop over three bars** (default >=0.15%). The entire month and the selected day's trade log update together. **Reset V2** restores the frozen baseline settings.
- View price **candlesticks + EMA5 + RSI14 pane**, eligible **C1 diamonds**, **BUY triangles**, **EXIT circles**, entry/initial-stop bands and simulated ratcheting stop plot.
- **Mouse wheel zoom**, drag to pan, hover to inspect candle data.
- Export a **date-by-date November results CSV** for the selected timeframe/parameter settings.

## Baseline sanity check (5m, RSI<36, 2% swing, 0.15% EMA slope)

For November 1–27, truncated at 18:00 UK on the 27th:

| Metric | Value |
|---|---:|
| Native 5m IBKR bars | 3,564 |
| UK dates containing any candles (including partial Saturdays and holiday spillover) | 23 |
| Trades | 70 |
| Winning trades | 30 |
| Losing trades | 40 |
| Win rate | 42.86% |
| Summed gross R | **−4.59185R** |
| Full-allocation price-return compounding illustration | **−4.91033%** |
| 25 Nov | 4 trades · 3 winners · +2.66078R |
| 27 Nov (up to 18:00 UK) | 1 trade · 0 winners · −1.00000R |

The independent [November 5m trade ledger](../results/COHR_2026-11_V2_5min_daily.json) is stored in the repository. The dashboard checks its own baseline trade count and summed R against that ledger's totals at startup.

## Rules and limitations

Active rules as of 27 Nov 2026: EMA5 down at least 0.15% across three 5m bars, C1 entire range below EMA5, 2% swing-down from preceding 24-bar high, Wilder RSI(14) strictly below 36 at completed C1, next C2 breaks max(C1 close +0.2%, C1 high +$0.02), initial SL = −1%; after +1% price rise arm a 0.2% trail while retaining the full position. C2-low 5%-range filter is **removed**. Maximum one position per day, marked out at final observed close.

**Research caution:** Historic 5m OHLC data does not prove the order of intra-candle highs and lows, or that fills are possible at displayed levels. Already-active stops checked before trail adjustments; entry-bar stop conflicts resolved conservatively. Fees, slippage, bid/ask spread, market impact and thin extended-hours liquidity not modeled. Summed R is a sum of price-based trade returns (1R = 1% share-price movement), **not a portfolio return**. Adjusting RSI thresholds on the same in-sample data can overfit.

For a more reliable comparison, add untouched months, per-trade cost modeling and fine-grained fills before live trading.
