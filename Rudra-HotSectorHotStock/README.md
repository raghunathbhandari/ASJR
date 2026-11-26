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
| Profit milestone / target | +1% above actual entry fill |
| Trailing stop | Increase stop in 1%-price steps as favourable price milestones are reached |
| Re-entry | Not defined in V1 |

**Unresolved: +1% exit interpretation.** An unconditional full-position take-profit at +1% conflicts with allowing a trailing stop to profit beyond +1%. Alternatives: (A) exit full size at +1%; (B) use +1% as the first trailing milestone, move SL to breakeven and keep the position; (C) sell 50% at +1%, trail the remainder. **Do not implement an execution engine until this choice is confirmed.**

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
6. Monitor protective stop and profit/trailing behaviour according to the exit choice once finalised.

**Timing:** ET 09:35 is usually UK 14:35, but can be UK 13:35 during the short US/UK daylight-saving transition gaps. All ASJR operational logs should use **Europe/London** timezone and retain ET for market-session labels.

## Practical constraints

- IBKR scan codes return ranked **candidates**, not a guaranteed exhaustive list of sector constituents or five-minute candle leaders; typical scanner result limits can miss strong stocks. Consider a sector-targeted scanner or fallback candidate universe.
- Scanner results and contract details must be received, filtered and bars confirmed **after** the five-minute candle closes. An exact 09:35:00 fill cannot be assumed.
- Market open spreads, gaps, partial fills, stop slippage and delayed data can materially affect a 1% risk/1% target strategy.
- Check market-data subscriptions, scanner parameters, ETF historical access, IBKR request pacing, account permissions, PDT/day-trading restrictions and market holidays before running.
- Historical tests must use point-in-time sector classification, survivorship-aware universes where possible, consistent corporate-action adjustment, commissions and plausible fill/slippage assumptions.
- **Research first, paper trade next, live only after verification and explicit authorisation.**

## Research files

- [IDEAS.md](IDEAS.md) — hypotheses, score and ranking ideas, decisions still open.
- [BACKTEST_PLAN.md](BACKTEST_PLAN.md) — historical validation, measurements and failure checks.

> Not investment advice. This is a hypothesis to backtest, not proven profitability.
