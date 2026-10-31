# AI SESSION HANDOFF — 31 October 2026
## Rudra-Gold V2 and Rudra NQ Three-Candle V2 — independent research tracks

**Canonical status:** This note records today's reproducible SSH outputs, research definitions, code locations, limitations and lessons. Keep **Gold and NQ entirely separate**. Neither strategy's filters, entries, stops, or exits may silently carry into the other.

### A. Gold V2 — frozen historical research version

Source: `three_candle/data/multi_asset_5m/GOLD_20260901_20261031_5m_UTC.csv` (Yahoo GC=F, 5m UTC).
Use 15m candles for detecting sweeps and confirmed trailing swing pivots, 5m for entry/exit execution approximation.

Frozen rules: C2 is turning-point sweep; detection in `detect_gold_v2_swings.py` uses prior 8 completed 15m highs/lows, C2 range ≥ 1.0 ATR14, sweep depth ≥ 0.5 ATR14, C1 body/range ≥ 40%, C3 directional body/range ≥ 60% and C3 extreme nonviolation; ATR excludes C2/future bars. **Frozen version** uses first price crossing *after C2 closes* of **BUY: max(C2 Open,Close); SELL: min(C2 Open,Close)**; initial stop at **C2 wick low for BUY / wick high for SELL**; confirmed 2-left/2-right 15m swing pivot trailing, with the +/− $0.20 pivot offset as coded. Important: selection by C3 confirmation before intrabar entry can cause look-ahead (see below).

Verified by user on VPS after pulling GitHub:
```
/root/trading/venv_new/bin/python three_candle/gold_v2_frozen_three_reference.py --date 2026-10-30
```
| C2 (UK GMT) | Side | Entry | Wick stop | Exit | Gross simulated P/L |
|---|---|---:|---:|---:|---:|
| 05:30 | SELL | 4011.80 | 4021.20 | 3997.80 | +0.3490% |
| 07:45 | BUY | 3990.00 | 3974.70 | 3974.70 | −0.3835% |
| 08:45 | SELL | 3998.60 | 4009.20 | 3894.20 | +2.6109% |
| **Reference summed** | | | | | **+2.5764%** |

**3/3 reached +0.20% subsequent favourable price excursion (research only)**; **2/3 swing-trailing exits positive = 66.67% simulated realised win rate**. NEVER describe the +0.20% movement statistic as 100% winning trades. The 07:45 BUY reached ~+0.481% favourable move but eventually exited at wick stop for −0.3835% in this frozen version. Initial risks for these three were 0.234%, 0.383%, 0.265%; all exceed the historical 0.20% cap.

Monthly same-version backtest, verified by user on VPS:
```
/root/trading/venv_new/bin/python three_candle/gold_v2_monthly_frozen_replay.py --month 2026-10 --out three_candle/results/gold_v2_october_replay.csv
```
- October 2026: **27 confirmed patterns, 26 simulated entries, 14 winners, 12 losers, win rate 53.85%, gross summed trade returns +5.8591%**.
- **8 trades** meet ≤0.20% wick-stop risk cap, **gross summed result −0.0016%** for those eight.
- The monthly code explicitly asserts 30 Oct gross sum **+2.5764%**, matching the frozen single-day code. This check prevents another mismatched-run comparison.
- +5.8591% is NOT compounded capital return, NOT risk-compliant portfolio return, and NOT executable validated profit: historical C3-selected candidates may enter during C3 (look-ahead/selection leakage), overlapping trades, fees, slippage, and five-minute OHLC ordering still unaccounted for.

**Separate Gold body-stop experiment**: `three_candle/research_gold_v2_early_body_cross.py`.
- Same C2 body-edge entry but **opposite C2 BODY edge for SL**, not wick extreme. Gold C2-only scanner 30 Oct found **12 C2 candidates, 7/12 showed unsequenced +0.20% later movement, 5 simulatable fills (3 wins, 2 losses), 5 same-five-minute entry/stop ambiguities, 2 no triggers**.
- Three handpicked C3-confirmed 30 Oct references: 3/3 later +0.20% movement, 2 assessable simulated winners and **07:45 BUY unresolved intrabar**; 08:45 SELL had ~0.215% body stop risk over the 0.20% cap.
- Crucial: **body-stop and frozen wick-stop version results are NOT interchangeable**. Never replace frozen 07:45 wick-stop loss with unverified body-stop win, or mix body-stop results into the frozen +2.5764%/+5.8591%.
- Body-based stop minimum (e.g. 0.08%) and 0.20% cap changes are experimental ideas, not adopted validated performance.

### B. Rudra NQ Three-Candle V2 — filtered research, NOT Gold strategy

**Name locked:** *Rudra NQ Three-Candle V2*. **Do not use Gold V2 or NQ EMA Bounce rules**.

