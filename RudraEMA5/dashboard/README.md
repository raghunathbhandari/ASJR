# RudraEMA5 — Dashboard V3, September–November 2026

Open [live dashboard](https://raghunathbhandari.github.io/ASJR/RudraEMA5/dashboard/) or download the self-contained [offline HTML](../dashboard-offline.html) via GitHub **Download raw**. The live site is built from this folder by [GitHub Pages Actions](../../.github/workflows/rudraema5-dashboard.yml).

## Features

- Choose **COHR** (November only) or six-stock group **AAPL, AMD, INTC, NVDA, PLTR, TSLA** (September, October, November).
- Choose **month**, **UK calendar day**, **V2** (RSI below 36) or **V3** (RSI below 36 and rising), and **5m, 15m, 30m or 1H**.
- Adjust RSI, swing decline and EMA slope thresholds for *selected ticker-month replay*; Reset V3 returns 5-minute reference settings.
- See candlesticks, EMA5, RSI(14), C1 diamonds, BUY/EXIT markers, initial/trailing stops, per-day trades and gross price-based R.
- Compare **all 18 stock-months** at the bottom using frozen baseline V2 vs V3; click a row to load its chart.
- Export selected ticker-month daily results as CSV.

### Frozen 5m reference

Six-stock group: **70,272 five-minute bars**; V2 **405 trades / −46.10R**, V3 **196 trades / −0.55R**. September V3 +12.12R, October −7.82R, November −4.85R. **This is not a demonstrated profitable net edge.**

COHR November baseline separately: V2 **70 trades / −4.59R**, V3 **23 trades / +8.64R**, and **not** counted in the six-stock totals because it was the sample used to choose V3.

[Full independent research report](../results/RudraEMA5_6stocks_3months_RESEARCH_REPORT.md) · [Machine-readable ledger](../results/RudraEMA5_6stocks_3months_V2_V3.json).

### Data and caveats

All source series are **static**, not live. Original monthly source CSVs are in `ASJR-Three-Candle-Original/data/2026-MM`. Stock prices are packed at precision 1/10000 USD; candle timestamps are UTC and converted to **Europe/London** including UK summer time. COHR source only contains November and is clipped to 27 November 18:00 GMT; six other stocks end with 25 November's US session.

Resampled timeframes **recompute** indicators and trades using only complete source blocks; these are different 15m/30m/1H strategies, not validation of 5m V3.

Historic five-minute candle highs/lows do not reveal the actual order of price touches, so 0.2% trailing-stop execution, same-bar entries and SL exits are unverified. No spreads, slippage, fees, overnight borrow costs, market impact or extended-hours liquidity filter. 1R is a share-price move, not an account return. The Sept–Nov data are now viewed, so future optimization on them cannot be labelled out-of-sample.
