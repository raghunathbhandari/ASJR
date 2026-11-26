# ASJR Trading Chart Lab

**Version:** 1.0 — 25 November 2026  
**Purpose:** A permanent, extendable strategy research dashboard. The same chart handles historical data, price, session VWAP, optional EMA overlays, entry/exit markers, zoom/pan, and a growing **named strategy library**.

## Open the dashboard

- **GitHub Pages site (after owner enables Pages):** https://raghunathbhandari.github.io/ASJR/
- **Source code:** [TradingChartLab](./)
- **Original MES October CSV:** [MESZ2026 5-minute October 2026](../three_candle/data/MESZ2026_IBKR_5m_2026-10.csv)

**One-time owner setup:** GitHub repository `Settings → Pages → Build and deployment → Source: GitHub Actions`. The isolated `.github/workflows/asjr_trading_chart_lab_pages.yml` workflow uploads **only** the `TradingChartLab/` static files. It never changes VPS/bot code or sends orders. The source repository currently reports `has_pages=false`, so the public site cannot be assumed live until Pages is enabled and deployment succeeds.

## Current capabilities

- Loads the **original public ASJR GitHub MES October CSV at runtime** (no duplicate copy).
- IBKR 5-minute OHLCV → **completed 15-minute bars**, with 5-minute volume-weighted typical-price VWAP.
- VWAP resets at the CME index-futures session boundary (**22:00 UTC during October 2026**). The first October session is incomplete at its beginning because the source starts at 00:00 UTC.
- Zoom with mouse wheel, drag to pan, hover for timestamp, price and indicator values. 6-hour / 1-session / 3-session / 5-session / full-month presets; next/previous session buttons. Table rows focus on an individual trade.
- Show/hide session VWAP, EMA9, EMA20, BUY/EXIT markers, and candles when zoomed in.
- Edit minimum VWAP deviation, fixed stop-loss, and maximum hold; recalculate historical BUY/EXIT results; download trade CSV.
- **Strategy names as a list**, with active/planned/draft status. Add draft names in the UI, persisted in that browser using `localStorage`; they are *not* backtests and do not automatically appear for other users/devices.

## Strategy register

| ID | Name | State |
|---|---|---|
| `vwap-mean-reversion` | VWAP Mean Reversion | **Active prototype** |
| `algo-with-renko` | AlgoWithRenko · 20pt | Planned dashboard integration; [existing backtest](../AlgoWithRenko/README.md) |
| `vwap-ema9` | VWAP + EMA9 | Planned |
| `three-candle` | Three-Candle Reversal | Planned |
| `gann-date-360` | Gann Date 360 | Planned |
| `point-figure` | Point & Figure | Planned |

When we define a new strategy, add its name, description and a `run(bars, params)` implementation to `strategies.js`. It then appears in the same chart engine; no recreation of the dashboard. New indicator overlays go in `app.js`. Update this README with each change and bump the visible version in `index.html`.

## VWAP Mean Reversion v1 — exact rules

**Long-only, experimental.** The strategy uses completed 15-minute OHLC candles and previous-bar VWAP.

1. A completed signal bar must have `Low <= VWAP - deviation`, `Close > Open`, `Close > previous Close`, and `Close < VWAP - 4 points`; signal and previous bar must be in the same CME session.
2. Buy at the **next 15-minute bar OPEN** only if `Open < signal VWAP - 2 points` and the entry-to-target distance exceeds 2 points.
3. **Target:** signal VWAP rounded down to a MES quarter-point tick; fixed at entry (no look-ahead).
4. **Stop:** entry minus configurable points (default 20).
5. Process each subsequent 15-minute OHLC bar with priority: gap-through stop at OPEN; intra-bar stop at stop level; VWAP target; last bar of session at CLOSE; max hold at CLOSE (default 16 bars / four hours). Treat ambiguous stop-and-target bars as **stop first**.
6. No same-bar re-entry after an exit. One position at a time. Results in gross MES points; **1 MES = $5/point**.

**Default**: deviation 15 pts / stop 20 pts / max 16 bars. Preliminary October results: **46 trades, 27 winning, +6.75 MES points (+$33.75 gross, one MES), 106 points max closed-equity drawdown**. These are exploratory values, with parameters examined on this same month. Recheck after any strategy changes.

**Important exclusions:** fees, slippage (except stop gaps), spread, intrabar tick sequence, live brokerage execution, margin, rollover and interest. The October source coverage audit says **NEEDS REVIEW**, not certified complete. Do not infer positive expected return from this single month.

## Files / change management

- `index.html`: stable dashboard shell and UI controls.
- `styles.css`: dark, responsive appearance.
- `strategies.js`: canonical **versioned** strategy list and pure backtest logic.
- `app.js`: source CSV loading, resampling, VWAP/EMA calculation, chart and user interaction.
- `.github/workflows/asjr_trading_chart_lab_pages.yml`: GitHub Pages deployment (once enabled).

**Do not modify** existing `three_candle/`, `AlgoWithRenko/`, DataLake, bots or production VPS when extending the dashboard. Use a separate PR/feature branch when the repo's branch protection requires it. No force-push or history rewrite.

## Next improvements

- Full tick-aware order-fill audit + commission/slippage model.
- EMA/RSI/ADX filter panels and walk-forward/out-of-sample evaluation.
- MES Renko price overlay and independent strategy comparison.
- Optional Gann and P&F visual layers.
- Additional month selector and research outcome exports.

## HotSector Research dashboard

**New reusable stock-research dashboard (26 Nov 2026):** [hotsector.html](hotsector.html) — deployed under `/ASJR/hotsector.html` when the repository's GitHub Pages site is enabled. Direct intended URL: `https://raghunathbhandari.github.io/ASJR/hotsector.html`. **Do not claim that URL is live until the owner enables GitHub Pages and the deployment workflow succeeds.**

The dashboard loads CSVs **directly at runtime** from public ASJR `main`: `Rudra-HotSectorHotStock/november_2026_sector_leaders.csv`, `Rudra-HotSectorHotStock/november_2026_daily_top10_stocks.csv`, each selected stock's `ibkr_stock_5min_csv`, and `three_candle/data/ibkr_bridge/research-1795712318577/SPY_2026-11-01_2026-11-25_15min_UTC.csv` for the November SPY first-15-minute filter.

Controls: **sector filter**, **SPY index filter** (all / positive / negative / sector outperforms SPY), **date**, **stock**, and **6 / 9 / 12 / 24 / 78 five-minute candles**. Shows actual OHLC candlesticks, traded shares per bar, first three bars shaded as 09:30–09:45 ET selection window, next-bar-open entry reference, initial −1% stop reference, hover/tap OHLCV and source GitHub CSV. The daily shortlist table is clickable. After the master CSV points to newly published stock files, the dashboard updates on refresh; **no per-stock code changes required**.

Execution note: the dashboard's sequential OHLC approximation flags same-bar stop/milestone order ambiguity and is not a fill-accurate live backtest. It intentionally preserves the distinction between web **full-day closing gainers** and a genuine 09:45 ET opening sector-wide stock ranking. The viewer is read-only and never sends orders.

**GitHub Pages setup:** `Settings → Pages → Build and deployment → Source: GitHub Actions`. The existing `.github/workflows/asjr_trading_chart_lab_pages.yml` publishes the entire `TradingChartLab` folder. Workflow now includes `actions/configure-pages@v5` before artifact upload and `actions/deploy-pages@v4` for deployment. Check the workflow under `Actions → ASJR Trading Chart Lab — GitHub Pages` after enabling Pages.

