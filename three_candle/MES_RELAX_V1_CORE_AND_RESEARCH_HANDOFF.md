# MES ThreeCandle Relax v1 — Core Idea, Visual Review and Research Handoff

**Updated:** 2026-11-03 (UK GMT)  
**Scope:** MESZ2026 December 2026 micro E-mini S&P 500 futures, 15-minute signal candles formed from IBKR 5-minute bars.  
**Status:** Research only; no live execution. Original V3 scanner, historical 5-minute CSV files and notebook remain unchanged.

## 1. Purpose and key principle

Develop a high-probability MES trading system while retaining *every* original candidate, including failures, to distinguish detection quality from profitable execution. Target for later out-of-sample validation: **50–60% take-profit hit rate** at a 2R target, positive net expectancy after commissions/slippage, and controlled maximum drawdown. This target has **not** been established.

Separate three levels:
1. **Raw V3 core:** identify candidates exactly as the existing implementation currently does; do not silently change.
2. **Relax research filters:** evaluate and rank candidates, record failure reasons. Keep all raw records.
3. **Revised parallel detection research:** evaluate missed or misclassified opposing-direction opportunities, with its own candidate IDs and parent/origin references. Do not label retrospectively recovered opportunities as historically executed trades.

## 2. Existing V3 / Relax core (what the original master actually measures)

Source: `three_candle/three_candle_learing.py`; MES rated master listed below.

- C1: reference candle; state machine preserves C1 while waiting for a sweep.
- C2 BUY: `C2.Low < C1.Low`; C2 SELL: `C2.High > C1.High`. A C2 sweeping *both* C1 extremes is currently treated as ambiguous/reset.
- C3 BUY currently qualifies when **C3.High > max(C2.Open, C2.Close)**; C3 SELL when **C3.Low < min(C2.Open, C2.Close)**. This is an *intrabar break*, **not** a required closing break.
- When a waiting candle breaks the C2 invalidation extreme, reset. If invalidation and confirmation occur in the same 15-minute OHLC candle, discard as ambiguous because intrabar event order is unknown.
- A confirmed C3 becomes the next C1. **Only one pending direction is tracked**, so an opposite-direction C2 may be missed while waiting on the old pattern.
- `C3_closes_beyond_C2_body` and `C3_directional_strength` are existing separate diagnostic fields and **are not mandatory in the current raw core**.
- Original V3 research diagnostics F3–F8 are retained; the 6-filter count and GOOD / REVIEW / WEAK labels are **pre-trade research descriptions**, not validated outcome ratings.
- Existing Balanced profile includes C3 body <0.10%, C2 directional wick/body >=0.25, and C2 RVOL20 >=0.30 (subject to warm-up).

### Source data / reproducibility

- `three_candle/data/MESZ2026_IBKR_5m_2026-09.csv`
- `three_candle/data/MESZ2026_IBKR_5m_2026-10.csv`
- `three_candle/results/MES_2026-09_10_ThreeCandle_RELAX_ALL_CANDIDATES_RATED.csv`
- `three_candle/results/MES_2026-09_10_ThreeCandle_RELAX_ALL_CANDIDATES_MASTER.csv`
- `three_candle/results/MES_2026-09_10_ThreeCandle_RELAX_MASTER_GUIDE.md`

Two-month raw core dataset: **593 candidates** (September 276; October 317). Preserve all source columns and all 593 rows; do not overwrite old CSVs. The user may later request a new versioned rated/outcome master.

## 3. Baseline 29–30 October preliminary independent signal replay

**Fixed for this study:** next available 5-minute OPEN after the **15-minute C3 has closed**; 1 MES ($5/index point); initial stop 5 MES points; target 10 points; move stop to entry (breakeven) after +5 points favorable movement; conservative stop-first in any ambiguous 5-minute OHLC bar; stop fill may worsen on a gap; before fees/slippage. Each candidate is evaluated separately, so trades overlap. Daily P/L figures are **not** realizable one-position portfolio performance.

| Day | Core signals | TP wins | TP rate | SL | BE | EOD partial | Summed points | Gross $ (1 MES) | Max realized equity DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-29 | 14 | 3 | 21.4% | 9 | 2 | 0 | -15.00 | -$75.00 | 25 points |
| 2026-10-30 | 12 | 6 | 50.0% | 3 | 2 | 1 (+2.75) | +47.75 | +$238.75 | 10 points |
| **Combined** | **26** | **9** | **34.6%** | **12** | **4** | **1** | **+32.75** | **+$163.75** | See note |

