# Rudra-HotSectorHotStock — Idea Log

**Created:** 26 November 2026 | **Status:** Design discussion; no executed strategy or proven backtest.

## Confirmed V1 design

1. At **09:35 ET**, use completed **09:30–09:35** OHLCV of the 11 US sector ETFs to rank sector strength.
2. Use IBKR scanner codes (`TOP_PERC_GAIN`, `HOT_BY_VOLUME`) to discover hot stocks. Scanner can run from market open; sector selection waits for candle completion.
3. Check sector membership of scanned stocks and validate their completed first five-minute candles.
4. Select **up to three** leading stocks **from the top sector**. Prefer a NO TRADE when nothing passes filters.
5. **BUY** immediately after the opening five-minute candle has closed and stock screening completed, subject to actual market latency.
6. **Initial stop:** actual fill × **0.99**.
7. **First milestone +1%:** when post-entry trade/high reaches actual fill × **1.01**, move stop to **breakeven** (actual fill), without closing the position.
8. **Each subsequent +1% milestone:** ratchet stop up an additional **1% of original entry**; never loosen it.
9. No fixed +1% take-profit order; trailing stop is intended to capture continuation.

Example: fill $100 → SL $99; post-entry high $101 → SL $100; high $102 → SL $101; high $103 → SL $102.

## Sector ranking ideas (hypotheses; weights unconfirmed)

- First 5-minute open-to-close ETF return.
- Previous close-to-09:35 return to capture gap and opening continuation.
- Relative ETF performance against **SPY** over consistent windows.
- First-five-minute relative volume against previous sessions' **same 09:30–09:35 interval** (not full-day RVOL).
- Breadth: percentage of mapped constituents advancing, if data permits.
- First candle body strength and close relative to high.

Consider requiring absolute positive performance, not merely "least weak" sector.

## IBKR scanner ideas

- `TOP_PERC_GAIN`: top percentage gainers; **not** explicitly first-five-minute leaders.
- `HOT_BY_VOLUME`: unusually active stocks.
- Optional `MOST_ACTIVE`: liquidity cross-check.
- Scanner may be capped at ~50 hits per scan and omit leading names from the chosen sector. Assess sector-targeted scanner filters or a constituent-universe fallback.
- Map scanner results to ETF sector carefully; IBKR category taxonomy and SPDR GICS sectors may differ.
- Verify historical **average** volume separately; `aboveVolume` is not necessarily 10-day average volume.

## Ranking stocks (to test)

First-five-minute price move vs sector ETF; volume in the same opening window vs historical; strong bullish first candle; trading spread/liquidity; optional VWAP comparison. Proposed minimum price $5, average daily volume 1M shares.

## Outstanding decisions

- Exact sector score / tie-breaker and whether positive sector strength is mandatory.
- Precise stock score, minimum acceptable RVOL and candle quality.
- Position sizing for three simultaneous BUYs, max exposure and correlation.
- Entry order type, acceptable price drift, spread and slippage cutoff.
- When to exit if a stop is never triggered (end of day vs overnight).
- Re-entry policy, scanner outage / insufficient-data behaviour.
- Tick / intrabar execution ordering in the backtest and realistic protective stop modelling.
- Live execution **not authorised**; proceed with research and paper trading only.

**Research cycle:** idea → versioned rules → historical replay → paper validation → independent review → revise.
