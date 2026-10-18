# Rudra-Gann Strategy — V1 Research (2026-10-18)

## Objective
NQ=F horizontal Gann levels + **mandatory bearish/bullish candle pattern** confirmation; test Oct 16 before testing one month. Separate research code; no bot, broker, alerts, or live trades.

## Gann formula
At fixed 1x index-price scale: for positive integer n, level = n² when n is odd, and n²+1 when n is even. Exact 1x multiplier is a research assumption. Relevant Oct 16 levels: 29,929 and 29,585. Do not optimize scale after seeing outcomes.

## Marked reference setups (New York EDT)
- First: 09:30 interaction with 29,929, retest around 10:30–10:45, **10:50 bearish reversal candle**. OHLC = 29,934.75 / 29,944 / 29,836.75 / 29,839.75.
- Second: 13:40 approach to 29,585 (high 29,574.25, gap 10.75), **13:45 bearish reversal/entry-designated candle**. OHLC = 29,532.75 / 29,548.75 / 29,489.25 / 29,493.25.
- The user's designation of 10:50 and 13:45 as **entry candles** is preserved as *visual labels*. However, a pattern cannot be confirmed at that candle's open or before its high/close are formed. Backtest executes after confirmation at the NEXT 5-minute open; same-candle opening entry plus stop based on that candle's future high is LOOK-AHEAD and may not be called a realized trade. A separate optional intrabar trigger requires earlier 1-minute/tick evidence and a stop known BEFORE entry.
- Earlier claims of a 13:45-open fill at 29,532.75 with stop 29,549 based on its later high, and TP from its later low, are invalid as executable backtests. The 10:50 bar is not an entry at its open under candle-close confirmation.
- **Timeframe distinction:** 5-minute candle pattern signals using the supplied 5-minute data; 15-minute context optional. The 10:50 and 13:45 samples are **5-minute**, not 15-minute patterns.

## V1 SELL research rules (fully deterministic)
1. Price makes a downward close-cross of Gann level (previous close >= level, current close < level); remember breakout for at most 24 subsequent 5m bars.
2. Subsequent candle revisits the level within ±15 index points; permit wick/sweep past line by up to 25 points. Rejection/retest defined by high >= level-15 and high <= level+25, candle close < level. Set `armed` after that candle. A rally too far over the level invalidates arm.
3. Candle pattern confirmation must occur AFTER the retest (or on the retest bar itself after it closes): bearish candle with close < open, real body >= 40% of high-low range, close in bottom 35% of range; close below level or beneath the retest area's close. If none appears in next 4 candles, skip.
4. **Execution** next candle open, SELL. One position at a time. SL one NQ tick (0.25) above pattern candle high (known upon confirmation). Target entry - 2 × risk. Skip risk <=0 or >150 points.
5. Conservatively stop-first when a 5-minute bar's high and low cross both stop and target; if neither hit by dataset end mark-to-market at last close. No slippage, fees, spread or contract roll in initial study.
6. No short from a Gann touch alone. No future information in signals.
7. Distinguish price proximity tolerance (default 15), overshoot (25), lookback (24 bars), confirm window (4 bars), min body/range (0.40), maximum close position (0.35), SL buffer (0.25), RR (2).
8. All timestamps in America/New_York, convert separately to UK time when reporting.

## V1 BUY mirror (for future testing)
Upward close-cross, retest as support, bullish body >=40%, close in upper 35%, SL below confirmation candle, enter next bar open, TP 2R. Do not conflate with shorts.

## Audit and next steps
- Source: `RudraScanner/ResearchData/Gann/NQ_2026-10-16_5m.csv` verified 203 5m candles, NY 00:05–16:55 Oct 16. Some sessions start before 00:05 or extend after 16:55; use available bars only.
- Run `python -m unittest RudraScanner.RudraGann.test_strategy -v` in a clean checkout.
- Run `python -m RudraScanner.RudraGann.strategy` to report signal/entry/exit summaries.
- One-day examples are **not** a robust strategy validation. Freeze thresholds before one-month out-of-sample testing and compare against ordinary support/resistance baselines.
- Deployment: GitHub writes do not update the diverged live VPS checkout; use isolated checkout. Do not change Chakra or force merge Git.