**Important:** Max realized drawdown figures above are calculated separately for each day. No combined floating/equity intratrade drawdown is claimed. A prior one-position/day-capped experiment (max four entries/day, stop after two consecutive losses) produced -10 points on Oct 29 and 0 points on Oct 30; this is materially different from independent candidate sums.

### Existing wick filter experiment (do not mistake for out-of-sample validation)

- `C2 directional wick/body >=2.0`: 13 candidates, 6 TP, **46.2%**, summed **+40 points**, independently evaluated.
- No filter: 26 candidates, 9 TP, **34.6%**, summed **+32.75 points**.
- These parameters were selected **after viewing the two days**; performance can be overfit and must be retested on unseen data.

## 4. User's visual findings — preserve as explicit research hypotheses

### Finding A — #570, 2026-10-29 07:00 UK: misclassified BUY; potential SELL C2

Original candidate #570: C1 05:00, C2 06:30, C3 07:00. Existing BUY trigger accepted because 07:00 **high 7765.50** exceeded C2 body top **7763.75** intrabar, although C3 **closed 7759.00** (below body top) and was bearish. Original BUY lost 5 points.

Opposing-direction interpretation:
- Candidate *SELL C1* at **06:45**: H 7762.00, L 7757.50, C 7760.75.
- *SELL C2* at **07:00**: H 7765.50 (sweeps C1 high +3.50), L 7757.00, C 7759.00.
- *SELL C3* at **07:15**: H 7761.25, L 7753.75, C 7757.25; closes below the C2 body bottom 7759.00.
- **C2 sweeps both C1 high and low**, so the existing ambiguity rule would also reject it in a new-start scan. SELL C2 upper wick/body approximately 1.57×, below the proposed >=2× strong-wick threshold.
- Treat this as a **missed structural SELL hypothesis**, *not* an approved strict strong-wick trade. Study bidirectional concurrent-state tracking and directional resolution of two-sided sweeps.

### Finding B — #582, 2026-10-30 00:00 UK: missed alternative SELL

Original candidate #582 was a BUY and lost -5 points. A separate prospective SELL pattern can be reconstructed:
- C1 **2026-10-29 23:45**: H 7707.50, L 7698.75, C 7706.50.
- C2 **2026-10-30 00:00**: O 7706.25, H 7709.00, L 7701.75, C 7705.50; high sweep +1.50 points; upper rejection wick 2.75 pts / body 0.75 pts = **3.67×**.
- C3 **00:15**: O 7705.25, H 7705.25, L 7697.75, C 7700.00; closes below C2 body and low.
- Historical hypothetical SELL entry **00:30** at 7700.00, SL 7705.00, TP 7690.00 reached later at around 00:55 in raw 5-minute candles. **Not an original core SELL**; also fails an absolute >=2.0-point C2 sweep rule (+1.50). Do not quietly add this WIN when calculating old baseline or claim it meets all new filters.
- Avoid double counting or counting a losing BUY and an alternative SELL as simultaneously executed on one-position accounts.

### Finding C — #577, 2026-10-29 14:45 UK: repeated large two-sided wicks = congestion

Original SELL #577 had C2 directional wick/body 2.50× yet lost -5 points. Across the five 15-minute bars ending in its C3 (13:45, 14:00, 14:15, 14:30, 14:45) **three** bars had **both** upper and lower wicks >= body:
- 13:45: body 0.25, upper 6.75, lower 14.00.
- 14:00: body 1.50, upper 12.25, lower 7.00.
- 14:15: body 8.00, upper 2.75, lower 2.75.
- 14:30: body 2.50, upper 6.25, lower 4.75.
- 14:45: body 9.50, upper 1.25, lower 10.25.
- Use last **five completed 15m candles**, including C3, as known at entry. User's **latest** direction: **if >=2 of last 5 candles have out-of-range long wicks, WAIT / NO TRADE**. This supersedes the prior preliminary >=3-of-5 rule.
- **Definition to formalize:** The earlier backtest specifically used **both upper AND lower wick >= max(real body, 0.25 MES pt)** for a flagged candle. The user said "if 2 candle has wicks out of range" without explicitly specifying whether *either* wick qualifies or *both* must be long. Do **not** silently conflate these. Record both interpretations as separate testable metrics and get the rule definition settled before deployment.
- Critical conceptual distinction: recurring wick rejection may indicate **chop/indecision**, not necessarily increased absolute volatility; separately measure ATR-normalized range.
- The earlier **>=3** filter combined with C2 wick >=2 yielded **8 candidates, 5 TP, 62.5%, +40 points**. This result **must not** be attributed to the newly requested **>=2** policy. For comparison on these 26 raw outcomes, implementing **>=2 flagged candles with both upper and lower long** together with C2 wick>=2 gave **4 candidates, 2 TP, 50.0%, +15 points**. Sample is insufficient; no claim of proved improvement.

