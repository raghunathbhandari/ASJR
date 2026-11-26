# Rudra-HotSectorHotStock

**Status:** Idea capture / research specification (V1, 26 November 2026). **No executable strategy, backtest, live alert, or trading bot is claimed here.**

## Objective

At the opening of the US regular stock session, identify the **single strongest sector** from its exchange-traded fund (ETF) and select the **top three stocks in that sector** using the IBKR market scanner. The strategy aims to enter immediately following the first completed five-minute candle and manage each trade with a tight percentage stop.

**Architecture:** Sector ETF candles → sector ranking → IBKR stock scanner candidates → verify sector membership and first stock candle → top 3 → BUY / risk management.

## Draft V1 rules (agreed in discussion)

| Setting | Specification |
| --- | --- |
| Strategy | Rudra-HotSectorHotStock |
| Direction | Long (BUY), opening-momentum research |
| Market | US-listed stocks, regular trading hours |
| Market open | 09:30 Eastern Time (ET) |
| Evaluation | First complete 09:30–09:35 ET 5-minute candle |
| Sector source | 11 Select Sector SPDR ETFs (5-minute bars) |
| Benchmark | SPY |
| Sector selection | Strongest sector at 09:35 ET (exact score to validate) |
| Stock candidate discovery | IBKR API scanner; proposed codes `TOP_PERC_GAIN` and `HOT_BY_VOLUME` |
| Stock shortlist | Up to three leading stocks **belonging to the chosen sector**, confirmed with 09:30–09:35 bar |
| Proposed liquidity constraints | Price > $5, 10-day average volume > 1,000,000 shares (requires history; scanner `aboveVolume` is not a substitute for average volume) |
| Entry | Buy each selected stock as soon as the 09:30–09:35 candle is confirmed and scanning/ranking completed; actual fill may be later than 09:35 |
| Initial stop-loss | 1% below actual entry fill |
| First profit milestone | +1% above actual entry fill, **do not take full profit** |
| Trailing stop | At +1% move SL to breakeven; for each further +1%-of-entry rise, raise the SL by 1%-of-entry |
| Re-entry | Not defined in V1 |

**Exit rule confirmed (26 November 2026):** **+1% is the first profit milestone, not a fixed exit.** When post-entry price reaches entry × 1.01, move the protective stop to **actual entry (breakeven before costs)** and keep the position. Every additional full +1% gain measured against the original fill increases the stop by another 1% of the original entry price. The stop **never moves down**. End-of-day exit, order placement details and fill behaviour remain to be specified and tested.

### Stepped trailing example (entry $100)

| Highest price achieved **after entry** | Protective stop |
| --- | --- |
| $100.00 to $100.99 | $99.00 |
| $101.00 to $101.99 | $100.00 (breakeven before costs) |
| $102.00 to $102.99 | $101.00 |
| $103.00 to $103.99 | $102.00 |
| $104.00 to $104.99 | $103.00 |

A stock can pass a milestone then fall back through the protective stop; a stop fill may slip, particularly at the open. Use intrabar prices for testing; 5-minute OHLC alone cannot always establish whether a trailing milestone or a stop happened first.

## Sector instruments

| ETF | Sector |
| --- | --- |
| XLK | Technology |
| XLC | Communication Services |
| XLY | Consumer Discretionary |
| XLF | Financials |
| XLI | Industrials |
| XLV | Healthcare |
| XLE | Energy |
| XLU | Utilities |
| XLP | Consumer Staples |
| XLB | Materials |
| XLRE | Real Estate |
| SPY | Market benchmark (not a sector) |

## Data and sequence

1. **09:30 ET:** Subscribe to or collect five-minute ETF OHLCV data; launch IBKR stock scanner(s) for candidates. Avoid assuming the scanner itself contains the first five-minute return.
2. **09:35 ET:** After the final 09:30–09:35 ETF candles are complete, score the 11 sector ETFs. Include first-bar price movement, performance relative to SPY, opening relative volume and, if available, sector breadth.
3. Filter the returned scan candidates to the strongest sector, resolve stock-to-sector classification (IBKR contract details or maintained mapping), and verify first five-minute stock OHLCV, liquidity and strength.
4. Rank and select up to the **top three** qualifying stocks. If fewer than three qualify, **do not manufacture replacements**.
5. Submit intended entry orders with a controlled risk limit; use actual fills to derive stop prices. Record signal time, request latency, order time, fill time and slippage.
6. Monitor the confirmed step-trailing policy: initial -1%; at +1%, stop to breakeven; for each further +1% milestone, increase stop 1% of original fill. Stop never decreases.