Files:
- `three_candle/three_candle.py` — existing NQ Three-Candle scanning/backtest model.
- `three_candle/export_two_month_signal_matrix.py` — rebuilds NQ 2026-09 + 2026-10 matrix and prints fixed V2 summary with hypothetical 1R/2R gain scenarios.
- `three_candle/results/NQ_2026-09_10_signal_matrix.csv` — output from VPS (generated locally; don't assume Git-tracked).
- Source data: `three_candle/data/NQ_2026-09_5m_UTC.csv` and `three_candle/data/NQ_2026-10_5m_UTC.csv`.

NQ V2 **proposed independent filters**, as currently coded:
- BUY: C3 Body_pct ≥0.06, C3 Wick_body_ratio ≤1, C2 Lower_wick_pct ≥0.06.
- SELL: C3 Upper_wick_pct ≥0.05, C2 Range_pct ≥0.12.
- Preserve separate BUY/SELL signal detection/execution logic in existing `three_candle.py`. Filters are selected from research and need forward testing.

VPS user-verified NQ matrix output (both months combined):
```
CREATED .../NQ_2026-09_10_signal_matrix.csv | 821 signals | 245 columns
FILTERED True: BAD 68, GOOD 65, WEAK 65
```
- Raw NQ signals **821**, V2 filtered **198**.
- Historical target-touch **at least 1R: 130/198 = 65.66%** (GOOD 65 + WEAK 65).
- Historical target-touch **at least 2R: 65/198 = 32.83%** (GOOD 65).
- 68/198 <1R.
- **These are target-reach research statistics, not verified realised win rate**.
- At session end, a later commit added printed scenario gross gain/loss in `export_two_month_signal_matrix.py` (fixed 1R / fixed 2R; model every target miss as -1R using entry-to-stop %). **No VPS output confirming those gain percentages has yet been provided**. Do not invent or label a gain figure verified.
- Note the matrix source spans September AND October, despite output filename beginning `NQ_2026-09_10`.

SSH:
```bash
cd /root/trading/ASJR-Synced
git pull --no-rebase --no-edit origin main
/root/trading/venv_new/bin/python three_candle/export_two_month_signal_matrix.py
```

### C. Lessons/QA gates from today

1. **One strategy, one version, one comparable result.** The initial Gold month test used post-C3-close entries whereas the Oct 30 frozen script used earlier C2 body-edge crossings. That mismatch produced +2.1517% vs frozen 30 Oct +2.5764%; correcting monthly entry logic yielded +5.8591% and the frozen-day consistency check.
2. **Never substitute NQ rules with Gold rules.** The mistakenly added NQ cross-asset Gold-style script was deleted from GitHub. NQ V2 has its own filters and data. The standalone historical NQ EMA Bounce strategy is unrelated.
3. **Always print complete summary each run**: period, model/version, detected/filtered signals, entries/no-triggers, winners/losers, win-rate definition, gross gain %, fee assumptions, risk-compliant subset, ambiguities and warnings. `export_two_month_signal_matrix.py` now prints modelled 1R/2R gain scenarios. Don't equate hypothetical targets with realised P/L.
4. **Price excursion vs actual sequence**: a candle touching +0.20% later does not establish target-before-stop ordering, particularly with entry and body-stop touched in the same 5m bar. Mark ambiguous and obtain 1m/tick data.
5. **Causal detection**: selecting setups after C3 and entering during C3 is not a valid prospective backtest. A proper causal early-entry scanner should consider ALL C2 candidates at C2 close, then follow triggers without using C3-close outcome to filter them.
6. **GitHub write hygiene**: one attempted edit inserted literal `\\n` sequences into Python and caused SyntaxError. Fixed in a later commit. Always compile-check before reporting ready; on VPS use `/root/trading/venv_new/bin/python -m py_compile path.py`.
7. **VPS command convention**: shell may not have `python` alias. Use `/root/trading/venv_new/bin/python`; pull via `git pull --no-rebase --no-edit origin main` (avoids interactive merge editor).
8. **Timestamp convention**: dataset is UTC; reports for UK must convert appropriately (BST before 25 Oct 2026, GMT thereafter).
9. **Do not infer portfolio gains from sum of trade return %**: overlapping positions, position size, futures multipliers, commissions, rolling contract details and margin are still required.

### D. Closure / next-session priorities
- Gold: lock frozen research baseline, avoid rewriting it. Next research is *causal* C2-only pattern evaluation, tick validation, Gold-specific risk tests, September OOS and a fee-aware portfolio simulation.
- NQ: confirm fixed summary prints from updated script and record 1R/2R hypothetical gross percentages only when VPS output supports them; develop true executable backtest independently of Gold.
- Both: maintain separate README/results/strategy names; verify code with py_compile and small reference outputs before declaring a result final.