### Finding D — #580, 2026-10-29 20:30 UK: weak BUY sweep, separate bearish displacement idea

Original BUY #580: C1 20:00, C2 20:15, C3 20:30; **C2 sweep depth +1.25 points**, C2 directional lower wick/body **1.45×**, C2 RVOL20 0.59×, C3 7715.50 did **not** close above C2 body top 7717.50; lost -5 points.
- User judged the small sweep and comparatively weak rejection insufficient quality for a BUY; propose minimum absolute sweep depth **2.0 MES points** separately from >=2× directional wick/body.
- However user also identified possible bearish continuation: 19:45 C1 high 7756.00; 20:00 bearish displacement candle O 7754.00, H 7758.00, L 7712.00, C 7715.00; 20:45 close 7710.25 below C2 body bottom. The bearish C2 **upper wick/body is only ~0.10×**, therefore this is **not** a strong-wick reversal and must be separately researched as **bearish displacement continuation**.
- 20:45 falls near a futures market break; next available fill could be delayed and/or gap. Do not presume a valid same-session or executable backtest without replay.

### Finding E — #30 Oct 18:45 low 7557.75: missed reversal-base formation

At 18:45 UK a wide-range candle swept the earlier 18:30 low of 7560.00, reaching 7557.75, but also swept 18:30's high. It closed 7575.25. The 19:00 candle closed 7587.25, above 18:45 high 7579.25; then 19:15–19:30 retained higher lows, and 19:45 broke up with high volume and close 7612.75. Existing core rejected the two-sided sweep and produced no BUY in this base. This is a **research case**, not a proven executable profit with 5-point stop; an entry at 19:15 after confirmation would have had large downside risk into the subsequent pullback.

## 5. Proposed research profiles (do not merge into the original core)

### A. Reversal / sweep-rejection profile

- Preserve directional C1/C2 sweep structure, with new parallel BUY+SELL state trackers and separate ambiguity handling.
- C2 **directional rejection wick / real body >= 2.0** (user-requested starting threshold; guard tiny/zero body denominators).
- C2 **absolute directional sweep >= 2.0 MES index points** is a proposed filter **in need of validation**; the historical candidate #582 alternative SELL swept only 1.5 points, so applying >=2 excludes it. Keep borderline cases.
- C3 must **close beyond the C2 BODY boundary** and have directional close:
  - BUY: `C3.Close > max(C2.Open,C2.Close)` AND `C3.Close > C3.Open`;
  - SELL: `C3.Close < min(C2.Open,C2.Close)` AND `C3.Close < C3.Open`.
- Store intrabar body-break separately, preserving evidence of discarded signals.
- C2 RVOL20 >=1.0 or >=1.2 can be tested as supplementary filters, NOT fixed.
- Measure sweep-depth points, wick points, wick/body, RVOL, C3 close strength, confirmation delay, position relative VWAP/EMA, regime, time/session and MFE/MAE.

### B. Wick-congestion WAIT (user latest rule)

- Calculate **last 5 completed 15m candles** ending at candidate C3.
- Flag individual candles with excessive wicks **relative to their body**. Version **BOTH_WICKS** uses upper>=max(body,0.25pt) AND lower>=max(body,0.25pt). Also compute **EITHER_WICK** independently as a sensitivity check.
- **NO TRADE / WAIT when flagged count >=2 of 5** under whichever definition is adopted. The threshold is the user's latest explicit instruction. Do not use stale >=3 count in new versions.
- Candidate C2 can itself have a large *directional* rejection wick; a single strong wick is desired, while a concentration of long, two-sided wicks over several candles can mean congestion. They are different tests.
- Validate 2-of-5 vs 3-of-5 on larger data before enabling live alerts.

### C. Bearish/bullish displacement continuation profile (separate logic)

