# Rudra-HotSectorHotStock — Backtesting Plan

**Status:** Planned, not run. Do not interpret this document as a measured result.

## Dates / universe

- Begin with **September, October and November 2026** US regular sessions, excluding market holidays and incomplete sessions unless modelled explicitly.
- ETFs: XLK, XLC, XLY, XLF, XLI, XLV, XLE, XLU, XLP, XLB, XLRE; SPY benchmark.
- Reconstruct candidate snapshots and stock sector membership **as-of each test date**; do not reuse today's scanner ranking as if historical.
- IBKR real-time scanner does **not** provide point-in-time historical scan results automatically; either archive scanner results live or create a historical scanner proxy and label it as such.

## Strict event sequence

1. Build first completed `09:30–09:35 ET` candle from 5-minute data (avoid bars labelled at the opposite edge).
2. Rank sector ETFs using only information known by **09:35 ET**.
3. Discover candidate universe that could have been known at that time; map it to the selected sector.
4. Rank candidate stocks using **only pre-entry** information, take up to three.
5. Simulate entry **after** signal completion with specified order latency, spread, commissions and slippage; never assume buy at the candle close without qualification.
6. Set stop 1% below the **filled entry** price.
7. Upon each **post-entry** +1% price milestone, move stop to entry (at first milestone), and upward one more percent-of-original-fill per additional milestone. Never decrease stop. Initial example: fill 100 → 99; 101 → 100; 102 → 101.
8. Determine exits from intrabar trades/quotes where possible. With only 5-minute OHLC, milestone and stop can occur in the same bar, so record ambiguity / conservative resolution. Stops do not guarantee exact fills.
9. Track all orders, fills, cancelled signals, end-of-day open positions, and incomplete data.

## Performance reports

- Number of sessions, sectors picked, candidate count and actual trades.
- Win rate, net and gross return, average win/loss, expectancy (R), profit factor.
- Max drawdown, worst consecutive losses, MFE/MAE and stop distance realised.
- Distribution of milestones (+1%, +2%, +3%, etc.) attained before stopping.
- Median latency from 09:35 to fill; fees, spread cost and slippage.
- By sector, by ticker, by month and by gap type.
- Compare to simple baselines: random eligible sector, top sector ETF buy, and a fixed +1% exit variant.
- Split development and out-of-sample periods; avoid tuning to the test months.

## Risk & verification gates

- Examine the impact of correlated positions when all three belong to the same sector.
- Confirm market-data subscriptions, IBKR scanner code support, order limits, stop mechanics, and local market/session calendar.
- Validate no use of future candles or revised sector members; ensure adjusted pricing is consistent.
- Paper trade with live archived scanner results before any consideration of deployment.
- **No live trades or bot deployment are authorised by this plan.**