**Timing:** ET 09:35 is usually UK 14:35, but can be UK 13:35 during the short US/UK daylight-saving transition gaps. All ASJR operational logs should use **Europe/London** timezone and retain ET for market-session labels.

## Practical constraints

- IBKR scan codes return ranked **candidates**, not a guaranteed exhaustive list of sector constituents or five-minute candle leaders; typical scanner result limits can miss strong stocks. Consider a sector-targeted scanner or fallback candidate universe.
- Scanner results and contract details must be received, filtered and bars confirmed **after** the five-minute candle closes. An exact 09:35:00 fill cannot be assumed.
- Market open spreads, gaps, partial fills, stop slippage and delayed data can materially affect the 1% initial stop and step-trailing strategy.
- Check market-data subscriptions, scanner parameters, ETF historical access, IBKR request pacing, account permissions, PDT/day-trading restrictions and market holidays before running.
- Historical tests must use point-in-time sector classification, survivorship-aware universes where possible, consistent corporate-action adjustment, commissions and plausible fill/slippage assumptions.
- **Research first, paper trade next, live only after verification and explicit authorisation.**

## Research files

- [IDEAS.md](IDEAS.md) — hypotheses, score and ranking ideas, decisions still open.
- [BACKTEST_PLAN.md](BACKTEST_PLAN.md) — historical validation, measurements and failure checks.

> Not investment advice. This is a hypothesis to backtest, not proven profitability.

## Phase 1 — November 2026 sector study (26 Nov 2026 update)

The 15-minute research pilot below supersedes the provisional 5-minute **entry-selection** timing described in the original V1 specification above; that original specification is retained for historical reference.

- **Sample:** 2026-11-01 through 2026-11-25, 18 US regular trading sessions (November 1 is Sunday).
- **Sector universe:** 11 Select Sector SPDR ETFs; also download SPY as market benchmark.
- **Signal time:** 09:45 ET / 14:45 UK. Compare each sector's *completed first 15-minute candle* (09:30–09:45 ET) as `(close/open - 1) × 100`.
- **Stock-selection hypothesis:** from the leading sector, examine the top three stocks by the first 15-minute price gain; choose the highest first-15-minute **absolute volume** among those three. Historical constituent-universe and liquidity screening must be point-in-time; do not select stocks retroactively using the day's closing winners.
- **Entry for backtest:** after the 09:45 ET signal, with an executable fill assumption (e.g. next-bar open). No assumption of a guaranteed close-price fill.
- **Exit:** initial stop -1% from actual fill; at each +1% entry-relative milestone raise the stop by 1% of the initial entry price (at +1% move to breakeven, at +2% to +1%, etc.). Stop never moves down. Close any still-open trade by 16:00 ET / 21:00 UK.
- **Execution study:** preserve 5-minute stock price data for exit and stop evaluation; flag bars where intrabar high/low ordering is ambiguous.

### Phase 1 download — sectors only

Run [`download_sector_15m_nov2026.py`](download_sector_15m_nov2026.py) from the VPS using the existing IBKR Python environment. It invokes the established `three_candle/ibkr_bridge_range_download.py` once per ETF, which **publishes each successful CSV plus a manifest to GitHub main** through a temporary isolated checkout. It will **not** queue or download constituent stocks.

The script checks 18 trading dates, opening 09:30 ET 15-minute candles, 26 regular-session 15-minute bars per day, and prints the leading two sector ETFs for each day's first completed candle. Logs and job mappings are stored outside the repo in `/root/trading/ASJR_research_logs/hot_sector/`. All timestamps in operational logs are UK time; CSV timestamps remain UTC.

**Phase 2 (after audit):** define the historical sector-specific candidate universe for each date, then download the top 10 eligible stocks per day's selected sector. Do not use future/day-end leadership when choosing 09:45 candidates. No stock downloads are part of Phase 1.

