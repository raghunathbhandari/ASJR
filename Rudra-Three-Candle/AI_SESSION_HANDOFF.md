# RUDRA THREE-CANDLE — AI SESSION HANDOFF
As of Sunday 25 October 2026 UK, resumed testing intended Monday 26 October.

## User decisions to preserve verbatim in logic
- Pattern C1 reference, C2 green lower-wick liquidity sweep/reclaim, C3 higher volume, confirm price.
- Entry designated C2 CLOSE, stop C2 OPEN.
- **Minimum 1R profit target distance = 0.10% of entry**, regardless of tiny C2 body; otherwise use full C2 body. 2R=2 steps, 3R=3 steps.
- On touch +1R STOP MOVES to +1R, touch +2R STOP MOVES to +2R, etc indefinitely. No forced exit at 3R.
- User wants summary of signals, win/loss, actual gain%, success%; clearly explain price-touch vs executed outcome.

## Repo and exact files
Repo `raghunathbhandari/ASJR`; study data branch `rudra-data-results` (do NOT commit exports to live main).
1. Sept INTC Yahoo (21 sessions; 4032 5m extended rows): `Rudra-DDB/DataBridge/exports/data-2026102520521/INTC.csv`; status `results/data-2026102520521.json` SUCCESS.
2. Oct INTC Yahoo (17 sessions, 3018 5m extended rows): `Rudra-DDB/DataBridge/exports/data-2026102417101/INTC.csv`; status `results/data-2026102417101.json` SUCCESS.
3. Existing 10 ticker IBKR historic dataset 2025-10-02 to 2026-10-02: `Backtesting/BacktestData/IBKR/MarketData/5m/{AMAT,GOOG,INTC,LRCX,META,MU,NVDA,PLTR,SPY,XOM}_5m.csv`. Matching 15m 1h 4h files.
4. **NEWS at handoff**: Oct 1–23 missing nine tickers *now successfully imported*: `Rudra-DDB/DataBridge/exports/data-2026102520591/{AMAT,GOOG,LRCX,META,MU}.csv`; `.../data-2026102520592/{NVDA,PLTR,SPY,XOM}.csv`. Both result JSONs report SUCCESS, checked after previous response: `results/data-2026102520591.json`, `results/data-2026102520592.json`. **October 10 ticker expanded backtest is now data-ready but NOT yet run.** Do not claim completed Oct multi-ticker results.
5. Sample first 3 Oct INTC: Oct2 2R price touch; Oct6 9R; Oct9 4R (peak price excursion; target-touch rates 3/3 1R 3/3 2R 2/3 3R, no verified profits). 15R cumulative peak excursion corresponds to +1.50% as 0.10% per step, but three stops also touched same five-minute C3 bar.
6. September INTC Yahoo 8 ex-post patterns; price reach 8/8 1R, 7/8 2R, 6/8 3R. Not zero confirmed SL.
7. September 10-ticker IBKR 83 patterns, 83 1R reach, 75 2R reach, 64 3R reach; see STRATEGY.md full table. '83 target touches' not 83 wins. Prior answer +8.30%, +15%, +19.20% are *misleading* naïve fixed R scenario totals; not realized PnL and omit stop/oversized-step/invalid entry effects. Correct urgently with actual chronological exits.

## Critical learning for next AI session
DO NOT use future highs through day's close to label a signal profit: initial SL may be hit beforehand. 5m OHLC of C3 may touch SL and 1R with unknown order; needs finer data. Completed C3 volume is future knowledge relative to C2 close: choose a causal trade entry after confirmation and re-backtest; maintain ex-post indicator mode separately. Avoid reporting 100% true win rate just because all later highs crossed 1R.
UK times: during Sept/Oct 1–23 2026 RTH 14:30–21:00 BST = 13:30–20:00 UTC. DST changed 25 Oct UK; US switches 1 Nov: account for DST when continuing.
The IBKR 5m files cover most Sep but only Oct1–2; October FULL Yahoo nine-ticker imports above solve coverage. The historic data was read with GitHub REST `https://api.github.com/repos/raghunathbhandari/ASJR/contents/Backtesting/BacktestData/IBKR/MarketData/5m/AMAT_5m.csv?ref=rudra-data-results` or connector fetch_file for smaller exports. GitHub fetch_file may return empty on ~3MB file, use `mcp__GitHub__fetch` on contents URL.
Repro issue: September INTC 11 IBKR vs 8 Yahoo signal discrepancy, audit source dates/volumes/candle rounding carefully.
No current trading orders. User wants reproducible backtest, master documentation, learning and clear handoff.
