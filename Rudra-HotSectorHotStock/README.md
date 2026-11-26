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
