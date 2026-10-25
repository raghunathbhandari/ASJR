# Rudra Three-Candle Strategy — Research Specification v1.1
Updated: 2026-10-25 (UK). Research/backtesting only; not validated for live trading.

## Pattern on 15-minute RTH candles
Resample 5-minute regular US-market session candles in non-overlapping groups of three (OHLCV, volume SUM). For 1–23 Oct 2026 RTH 13:30–20:00 UTC (14:30–21:00 BST). Handle US/UK DST changes explicitly.
- C1 is prior 15m bar.
- C2 is GREEN (close>open), lower wick (open-low)>real body (close-open), sweeps C1 low (C2.low<C1.low), and reclaims it (C2.close>C1.low).
- C3 volume strictly greater than C2 total volume; preliminary scanner also requires C3.close>C2.close. Preserve these filters in reproducible tests.
- Proposed entry = C2 close; initial SL = C2 open. This entry occurs BEFORE fully known C3 volume: **look-ahead conflict**. Must either run descriptive/ex-post screening, or revise live-executable entry after C3 close and re-test; do not label ex-post patterns executed trades.

## R unit and profit-lock trailing SL
Price risk distance = C2.close-C2.open (positive).
R price-step = max(C2.close-C2.open, 0.001*C2.close) [minimum +0.10% of entry].
After an entry is actually filled, initial SL=C2.open; when +k*R step FIRST traded, move SL to entry+k*R step, k=1,2,3,... . Never lower the stop, no fixed take-profit unless explicitly requested. This is a same-level step trailing stop, not one-R lagging.
At exact 1R, move SL to 1R (not breakeven).
For tiny C2 bodies, +1R/+2R/+3R = +0.10/+0.20/+0.30%.
If a 5m candle touches new higher milestone AND relevant stop in the same 5m bar, ordering is unknown. Record as AMBIGUOUS, do not claim a profit. Require 1m/tick data and correct ordering for execution proof; account for fills, gaps, costs, slippage, and no overlapping trades as an explicit test assumption.
Reset trading day; no credit for price movement after an initial SL. Separately report ex-post **maximum price R excursion**, **target-touch frequencies**, and **executed trade outcomes**.

## October INTC first data study (Yahoo 5m, Oct 1–23)
Source: `Rudra-DDB/DataBridge/exports/data-2026102417101/INTC.csv`.
Three selected patterns 2 Oct (C2 18:15 BST; entry 119.9551 / SL 119.9460), 6 Oct (17:15; 114.1300/114.1200), 9 Oct (17:00; 105.3800/105.3600).
For R=max(body,0.1% entry), max future price-touch levels: 2R / 9R / 4R respectively (total 15R = sum of potential percentage steps +1.50%). All three reached 1R and 2R; two reached 3R. **Not realized profit**: original stops touched in first 5m C3 bar; event order unknown. Completed C3 volume not known at proposed entry.

## September INTC first data study (Yahoo 5m)
Source: `Rudra-DDB/DataBridge/exports/data-2026102520521/INTC.csv` (4032 extended-hours rows, 21 RTH dates).
65 sweep/long-wick patterns -> 33 green C2 -> 8 with C3 volume> C2 and C3.close>C2.close. All eight later reached 1R price; 7 later reached 2R; 6 later reached 3R, **without requiring that a stop was avoided**. Original SL first touched before 1R in 2 setups; 5 same-5m stop/1R order ambiguities; remaining setup had 1R before eventual original-stop touch but subsequent step-stop sequence ambiguous. Do NOT report 0 SL or 100% execution win rate.

## Ten-ticker September preliminary IBKR historical scan
Source: `Backtesting/BacktestData/IBKR/MarketData/5m/{TICKER}_5m.csv`; tickers AMAT GOOG INTC LRCX META MU NVDA PLTR SPY XOM; files 2025-10-02 through 2026-10-02. September only 21 sessions; 15m from 5m; ex-post C3 filter as above.
|Ticker|Signals|Later 1R touch|Later 2R touch|Later 3R touch|
|---|---:|---:|---:|---:|
|AMAT|5|5|4|3|
|GOOG|8|8|7|3|
|INTC|11|11|9|8|
|LRCX|10|10|10|10|
|META|12|12|12|12|
|MU|7|7|7|7|
|NVDA|9|9|9|7|
|PLTR|11|11|11|10|
|SPY|4|4|0|0|
|XOM|6|6|6|4|
|TOTAL|83|83|75|64|
Price-touch rates: 100.0%, 90.4%, 77.1%. Alternate fixed target theoretical **per-trade** sum at exactly 0.10/0.20/0.30% would be 8.30/15.00/19.20% only if ALL target-hitting trades executed and WON, disregarding larger-than-0.1% R and other losers; **NOT** realized P&L and not an actual valid fixed-R calculation for the full sample. Note some C2 body R >0.10%; use per-signal step for correct financial computations.
Difference between INTC IBKR 11 qualifying and Yahoo 8 requires audit (different feed/time alignment, candle conditions, missing bars).

## Next test must produce
Entry-fill mode explicitly post-C3 confirmation, date/session splits, nonoverlapping signals, 1m intrabar sequence, detailed trail log event order, initial SL hit before 1R, ambiguous bars, win/loss/flat, realized return, cumulative equal-sized trade returns, commission/slippage assumptions; compare Yahoo vs IBKR on matching period.