- Do NOT loosen the reversal strong-wick rule simply to include large bearish C2 displacement bars.
- Study a separate continuation setup with momentum body, range expansion, preceding sweep, context/structure and a subsequent close-through, with separate entries and realistic stop sizing.
- Classify #580-related bearish idea here, pending validation.

### D. Parallel bidirectional detector / state priorities

- Maintain independently tracked pending BUY and SELL C2s rather than a single state that locks out opposing opportunities.
- Capture both-sided sweeps as separate **candidate variants** with a confidence/resolution tag rather than auto-accepting them.
- Avoid unbounded duplicate nearby signals: label replacement/competing hypotheses; deduplicate at execution level, using consistent one-position rules.
- **Causal only:** C2 status known only after C2 close, confirmation after C3 close; no future candles used in signals; replay 5-minute execution realistically.

## 6. Proposed audit fields to append to a new versioned master (not overwrite original)

- `original_candidate_id`, `research_candidate_id`, `detector_version`, `signal_origin` (original / recovered-opposite / displacement / base), `replaces_candidate_id`.
- `c2_sweep_points`, `c2_directional_wick_points`, `c2_directional_wick_body`, `c3_closes_beyond_c2_body`, `c3_directional_close`.
- `prev5_both_wick_count`, `prev5_either_wick_count`, `prev5_congestion2_both`, `prev5_congestion2_either`, `atr14`, `atr_normalized_range`.
- `pass_wick2`, `pass_sweep2`, `pass_c3_close`, `pass_congestion2`, `reject_reason`, `session`, `ema20/200_alignment`, `vwap_alignment`.
- `entry_time_uk`, `entry_price`, `stop`, `target`, `exit_time_uk`, `exit_price`, `exit_reason`, `mfe_points`, `mae_points`, `gross_points`, `net_dollars_after_costs`, `is_overlapping`, `portfolio_executable`.

## 7. Required follow-up research

1. Replicate raw 593-candidate master and replay outcomes with frozen assumptions and data-quality checks.
2. Compare baseline vs strong wick >=2, sweep >=2, C3 close rule, **latest congestion >=2/5**, and combinations; group by BUY/SELL and session. Report winners removed as well as losers removed.
3. Build separate recovered opposite-direction detector; explicitly verify #570/#582 and two-sided sweep base on 30 Oct without hindsight.
4. Test displacement continuation independently of sweep-reversal; annotate #580, especially next-session availability.
5. Validate across Sep/Oct with **time-ordered holdout** and eventually fresh unseen months; do not optimize solely for 29–30 Oct.
6. Report TP-hit rate, average R, summed independent signal points, one-position net P/L, commission/slippage, drawdown, candidate count and confidence intervals. **No guarantee of 50–60%**, and high hit rate alone does not imply edge.

## 8. Git and code safety

- **No changes** to `three_candle/three_candle_learing.py` original core, `three_candle/test_three_candle.ipynb`, IBKR September/October source CSVs or historical master datasets.
- This handoff is documentation only. Any proposed code should live in a separate versioned research module and be tested/diffed before merge.
- VPS safe sync after GitHub commit: `git fetch origin && git merge --ff-only origin/main`. Never force-push or open a merge editor for normal synchronization.


## 9. Structure-first code added 2026-11-03 (R&D; edit-friendly)

New standalone source: [mes_relax_structure_first_v1.py](./mes_relax_structure_first_v1.py) (commit `fd699a7`). **Original V3 unchanged.**

The detector evaluates **confirmed market structure first** (unique 2-left/2-right swing high/low; pivots only after their right-hand candles close), then prior confirmed price levels, then C1/C2 sweep candidates, and then **four independent checks**:

1. `pass_wick2`: C2 directional rejection wick / max(real body, 0.25pt) >= **2.0**.
2. `pass_sweep2`: C2 sweeps C1 high/low by >= **2.0 MES points**.
3. `pass_c3_close`: C3 **closes** beyond C2 body in trade direction, and C3 candle itself closes in that direction.
4. `pass_wick_congestion`: last **5 completed 15-minute candles**, including C3, must have **fewer than 2** candles with excessive wicks. Current implementation: **both** upper and lower shadows >= max(body, 0.25pt). Alternate `EXCESSIVE_WICK_MODE="either"` is exposed separately.