## November 2026 day-by-day report

- [**November 2026 — 18 daily sector leaders, first 15-minute gains, existing sampled stock rankings and exact GitHub CSV paths**](NOVEMBER_2026_DAILY_SECTOR_AND_STOCKS.md).
- **Status:** All 12 ETF files audited (18/18 sessions, 26 RTH 15-minute bars per session). Stock top 10 is **incomplete** until the broader daily winning-sector constituent universe and historical first-15-minute data are downloaded; only a labelled 25 November Energy 10-stock sample is currently available. Do not use end-of-day winners as the 09:45 historical candidate pool.

## Phase 2 — Construct daily top-10 stock candidates

**Status:** Phase 2 script created, but the new seven-sector constituent download and 18-day top-10 stock ranking have **not** been run.

Script: [phase2_top10_nov2026.py](phase2_top10_nov2026.py). Run from the existing VPS Python.

1. **--mode universe**: download the seven winning-sector ETF holdings from State Street and freeze a constituent CSV under /root/trading/ASJR_research_logs/hot_sector/phase2/frozen_sector_holdings.csv. The snapshot is a **retrospective current-holdings proxy**, NOT proven Nov 2026 point-in-time membership.
2. **--mode download --limit 15**: reuse already published full-month tickers, then request up to 15 missing stocks per run from the existing read-only IBKR downloader, 2026-11-01 to 2026-11-25, 15min interval; the downloader automatically publishes each CSV and manifest to GitHub main. Repeat to resume. --limit 0 attempts all missing stocks.
3. **--mode rank**: produce 18 day-specific rankings by the completed 09:30–09:45 ET stock candle open/close gain, record opening share volume and the best-volume ticker among top-three gainers, then publish data/YYYY-MM-DD/top10_opening_15m.csv and NOVEMBER_2026_TOP10_STOCKS.md through an isolated clone.
4. Download five-minute candles for the daily selected trade(s) to test stepped stops, true entry timing, and end-of-day exits; the initial 15-minute historical data only selects candidates.

**Quality guardrails:** Ranks are computed only from data available at 09:45 ET, not eventual day-end winners. Missing candidate bars yield INCOMPLETE_BARS status, not fabricated complete ranks. Even COMPLETE_BARS means only full coverage of the **current-holdings proxy**, not historically verified membership. No trades or live bot changes.


## Day-wise top-10 stock research CSV

See [**november_2026_daily_top10_stocks.csv**](november_2026_daily_top10_stocks.csv) for the consolidated per-date stock research table. It currently contains the **2 Nov XLY web-researched 10 full-day gainers** and **25 Nov XLE 10 sampled stock first-15-minute results**, with separate rank-method and research-status fields. Other 16 dates remain pending. The 2 Nov ranking uses **end-of-day returns**, so it cannot be used to claim a genuine 09:45 ET stock selection or an unbiased live-strategy backtest. [Daily sector-leader index](november_2026_sector_leaders.csv) links each day's stock-candidate CSV when available. [Detailed source notes](NOVEMBER_2026_DAILY_SECTOR_AND_STOCKS.md).


## Historical web shortlists: 3–24 November

**Current master status:** [november_2026_daily_top10_stocks.csv](november_2026_daily_top10_stocks.csv) has **50 sampled/researched stock rows for five dates**: 2 Nov XLY (web daily close), 5 Nov XLE (web daily close), 13 Nov XLC (web daily close), 17 Nov XLB (web daily close), and 25 Nov XLE (previously selected 10-name sample with IBKR first-15-minute measurements). The other **13 dates remain pending until the script executes successfully**.

