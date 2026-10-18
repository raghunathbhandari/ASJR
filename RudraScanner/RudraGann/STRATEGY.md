## 2026-10-18 — OPERATIONAL HANDOFF AND VERIFIED DATA AUDIT

**First read:** [Rudra-Gann OPERATIONS.md](https://github.com/raghunathbhandari/ASJR/blob/main/RudraScanner/RudraGann/OPERATIONS.md) for verified data-source folders, imported CSV SHA256, basic audit results, GitHub→VPS bridge limitations, approved Discord/admin commands, safe SSH worktree commands, and precise Gann candle confirmation rules. As of Oct 18 user-confirmed audit: 627,688 real 1m rows, no malformed timestamps/duplicates/order/OHLC errors; 33 ASJR 5m session files. Gap/roll/resampling audit remains pending. **Data collection only until user authorizes backtest.**

---

## HISTORICAL NQ DATA SOURCES — VERIFIED 2026-10-18 (READ NEXT SESSION FIRST)

**New source identified:** public [kfccolonel1/BARS](https://github.com/kfccolonel1/BARS), source catalog [catalog.json](https://github.com/kfccolonel1/BARS/blob/main/catalog.json). Catalog says stitched 1-minute NQ futures, unadjusted/front-month, quarterly contract roll jumps and holiday/market-closure gaps. Third-party historical source: independently validate timestamps, OHLC integrity, gap coverage, roll discontinuity and permission to reuse before claiming a clean backtest. A rollover jump must NOT be interpreted as a Gann trade.

**Exact downloadable CSVs:**
- [2025 1-minute](https://raw.githubusercontent.com/kfccolonel1/BARS/main/NQ/1min/NQ_1min_2025-01-01_2025-12-31_stitched.csv): catalog 353,233 rows; NY 2025-01-01 18:00 through 2025-12-31 16:59.
- [2026 1-minute](https://raw.githubusercontent.com/kfccolonel1/BARS/main/NQ/1min/NQ_1min_2026-01-01_2026-10-08_stitched.csv): catalog 274,455 rows; NY 2026-01-01 18:00 through 2026-10-08 23:58.
- ASJR Yahoo NQ=F 5m per-day CSVs already at `RudraScanner/ResearchData/Gann/NQ_2026-09-DD_5m.csv` and `NQ_2026-10-DD_5m.csv` covering 33 Sep–Oct 16 sessions. **Do not silently merge third-party stitched futures with Yahoo continuous data**; prices can differ considerably near roll/throughout history.
- Other original historical sources: `raghunathbhandari/AlgoStrategy` repo, `AI_Chunks/NQ/data/external/Dataset_NQ_1min_2022_2025` (105 pieces, original archive ended ~Dec 11 2025), `NQ/data/NQ_5min_20260120_20260415.csv`, `NQ/data/NQ_1min_20260401_20260902.csv`.
- ASJR historical IBKR checkpoint importer (dated NQ futures) `RudraScanner/RudraGann/import_ibkr_1y.py` is an alternative where needed; live file is local research checkpoint, not GitHub until published.

**Copy source archive into ASJR:** `/root/trading/venv_new/bin/python RudraScanner/RudraGann/import_bars_sources.py` from a refreshed `/root/trading/ASJR-Gann` detached research checkout. This imports two source CSVs under `RudraScanner/ResearchData/Gann/Source/BARS/` using an isolated scratch Git clone/push; it does NOT modify live Chakra checkout. **Import is committed as code but source CSV transfer is PENDING until VPS prints `BARS IMPORT | SUCCESS | PUSHED TO ASJR` and the files are independently verified.** Avoid storing a repeated copy in the main repo if either file is >100MB GitHub limit; handle failure explicitly, do not assume saved.

**Backtest preparation:** resample 1m bars only if a full set of five real contiguous minutes is present for a 5m candle; 5m->15m/1H/4H with aligned exchange session boundary and candle completeness. Report coverage by month and preserve original timezone, provider and contract labels. Run frozen Gann pattern test only after the joined dataset passes integrity and rollover checks.

---

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