All parameters are grouped at the very top of the Python file, with comments for manual edits. BUY and SELL hypotheses are evaluated in parallel; confirmed HH+HL or LH+LL classification is a gating check by default, and ranging/unknown => WAIT. A prior swing-level touch is recorded; hard level gating is off initially because the interpretation needs calibration. C1/C2 are deliberately consecutive; C3 may arrive within 3 bars. This is a **new candidate universe**, not the original 593-signal persistent-C1 scanner. No signal outcome should be compared as if these universes were identical.

The revised code is a **research scanner**, not an execution or 5m replay backtester. It retains WAIT rows via `--all` and can export CSV. It does **not** automatically classify strong-body displacement continuation (a separate future research path). It is not connected to a live trading bot and sends no orders.

### Commands after safe VPS sync

```bash
cd /root/trading/ASJR
git fetch origin
git merge --ff-only origin/main
python3 -m py_compile three_candle/mes_relax_structure_first_v1.py

# View every candidate and rejection reason (including WAIT)
python3 three_candle/mes_relax_structure_first_v1.py --date 2026-10-29 --all
python3 three_candle/mes_relax_structure_first_v1.py --date 2026-10-30 --all

# Show only passing candidates; optional CSV, never overwrite source masters
python3 three_candle/mes_relax_structure_first_v1.py --date 2026-10-30 \
  --output three_candle/results/MES_structure_first_2026-10-30_research.csv
```

**Validation status:** GitHub source commit completed; executable compilation and full 5m outcome backtest are still to be run on a Python environment holding the IBKR CSVs. Do not claim an improved win rate from code creation alone.


## 10. Confirmed nine-method order and all/good visual plots (2026-11-04)

**User-approved arrangement:** `candle_detect_core()` → `market_structure()` → `swing_sr_lines()` → `volume_detect()` → `wicks_detect()` → `daily_range_check()` → `display_other_metrics()` → `higher_timeframe_support()` → `Liquidity_area_detect()`.

New commented research orchestrator: [mes_relax_pipeline_v1.py](./mes_relax_pipeline_v1.py). It imports the prior [mes_relax_structure_first_v1.py](./mes_relax_structure_first_v1.py) for IBKR loading, 15m resampling and pivot helpers. Neither source CSVs nor the original V3 core is touched.

- `candle_detect_core()`: first valid C1/C2 sweep and C3 directional **close** confirmation. BUY/SELL analysed independently. Its TRUE output is a **raw candidate** (not a trade).
- `market_structure()`: confirmed 2-left/2-right swing pivots; alignment required to be GOOD by default.
- `swing_sr_lines()`: recent confirmed swing S/R levels and proximity; plot/context first, optional hard gate.
- `volume_detect()`: historical 20-bar RVOL20; informational initially.
- `wicks_detect()`: C2 directional wick/body >=2x plus last-five-candle excessive-wick rule (>=2 of 5 => WAIT); documented default requires both upper/lower shadow >= body; adjustable.
- `daily_range_check()`: day-to-date high/low and remaining distance to extreme; informational, NOT forecast.
- `display_other_metrics()`: C1/C2/C3 price/time/range labels.
- `higher_timeframe_support()`: last fully completed H1 bar direction; informational until user enables gating.
- `Liquidity_area_detect()`: confirmed swing liquidity touch; informational initially.

**Two separate chart collections:** `--plot-all` creates a multipage PDF of **every CORE-TRUE candidate**, including later WAIT. `--plot-good` plots **only candidates passing all currently required filters**. `--plot-both` creates both. Each page keeps the prior dark candlestick styling: green/red candles, highlighted C2, C1/C2/C3 labels, blue dashed reference entry, red dashed reference stop, purple reference target; all labels in UK time. Entry/SL/TP are illustrative levels; charts DO NOT constitute a 5m fill backtest or prove profitability.

```bash
cd /root/trading/ASJR
git fetch origin && git merge --ff-only origin/main
python3 -m py_compile three_candle/mes_relax_pipeline_v1.py
python3 three_candle/mes_relax_pipeline_v1.py --date 2026-10-29 --plot-both --show-wait
python3 three_candle/mes_relax_pipeline_v1.py --date 2026-10-30 --plot-both --show-wait
# PDFs and audit CSVs: three_candle/results/MES_relax_v1_review/
```

Dependencies: matplotlib for PDF charts, Python 3.9+ standard library for scanning (ZoneInfo). **Changes are committed but have not yet been executed against the VPS IBKR datasets.** Verify candidate results and chart rendering before accepting as a final backtest.