Use [build_november_web_shortlists.py](build_november_web_shortlists.py) to fetch the [Market Wrap dated S&P sector tables](https://www.market-wrap.com/daily-wrap/) for the 16 dates 3–24 Nov, audit constituent-table coverage against published sector counts, and automatically write a per-day web shortlist CSV, update the master CSV and sector-leader index, and create NOVEMBER_2026_WEB_CANDIDATES.md. It uses an **isolated temporary Git clone** and does not modify the live ASJR worktree or place trades. The script needs Python `beautifulsoup4` and VPS internet access. Try `--dry-run --only-date 2026-11-03` before running without flags; unresolved/invalid dates remain pending instead of claiming ten winners.

**Critical:** Website lists **full-day S&P 500 sector gainers** (day-end hindsight). They are NOT the leading stocks at 09:45 ET and may not match sector ETF membership exactly. These are research shortlists only; IBKR historical 09:30–09:45 candles are required before comparing our opening-momentum strategy.

## Phase 3 — Day-wise IBKR 5-minute stock data from researched shortlists

**Script:** [download_daywise_top10_ibkr_5min.py](download_daywise_top10_ibkr_5min.py). This operationalises the existing **day-wise researched top-10 candidate CSV** instead of downloading all sector constituents. As of 26 Nov 2026, the master contains **5 dates × 10 tickers = 50 stock-day shortlist rows**, not 18 complete days. New candidate dates are automatically discovered when the master CSV is updated on GitHub.

Download target: for **each stock on each researched day**, fetch only that day's **5-minute IBKR OHLCV**, including extended session, with at least **78 regular-session bars** for a fully complete stock-day. Three 5-minute bars from 09:30–09:45 ET measure first-candle growth and summed share volume. The post-09:45 regular-session highs permit max-upside study and subsequent 5-minute stop backtesting.

**How it runs:** Fetch `origin/main` → read November master and daily winning sector index → require ten unique ranked stock entries for each researched day → examine existing daily/monthly 5-minute exports and reuse complete data → download missing day/ticker pairs through the already tested `three_candle/ibkr_bridge_range_download.py`, read-only Gateway 4002 → each successful file + manifest is automatically pushed by the existing downloader → audit 5-minute regular-session coverage → append source path, opening growth, opening volume and after-14:45 maximum upside to the master; publish [November stock IBKR coverage report](NOVEMBER_2026_IBKR_5MIN_DATA_STATUS.md) from a temporary clone. **The coverage report is a future output and not available until the command executes.**

**Run in SSH** (script fetched from `origin/main`, production worktree unchanged):

```bash
cd /root/trading/ASJR
git fetch origin main
git show origin/main:Rudra-HotSectorHotStock/download_daywise_top10_ibkr_5min.py > /tmp/download_daywise_top10_ibkr_5min.py
/root/trading/venv_new/bin/python -u /tmp/download_daywise_top10_ibkr_5min.py --dry-run
/root/trading/venv_new/bin/python -u /tmp/download_daywise_top10_ibkr_5min.py --date 2026-11-02 --limit 10
/root/trading/venv_new/bin/python -u /tmp/download_daywise_top10_ibkr_5min.py --limit 10
```

Repeat `--limit 10` to process remaining missing stock-days; `--limit 0` downloads all missing at once. Existing partial data is reported rather than overwritten; `--retry-incomplete` can explicitly request a new export for incomplete stock-days.

**Research integrity:** Full-day web lists were unknowable at 09:45 ET, so IBKR opening re-ranking **within that preselected list** is not an unbiased historical live screen. The download script preserves the `rank_method`, original rank, and `research_status` columns. It does not trade, change production processes, or claim every date is already complete.

## Reusable HotSector candlestick research dashboard

**GitHub source:** [TradingChartLab/hotsector.html](../TradingChartLab/hotsector.html) with [hotsector.js](../TradingChartLab/hotsector.js). This is a permanent GitHub CSV-driven read-only dashboard; select date, winning sector, stock, SPY first-15-minute index filter and opening candle count. It shows five-minute OHLC, opening 15-minute gain and volume, simulated next-bar entry and original −1% stop. When subsequent IBKR stock files are committed to the master CSV, click **Refresh GitHub data** rather than creating a new chart.

**Intended GitHub Pages address (not yet verified live):** `https://raghunathbhandari.github.io/ASJR/hotsector.html`. The repository owner needs to enable **Settings → Pages → Source: GitHub Actions** and run the existing ASJR Trading Chart Lab Pages workflow first. The web dashboard does not trade, and web full-day stock shortlist rankings remain hindsight-selected until a full opening-sector universe has been studied.
