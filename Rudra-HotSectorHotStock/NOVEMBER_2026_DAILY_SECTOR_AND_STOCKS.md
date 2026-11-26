# Rudra-HotSectorHotStock — November 2026 day-by-day sector leaders and stock research

**Research as of 26 November 2026 (UK). Scope: 2–25 Nov 2026, 18 US regular trading days.** Phase 1 ETF downloads **12/12 succeeded**; VPS script audit: **18/18 sessions per ETF, each with 26 regular-session 15-minute bars, no duplicate session bars**. The stock-level *top 10 per daily winning sector is not yet established*. Do not interpret `Pending` as no strong stocks.

## Definitions (avoid look-ahead)

- **Daily winning sector:** rank all 11 sector ETFs by their first completed **09:30–09:45 ET** (14:30–14:45 UK in Nov 2026) 15-minute **open-to-close percentage return**. `SPY` is the benchmark, excluded from rankings.
- **Daily top 10 stocks (intended):** first establish the winning ETF's **full, dated sector membership**, obtain each stock's first 09:30–09:45 ET OHLCV, then rank by `(09:45 close / 09:30 open - 1) * 100`. Later-day or full-day gainers must **not** be used to decide this opening top 10.
- **Proposed trade-selection rule:** from those top 10, select the three largest first-15-minute price gainers, then choose the highest **absolute 15-minute share volume** among those three; validate liquidity and compare RVOL in subsequent research. Entry assumed **after** 09:45 ET, and five-minute data are retained for stop-order simulation.
- **Proposed exit:** initial stop -1%; at +1% move stop to breakeven; at +2% stop +1%; then advance in 1% steps; exit on active stop or by **16:00 ET / 21:00 UK**, with execution/slippage tests. These are research rules, not executed trades.

## 1. Verified daily sector leadership and stock-top-10 readiness

| Date (2026) | #1 sector | 09:30–09:45 gain | #2 sector | Gain | #1 sector IBKR data | Top-10 stock ranking |
|---|---|---:|---|---:|---|---|
| 2026-11-02 | **Consumer Discretionary (XLY)** | +0.950% | Communication Services (XLC) | +0.558% | [XLY 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318568/XLY_2026-11-01_2026-11-25_15min_UTC.csv) | [10 web full-day gainers](data/2026-11-02/xly_web_close_gainers_top10.csv) — **NOT 14:45 winners** |
| 2026-11-03 | **Technology (XLK)** | +1.101% | Healthcare (XLV) | +0.681% | [XLK 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318566/XLK_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-04 | **Technology (XLK)** | +1.688% | Consumer Discretionary (XLY) | +1.127% | [XLK 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318566/XLK_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-05 | **Energy (XLE)** | +0.421% | Utilities (XLU) | -0.159% | [XLE 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318572/XLE_2026-11-01_2026-11-25_15min_UTC.csv) | [10 web close gainers](data/2026-11-05/xle_web_close_gainers_top10.csv) — **NOT 14:45 winners** |
| 2026-11-06 | **Healthcare (XLV)** | +1.213% | Financials (XLF) | +0.987% | [XLV 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318571/XLV_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-09 | **Consumer Discretionary (XLY)** | +1.454% | Technology (XLK) | +1.171% | [XLY 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318568/XLY_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-10 | **Technology (XLK)** | +0.426% | Industrials (XLI) | +0.407% | [XLK 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318566/XLK_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-11 | **Consumer Staples (XLP)** | +0.509% | Real Estate (XLRE) | +0.383% | [XLP 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318574/XLP_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-12 | **Technology (XLK)** | +1.342% | Consumer Discretionary (XLY) | +0.653% | [XLK 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318566/XLK_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-13 | **Communication Services (XLC)** | +0.674% | Consumer Staples (XLP) | +0.273% | [XLC 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318567/XLC_2026-11-01_2026-11-25_15min_UTC.csv) | [10 web close gainers](data/2026-11-13/xlc_web_close_gainers_top10.csv) — **NOT 14:45 winners** |
| 2026-11-16 | **Technology (XLK)** | +0.594% | Industrials (XLI) | +0.310% | [XLK 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318566/XLK_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-17 | **Materials (XLB)** | +0.994% | Industrials (XLI) | +0.713% | [XLB 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318575/XLB_2026-11-01_2026-11-25_15min_UTC.csv) | [10 web close gainers](data/2026-11-17/xlb_web_close_gainers_top10.csv) — **NOT 14:45 winners** |
| 2026-11-18 | **Consumer Discretionary (XLY)** | +0.887% | Utilities (XLU) | +0.856% | [XLY 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318568/XLY_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-19 | **Technology (XLK)** | +0.967% | Financials (XLF) | -0.159% | [XLK 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318566/XLK_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-20 | **Consumer Discretionary (XLY)** | +0.571% | Communication Services (XLC) | +0.516% | [XLY 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318568/XLY_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-23 | **Healthcare (XLV)** | +0.728% | Utilities (XLU) | +0.560% | [XLV 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318571/XLV_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-24 | **Healthcare (XLV)** | +1.842% | Communication Services (XLC) | +0.979% | [XLV 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318571/XLV_2026-11-01_2026-11-25_15min_UTC.csv) | **Pending** (full sector stock universe not downloaded) |
| 2026-11-25 | **Energy (XLE)** | +0.316% | Utilities (XLU) | +0.277% | [XLE 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318572/XLE_2026-11-01_2026-11-25_15min_UTC.csv) | 10 sampled XLE stocks; **not full-universe top 10** |

**Source:** 26 Nov 2026 VPS log `sector_15m_nov2026_20261126_165838.log`, produced by [`download_sector_15m_nov2026.py`](download_sector_15m_nov2026.py), corroborated by its validated published IBKR CSV exports. The log and job mapping remain on VPS at `/root/trading/ASJR_research_logs/hot_sector/`; they were **not** committed to GitHub.

**Counts:** XLK=6, XLY=4, XLV=3, XLE=2, XLC=1, XLP=1, XLB=1; total 18 days. Other sectors did not rank #1 at the first 15-minute close.

## 2. Actual stock results available: 25 Nov Energy (XLE) — provisional sample, not a certified sector top 10

For **25 Nov 2026 only**, ten Energy tickers were subsequently downloaded. **These candidates originally came from a day-end-gainer shortlist**, so selecting them retrospectively is *look-ahead / selection bias*. Their opening candles and post-entry price paths are valid observations, but this is **not** proof these were the ten strongest among the full XLE constituent universe at 09:45 ET. Use only for a sample method check until the wider constituent universe is downloaded.

| Rank within sample | Ticker | First 15m gain | First 15m shares | Max upside after 14:45 vs signal close | 21:00 return vs signal close | IBKR 5m CSV |
|---:|---|---:|---:|---:|---:|---|
| 1 | APA | +1.589% | 138,038 | +1.388% | +0.176% | [APA 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795711282880/APA_2026-11-25_2026-11-25_5min_UTC.csv) |
| 2 | FANG | +1.246% | 46,257 | +1.921% | +1.219% | [FANG 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795711282876/FANG_2026-11-25_2026-11-25_5min_UTC.csv) |
| 3 | SLB | +1.000% | 238,873 | +5.143% | +4.476% | [SLB 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795711282874/SLB_2026-11-25_2026-11-25_5min_UTC.csv) |
| 4 | DVN | +0.945% | 565,483 | +3.002% | +1.969% | [DVN 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795711282875/DVN_2026-11-25_2026-11-25_5min_UTC.csv) |
| 5 | EQT | +0.899% | 167,056 | +4.942% | +4.355% | [EQT 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795711282872/EQT_2026-11-25_2026-11-25_5min_UTC.csv) |
| 6 | EXE | +0.760% | 74,049 | +5.904% | +5.648% | [EXE 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795711282871/EXE_2026-11-25_2026-11-25_5min_UTC.csv) |
| 7 | HAL | +0.753% | 282,170 | +3.410% | +2.696% | [HAL 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795711282877/HAL_2026-11-25_2026-11-25_5min_UTC.csv) |
| 8 | OKE | +0.463% | 151,177 | +2.696% | +2.247% | [OKE 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795711282879/OKE_2026-11-25_2026-11-25_5min_UTC.csv) |
| 9 | KMI | +0.260% | 284,290 | +3.046% | +2.722% | [KMI 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795711282878/KMI_2026-11-25_2026-11-25_5min_UTC.csv) |
| 10 | TPL | -0.075% | 29,565 | +5.134% | +3.316% | [TPL 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795711282873/TPL_2026-11-25_2026-11-25_5min_UTC.csv) |

**Sample rule result, 25 Nov:** top three by **opening** price growth are APA, FANG, SLB; their first-15-minute volumes are 138,038, 46,257, and **238,873** shares, respectively, so the rule selects **SLB**. Using its 14:45 bar **close reference** $46.47, maximum subsequent five-minute bar high was $48.86 (**+5.14%**), and regular-session close was $48.55 (**+4.48%**). A next-bar-open fill was $46.48, and fills/costs remain unverified. This is a **single-case example**, not an audited month backtest.

## 3. Exact sector-history data locations (all 18 days per file)

| ETF | Sector / role | Source file |
|---|---|---|
| XLK | Technology | [XLK 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318566/XLK_2026-11-01_2026-11-25_15min_UTC.csv) |
| XLC | Communication Services | [XLC 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318567/XLC_2026-11-01_2026-11-25_15min_UTC.csv) |
| XLY | Consumer Discretionary | [XLY 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318568/XLY_2026-11-01_2026-11-25_15min_UTC.csv) |
| XLF | Financials | [XLF 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318569/XLF_2026-11-01_2026-11-25_15min_UTC.csv) |
| XLI | Industrials | [XLI 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318570/XLI_2026-11-01_2026-11-25_15min_UTC.csv) |
| XLV | Healthcare | [XLV 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318571/XLV_2026-11-01_2026-11-25_15min_UTC.csv) |
| XLE | Energy | [XLE 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318572/XLE_2026-11-01_2026-11-25_15min_UTC.csv) |
| XLU | Utilities | [XLU 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318573/XLU_2026-11-01_2026-11-25_15min_UTC.csv) |
| XLP | Consumer Staples | [XLP 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318574/XLP_2026-11-01_2026-11-25_15min_UTC.csv) |
| XLB | Materials | [XLB 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318575/XLB_2026-11-01_2026-11-25_15min_UTC.csv) |
| XLRE | Real Estate | [XLRE 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318576/XLRE_2026-11-01_2026-11-25_15min_UTC.csv) |
| SPY | Market benchmark | [SPY 15m CSV](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795712318577/SPY_2026-11-01_2026-11-25_15min_UTC.csv) |

Each CSV is accompanied by `manifest.json` in the same `research-<job-id>` directory. Source: IBKR Gateway 4002; interval=15min; `Datetime_UTC` timestamps; date range 2026-11-01 to 2026-11-25. Published datasets: [IBKR research export folder](https://github.com/raghunathbhandari/ASJR/tree/main/three_candle/data/ibkr_bridge).

## 4. Existing stock data inventory and what is still missing

**Full-month 5-minute stock files already present (technology sample):** NVDA, INTC, TSLA, PLTR, AMD, AAPL. These are **six sampled symbols**, not the whole XLK ETF constituent universe or sufficient for a full daily top 10.

| Ticker | Full-month IBKR 5m data |
|---|---|
| NVDA | [NVDA Nov 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795685200003/NVDA_2026-11-01_2026-11-25_5min_UTC.csv) |
| INTC | [INTC Nov 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795685200006/INTC_2026-11-01_2026-11-25_5min_UTC.csv) |
| TSLA | [TSLA Nov 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795685200009/TSLA_2026-11-01_2026-11-25_5min_UTC.csv) |
| PLTR | [PLTR Nov 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795685200012/PLTR_2026-11-01_2026-11-25_5min_UTC.csv) |
| AMD | [AMD Nov 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795685200015/AMD_2026-11-01_2026-11-25_5min_UTC.csv) |
| AAPL | [AAPL Nov 5m](https://github.com/raghunathbhandari/ASJR/blob/main/three_candle/data/ibkr_bridge/research-1795685200018/AAPL_2026-11-01_2026-11-25_5min_UTC.csv) |

**Additional 25 Nov stock-only data (not for the other 17 dates):** [XLU Utilities stock research files](https://github.com/raghunathbhandari/ASJR/tree/main/three_candle/data/ibkr_bridge) (31 names including a later NEE retry), Materials samples IP/SW/CRH, and the ten XLE Energy files linked in section 2. These do not establish the sector-wide top 10 for any full month.

**Missing for Phase 2:** a defensible, historically dated constituent universe and 09:30–09:45 ET 15-minute OHLCV for *every eligible constituent* on each winning-sector date, plus five-minute OHLCV after entry. Without this, claiming 18 × 10 actual winners is unsupported. A current ETF holdings list can serve as a labelled retrospective proxy but is not identical to the sector universe on every historical day.

## 5. Day-wise Phase 2 deliverables (to fill after future verified downloads)

For each date, save in `Rudra-HotSectorHotStock/data/YYYY-MM-DD/`: `sector_leader.json` (winner, runner-up, ETF file/first candle); `stock_universe.csv` (dated sector constituents, source and snapshot date); `stock_opening_15m_ranked.csv` (rank 1–10, open, close, growth %, shares, input path, coverage flags); `selected_trade.json` (top three, volume winner, signal/fill, stops); and `backtest_5m.json` (stop history, exit, costs and ambiguity flags). **These output files have not yet been created**; they are required targets, not existing links.

A complete daily top-10 ranking must cover every known eligible constituent (or state the exact shortlist restriction), record failed/missing downloads, use historical information available by 09:45 ET, and label results `COMPLETE` only after QA. Excluding missing stocks can materially change ranks.

## 6. Run and update

Sector collection script: [`download_sector_15m_nov2026.py`](download_sector_15m_nov2026.py). Live sectors downloader source: [`three_candle/ibkr_bridge_range_download.py`](../three_candle/ibkr_bridge_range_download.py). Next: obtain frozen constituent universes for the seven winning sectors (XLK, XLY, XLV, XLE, XLC, XLP, XLB); download their 5m data for the required historical dates; then replace `Pending` with verified daily ranked stock reports and actual paths. Do not alter the original source CSVs.

## 7. Machine-readable daily results

The same verified 18-date leader list is available as [`november_2026_sector_leaders.csv`](november_2026_sector_leaders.csv), including first-15-minute sector gains, exact ETF source CSV paths, and each date's stock-top-10 research status. This allows Phase 2 to populate daily top-10 rankings without manually re-entering the sector choices.


## 8. Consolidated day-wise stock shortlist CSV

Master research CSV: [**`november_2026_daily_top10_stocks.csv`**](november_2026_daily_top10_stocks.csv), with a consistent day/sector/rank/ticker schema, columns for web full-day return, IBKR first-15-minute gain, 15-minute share volume, maximum subsequent upside and source data paths. **Current entries: 20 candidate rows across two dates; all other dates are pending.**

- **2 Nov (XLY):** 10 ranked **full-day close-to-close gainers** from [The Market Wrap 2 Nov archive](https://www.market-wrap.com/daily-wrap/2026-11-02/): DASH, CVNA, PHM, NVR, DHI, LEN, EXPE, RCL, LOW, MAR. These are **look-ahead candidates**, not the actual opening top 10 at 14:45 UK. Their intraday IBKR stock candles have **not yet been downloaded**.
- **25 Nov (XLE):** 10 previously downloaded Energy sample stocks ranked by first-15-minute performance, with IBKR 5-minute path and volume. The **sample stock universe was selected using later-day winners**, therefore the reported ordering is only within that preselected sample, not the whole sector's genuine opening top 10.
- **Other 16 sessions:** no validated constituent top-10 list yet. Their winning sectors are already recorded in [`november_2026_sector_leaders.csv`](november_2026_sector_leaders.csv); don't manufacture missing rankings.

Retain both kinds of rankings **separately**: an internet-researched full-day shortlist is useful for retrospective exploration, but must not be confused with the live-available 09:45 ET signal. Future validated intraday ranks should use an explicit `IBKR_FULL_UNIVERSE_0945` status and point to the underlying stock bars.


## 9. Additional November web-sourced daily shortlists

Web-archive shortlists have now been manually verified and committed for **5 Nov (XLE), 13 Nov (XLC), 17 Nov (XLB)**, in addition to **2 Nov (XLY)** and the existing sampled **25 Nov (XLE)** dataset. [Consolidated master](november_2026_daily_top10_stocks.csv) now contains **50 rows across 5 dates**. These web-stock ranks are from **daily close-to-close percent changes** within the source's S&P 500 sector coverage, NOT 09:45 ET opening gains and not necessarily the exact historical sector-ETF membership.

**Remaining 13 dates:** 3, 4, 6, 9, 10, 11, 12, 16, 18, 19, 20, 23, 24 November. The program [`build_november_web_shortlists.py`](build_november_web_shortlists.py) fetches the archive for each remaining date, verifies sector-table coverage, generates up to ten close-gainer rows/day and pushes daily CSVs and the master/index updates to GitHub. A `--dry-run` validates without publishing. This script **has not been executed against the VPS website data**. Any inaccessible/invalid archive days remain PENDING; the script will not invent tickers.
