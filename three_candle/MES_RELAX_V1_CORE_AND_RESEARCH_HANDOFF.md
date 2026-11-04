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


## 11. Confirmed original-learning plotting layouts (2026-11-04)

Updated `mes_relax_pipeline_v1.py` with **two separate implemented plotting functions**, preserving the original learning-style dark candlestick design:

1. `plot_candidates(bars, rows, outpath, title)`: **ONE full-range chart per requested date/range**, every CORE-TRUE candidate marked by a **purple dot on C2** (below BUY C2 low, above SELL C2 high). Includes price candles and confirmed swing support/resistance. Prints all core candidates, GOOD and WAIT. Exports `MES_<date>_ALL_CANDIDATES.png`.
2. `plot_good_candidates(bars, rows, outpath)`: **ONE GOOD SIGNAL PER PAGE**, preserving local candle context, explicitly labelled C1/C2/C3, highlighted C2, blue ENTRY reference, red SL reference, purple TP reference, price labels and swing S/R. Exports `MES_<date>_GOOD_CANDIDATES.pdf`.

The old learning `plot_signal_candidate()` marked BUY C2 green and SELL C2 red; purple is the **user-requested MES colour override**. The old `plot_signal_passed()` and `plot_signal()` used individual full-history charts; new GOOD views use a **focused candle context around one signal** for legibility, matching the requested one-signal-per-chart rule.

The **reference** ENTRY uses C3 closing price, and stops/targets use 5/10 points around it. It is not represented as a next-5-minute actual fill. No profitability result is claimed by these plots. Original V3/learning notebook unchanged.


## 12. Original learning-compatible MAIN method (2026-11-04)

The MES research pipeline now exposes the same **method names** as the first learning module, so notebook usage is familiar:

```python
from mes_relax_pipeline_v1 import (
    three_candle_signal_learning,
    plot_signal_candidate,
    plot_signal_passed,
)

result = three_candle_signal_learning("MES=F", "2026-10-29", "2026-10-30")
plot_signal_candidate(result)   # ONE chart: purple dots on all candidate C2s
plot_signal_passed(result)      # ONE chart per GOOD signal: C1/C2/C3, entry/SL/TP
```

- `three_candle_signal_learning(tiker,datefrom,dateTo)` is the **main public function**, same spelling and signature as `three_candle_learing.py`. It returns `MESLearningResults`, a **list of dictionaries with attached candle data**, not pandas DataFrame, so the output format is NOT identical to the original learning module.
- `plot_signal_candidate(result)` calls `plot_candidates(...)` internally.
- `plot_signal_passed(result)` calls `plot_good_candidates(...)` internally.
- `main()` remains the CLI entry point used by `python3 three_candle/mes_relax_pipeline_v1.py --date ... --plot-both`.
- No original learning code was modified. GitHub commit `92a6558`. Python runtime checks and plotted output still require execution.


## 13. LOCKED PUBLIC API AND CHART CONTRACT — apply to ALL future MES versions (2026-11-04)

**USER-APPROVED; do not rename or redesign in future versions unless the user explicitly requests it.** This section supersedes older experimental naming examples (`three_candle_signal_learning`, `plot_signal_candidate`) in this historical document. Future refactors must retain a backward-compatible public wrapper for these exact calls.

### Fixed user notebook calls and order

```python
from mes_relax_pipeline_v1 import three_candle_signal, plot_candidates, plot_signal_passed

# Loads local IBKR CSVs; analyses using internal 9-stage pipeline.
result = three_candle_signal("MES=F", "2026-10-29", "2026-10-30")

# One FULL-RANGE chart with EVERY core-true C2 highlighted by a PURPLE dot.
plot_candidates(result)

# One separate, detailed chart per GOOD candidate; C1/C2/C3 and price levels.
plot_signal_passed(result)
```

This is the fixed API regardless of future research version; keep function names, positional parameters and the `result` object convention stable. The public main function uses the user-requested exact spelling `three_candle_signal(tiker, datefrom, dateTo)`. Do NOT silently switch to `three_candle_signal_learning()` or require users to pass raw candles into plotting functions. Internally, `plot_candidates(result)` can delegate to `_plot_candidates_chart(...)`, and `plot_signal_passed(result)` can delegate to `plot_good_candidates(...)`.

### Locked chart layouts and colors — retain between versions

**A. `plot_candidates(result)`: ALL candidates**
- ONE full-price-history candlestick chart for the requested interval.
- Every candidate for which `candle_detect_core()` is TRUE appears, whether GOOD or WAIT.
- **Purple dot on the C2/sweep candle**: dot below BUY C2 low, above SELL C2 high; no cluttered per-candidate entry/stop lines.
- Dark background, green bullish candles, red bearish candles, swing support and resistance lines, and UK local time labels.
- Keep an overview chart, not one chart per candidate.

**B. `plot_signal_passed(result)`: GOOD candidates**
- Exactly ONE signal per detailed chart (multipage PDF allowed).
- Clearly label C1, C2 and C3; show surrounding price candles, highlighted C2 and confirmed swing S/R.
- Show numeric reference **ENTRY** (blue dashed line), **STOP LOSS / SL** (red dashed line), and **TAKE PROFIT / TP** (purple line), all clearly legible.
- All times in **UK time**. This is an analytical plot; distinguish reference levels from actual 5-minute historical execution prices and do not invent realized P/L.

### Locked data and analysis responsibilities

1. Main function **reads local IBKR 5-minute CSV data**; no Yahoo/network calls or broker connection are required. Current sources:
   - `three_candle/data/MESZ2026_IBKR_5m_2026-09.csv`
   - `three_candle/data/MESZ2026_IBKR_5m_2026-10.csv`
   - Data is resampled to complete 15-minute candles; keep UTC for calculations and UK labels for presentation.
2. `candle_detect_core()` must be evaluated first for independent BUY and SELL candidate discovery.
3. Every CORE-TRUE candidate remains visible in the ALL plot and audit, even if quality checks later fail.
4. Internally run the confirmed 9 named stages in this order:
   `candle_detect_core()` → `market_structure()` → `swing_sr_lines()` →
   `volume_detect()` → `wicks_detect()` → `daily_range_check()` →
   `display_other_metrics()` → `higher_timeframe_support()` →
   `Liquidity_area_detect()`.
5. Classify signals as GOOD or WAIT based on the enabled requirements, retaining reasons and measurements. Plot only GOOD in the second plot.
6. Preserve original V3, original learning notebook, CSV source data and historical candidate master files. Any future experiment is versioned separately.
7. Future meetings can discuss method details, detection and new ideas. **Do not modify source code, public names, chart design, thresholds, or assumptions until requested.** Once changes are explicitly approved, change internal implementations without breaking this public contract.

**Current implementation:** `three_candle/mes_relax_pipeline_v1.py`, public function-name correction commit `c2df9f2`. That GitHub code was committed but execution and chart rendering have not yet been verified in a Python runtime.


## 14. CROSS-STRATEGY THREE-CANDLE DEVELOPMENT STANDARD (2026-11-04)

This convention is **COMMON TO ALL THREE-CANDLE STRATEGIES**, not MES-only. Carry it as a design contract when researching NQ, MNQ, MES, GC, INTC, or other tickers.

### Permanent user-facing functions

```python
result = three_candle_signal(tiker, datefrom, dateTo)
plot_candidates(result)
plot_signal_passed(result)
```

- Keep these names, parameter order and result-to-plot flow stable across all future variants.
- `three_candle_signal()` loads local CSV data where the relevant dataset is available, processes candles, runs named core/filter methods and returns all candidates plus GOOD/WAIT classifications and data needed for plotting.
- `plot_candidates()`: **one** dark, full-range candlestick chart with **purple dots on C2** for every CORE-TRUE candidate.
- `plot_signal_passed()`: **one GOOD signal per detailed chart**, with C1/C2/C3, clearly visible blue ENTRY, red SL, purple TP, price values, contextual price action and UK-time labels.
- Versions may change implementation, instrument-specific data adapters and research checks, but not this public API or visual contract without explicit approval.

### Ideas are transferable; implementation changes are NOT automatic

- Record new market-structure, liquidity, wick, volume, higher-timeframe and price-level ideas as **research proposals** that can be **imported/reused** between Three-Candle strategies.
- In a later session, **discuss an idea first** and wait for explicit instruction before adapting another strategy's code, modifying thresholds or changing historical results.
- Keep core detection, market-structure logic, filtering, plotting and data-source loading in separate small functions.
- Preserve existing strategy code and files; add isolated, versioned experiments when needed.

### Human-readable code and documentation standard

1. Prefer **simple explicit Python** over clever abstractions or compressed single-line expressions.
2. Add short comments at every **major logical step** explaining **why** the check exists, not only what Python does.
3. Each method needs a brief docstring: **inputs, output, and rules**. Keep method names descriptive.
4. Put tunable parameters together at the top with units and example values.
5. Use clear variables such as `c2_sweep_points`, `directional_wick_ratio`, `market_direction`, `entry_price`; avoid cryptic names.
6. Label completed vs unconfirmed bars carefully; do not use future candle information or repaint historical signals.
7. Keep debugging/audit output for every candidate, its pass/fail checks and reasons.
8. Make next-session handoffs easy to read, with paths, exact commands, version, tests and findings.
9. Protect the user's notebook and downloaded CSVs unless explicitly asked to change them.

This cross-strategy guideline is a **documentation agreement**: other strategy files are not modified by adding this section.


## 15. Nine-method diagnostic printing and original-learning metrics inventory (2026-11-04)

**Implemented:** `three_candle_signal(tiker,datefrom,dateTo)` now invokes `print_signal_details(result)` and prints **EVERY CORE-TRUE signal** (GOOD and WEAK/WAIT), its UK C3 date/time and price, nine method true/false statuses, which checks are required versus informational, four separately reported candle-quality tests, **all fields already present in MES Relax output**, and rejection reasons. This retains the locked public 3-call API and both plot designs.

Important convention: an optional informational method's boolean is **not** a mandatory pass condition. `display_other_metrics` reports True to mean the stage ran; it is not a quality filter. `candle_detect_core=True` is required for a record to appear.

### Inventory from the FIRST `three_candle_learing.py` version

The earlier learning module's `build_signal_metrics()`, `v3_research_checks()` and helper filters report significantly more than current MES Relax. **The following are found there and are proposals to port as diagnostic-only fields** (not yet newly computed in this commit):

- Candle anatomy: C1/C2/C3 range %, C2/C3 body %, individual upper/lower wick %; C2 lower-wick/body, C3 total wick/body, C3 wait bars, C2 sweep ticks.
- Trend: EMA20 distance %, EMA200 distance %, EMA20 3-bar slope %, EMA20/EMA200 overlays.
- Momentum/volatility: RSI14, ATR14 %, BB20 width %, rolling 10-bar and 20-bar price-range %.
- Liquidity/price level: session VWAP distance %, prior-20-candle low sweep %, distance to prior-20-candle high %, nearest confirmed support/resistance and **room in points and R**.
- Participation: C2 RVOL20, C3/C2 volume ratio, C3 volume, C3 volume increase boolean.
- Price-action approach: 10-bar approach %, C2-to-C3 directional recovery %, V-shape observation.
- Time/session: US opening-hour / RTH / premarket / postmarket / overnight bucket, C3 UK hour.
- Futures daily range: high/low of developing 18:00 ET futures session, current range %, position within range %, previous completed session high/low, room to previous-session target in R.
- Earlier experimental variants: C3 SELL body 0.05%–<0.10% and C2 wick/body 4x–<10x. Preserve as research diagnostics only, not automatic GOOD conditions.

These metrics should be ported as **human-readable, separately commented** calculations with data warm-up and no lookahead. The most informative first priority is trend EMA20/EMA200, RSI14, ATR14, session VWAP, C3/C2 volume ratio, confirmed support/resistance room, futures-session previous high/low, and C1/C2/C3 OHLC+volume. Review with the user before new filter thresholds or core changes.

**Commit implementing prints:** `18c67ae`. Code is committed, **not runtime-validated** in a Python execution environment yet.


## 16. EMA historical warm-up, chart overlays and first-learning diagnostic parity (2026-11-04)

**User instruction:** use enough earlier CSV history for indicators to be valid from the beginning of the *requested display period*. Compute indicators across ALL available MES September/October IBKR 5-minute CSV, resampled to complete 15-minute candles, **before** filtering to `datefrom`–`dateTo`. For October requested periods, September provides prior history. If the earliest loaded history has fewer than 200 15m candles, EMA200 is **N/A**, not a fabricated complete EMA. Do not fetch hidden future bars.

**Implemented in `mes_relax_pipeline_v1.py` (commit `c816147`):**
- `calculate_indicators(bars)` calculates EMA20 / EMA200 seeded with the corresponding first 20 / 200 bars' simple average (warm-up-aware); also RSI14, ATR14, BB20 width and 18:00 New York futures-session VWAP. A single indicator set is computed once per full `scan(bars)`, not per candidate.
- `indicator_metrics(...)` records from the original first learning version C1/C2/C3 OHLC and volumes; range/body/wick percentages, C2 sweep ticks, C3/C2 volume, EMA distances/slope, RSI14, ATR14, BB width, VWAP/distance, rolling 10/20 range, 10-bar approach and recovery, prior20 high/low, sweep/high distances. These are **display metrics**, not newly mandated filters.
- Both `plot_candidates(result)` (one overview with purple C2 dots) and `plot_signal_passed(result)` (one detailed chart per GOOD candidate) draw **EMA20 gold** and **EMA200 lavender/violet**, using the SAME full-data precomputed history (not recalculated from the visible chart slice).
- `three_candle_signal()` prints all nine method status lines, the four core quality checks, and all available metrics for each signal (GOOD and WAIT), following the original learning's detailed print style.
- Existing locked public method names and plotting layouts stay unchanged:
  ```python
  result = three_candle_signal("MES=F", "2026-10-29", "2026-10-30")
  plot_candidates(result)
  plot_signal_passed(result)
  ```

**Important data coverage:** the presently selected CSVs begin in September 2026 and end in October 2026. Early September does **not** necessarily have the 200 already-closed 15-minute bars needed for fully warmed EMA200. Earlier CSV months would be required to have a complete EMA200 from the very first September candle.

**Runtime status:** GitHub code updated. Compilation and actual chart generation have **not yet been executed successfully** against the VPS/local data from this session; source-container networking prevented automated download for a runtime check. Run `python3 -m py_compile three_candle/mes_relax_pipeline_v1.py` and notebook calls after safe `git merge --ff-only`.


## 17. VERIFIED FIRST REAL RUN — MES 29–30 OCTOBER 2026 (run 2026-11-04)

**Source:** real IBKR MESZ2026 5-minute September/October 2026 CSVs from GitHub; resampled to 15-minute bars. The actual version `three_candle/mes_relax_pipeline_v1.py` was executed in GitHub Actions on Ubuntu/Python 3.11, not merely estimated. Both fixed public plot methods executed successfully. Run: https://github.com/raghunathbhandari/ASJR/actions/runs/41793966304 ; downloadable run artifact: https://github.com/raghunathbhandari/ASJR/actions/runs/41793966304/artifacts/13304478251

### Real classification result

| UK calendar day | CORE-TRUE | GOOD | WAIT |
|---|---:|---:|---:|
| 2026-10-29 | 27 | 0 | 27 |
| 2026-10-30 | 24 | 2 | 22 |
| **Total** | **51** | **2** | **49** |

Two **GOOD SELL** signals:
1. **2026-10-30 15:00 UK** C3, C1 14:30 / C2 14:45; C3 close 7641.75; C2 high sweep 2.75 MES points; C2 rejection wick 4.75× body; C2 RVOL20 2.25; C3/C2 vol ratio 0.8678; market structure BEARISH; previous 1H BEARISH; EMA20 7661.2284; EMA200 7713.2288; RSI14 36.3872; ATR14 11.6817; VWAP 7665.4167; last5 double-long-wick candles 1.
2. **2026-10-30 16:45 UK** C3, C1 16:15 / C2 16:30; C3 close 7614.00; C2 high sweep 3.00 MES points; C2 rejection wick 2.571× body; C2 RVOL20 0.86; C3/C2 vol ratio 2.3467; market structure BEARISH; previous 1H BEARISH; EMA20 7644.6775; EMA200 7707.5672; RSI14 30.1293; ATR14 12.0079; VWAP 7656.2276; last5 double-long-wick candles 1.

**Failure counts across all 51 candidates** (overlapping; a single WAIT can fail several): market_structure=30, wick2=29, wick_congestion=24, sweep2=20. These are the current mandatory check counts, not loss-trade counts.

**Important caution from actual metrics:** Both GOOD signals have `liquidity_area_ok=False`, but that check was intentionally **informational / disabled** and not a mandatory GOOD condition. The corrected nine-method print now shows these as `false [INFO / OPTIONAL]` rather than misleadingly printing `true` from bypass flags; correction commit `3633185`. Also `daily_range_check` is presently an informational distance to the **UK calendar-day** extreme and `daily_range_ok=True` placeholder, not yet the original learning script's 18:00 ET futures trading session range or a validated room-to-target test. The second GOOD signal's current UK-day low distance is only 5.75 points while the illustrative target is 10 points. Do not claim full 9-filter strict validation.

**Outputs in GitHub Actions downloadable artifact:** full per-signal 9-stage human-readable log, 51-row full diagnostic CSV, one all-candidates dark chart with purple C2 dots and EMA20/EMA200, and one two-page PDF of GOOD charts with C1/C2/C3 / entry / SL / TP / EMA20/EMA200. All compiled/rendered successfully.

**This is classification validation only.** No next-5-minute fill, realized R, TP/SL hit, transaction fees, slippage, P&L, or success rate have been calculated for these 2 signals in this run.

**Next idea-review priorities:** visually inspect the two GOOD charts; verify future-outcome TP/SL via 5-minute replay; consider whether the daily range and liquidity checks should become meaningful measurements/gates. Keep fixed public API and chart designs unchanged.


## 18. RUDRA THREE STRATEGY — CURRENT FINAL HANDOFF (2026-11-04 08:37 UK)

**This is the latest agreed state.** The cross-instrument source of truth is `three_candle/NEXT_SESSION_IDEAS_HANDOFF.md` section 10. In later conversations, **discuss strategy ideas only until implementation is explicitly requested**.

**All Three-Candle strategies share this locked notebook entry point:**
```python
result = three_candle_signal(tiker, datefrom, dateTo)
plot_candidates(result)
plot_signal_passed(result)
```
The nine stable internal stages, in order:
`candle_detect_core()`, `market_structure()`, `swing_sr_lines()`, `volume_detect()`, `wicks_detect()`, `daily_range_check()`, `display_other_metrics()`, `higher_timeframe_support()`, `Liquidity_area_detect()`.
Supporting code: `scan()`, `evaluate_pipeline()`, `calculate_indicators()`, `indicator_metrics()`, `print_signal_details()`.

**Final print convention:** the main `three_candle_signal()` prints every signal header and status. For **WEAK/WAIT**, print all nine boolean observations, REQUIRED/OPTIONAL labels, candle subchecks, all available metrics and rejection reasons. For **GOOD**, print a short passed-mandatory-filters summary and key prices/metrics **without** repeating the nine booleans. Optional measurements can be false even for GOOD; the detail remains in `result` and the exported audit CSV. This formatting update is committed (`4303a4f`) but has not separately been runtime tested after the verified 29–30 Oct run.

**Locked charts:** `plot_candidates()` = one dark full-period chart, purple dots on all C2 CORE-TRUE candidates, EMA20 gold, EMA200 lavender and swing S/R. `plot_signal_passed()` = one focused chart per GOOD with C1/C2/C3, entry blue, SL red, TP purple, numeric price labels, EMA20/EMA200, swing S/R and UK times. No chart redesign without approval.

**Data:** pre-read all available historical IBKR 5m CSV history, resample to complete 15m candles, calculate EMA20/EMA200 and all indicators **before** limiting displayed dates. Return N/A until warm-up sufficient. Don't modify input data. Print diagnostic RSI14, ATR14, BB20 width, RVOL, VWAP, OHLCV, range/body/wick, price sweep and volume comparisons. Avoid changing filters based on indicators without permission.

**Real-run baseline (GitHub Actions, successful Python 3.11 test):** 29 Oct 2026: 27 CORE/0 GOOD/27 WAIT; 30 Oct: 24 CORE/2 GOOD/22 WAIT; **combined 51 CORE, 2 GOOD, 49 WAIT**. The two GOOD were **SELL 30 Oct 15:00 UK @ 7641.75** and **SELL 30 Oct 16:45 UK @ 7614.00** (C3 closes). Main overlapping rejections: structure 30, wick2 29, wick congestion 24, sweep2 20. This was **classification only**, not measured profitability. Last verified detailed results and charts: https://github.com/raghunathbhandari/ASJR/actions/runs/41793966304/artifacts/13304478251 ; updated optional-observation verification: https://github.com/raghunathbhandari/ASJR/actions/runs/41793966304 .

**Editing standard:** human-readable, short self-documenting methods, comments around every major area, descriptive names, thresholds with units at top, retain full diagnostic audit, never edit prior notebook/historical CSVs/master results. Follow Git safety (`git fetch origin && git merge --ff-only origin/main`). Future session should start by reviewing these notes and discussing **ideas only**.


## 19. Confirmed liquidity area lines and printed levels (2026-11-04)

**Explicit user request:** For now, make visible liquidity area lines and print the current areas only; **do not change entry filters**.

Implemented as a new informational helper `liquidity_levels_at_signal(bars,c3_i)`, called from `evaluate_pipeline()`. Per candidate the nearest **already-confirmed swing high on/above C3 close** is labelled **BUY-SIDE liquidity**; the nearest already-confirmed swing low on/below C3 close is labelled **SELL-SIDE liquidity**. Both store level price and distance in MES points; absence is `N/A`. They approximate possible liquidity, **not actual order-book resting orders**. The existing Method 9 `Liquidity_area_detect()` remains the optional swing-touch check, untouched.

The main `three_candle_signal()` print includes both levels for all GOOD/WAIT candidates. WEAK/WAIT still print the nine boolean diagnostic checks; GOOD still print only their concise summary. On the all-candidates overview, label **the latest candidate's** two confirmed liquidity levels as dashed **amber buy-side** and dashed **teal sell-side** lines; one per GOOD chart uses the respective candidate's snapshot. Lines start no earlier than the swing confirmation (right-hand 2 candles) and do not use future pivots. EMA20/EMA200 and existing S/R chart lines remain.

Change commit: `9dfde8d`. GitHub Actions real-run validation pending at this writing; use the latest workflow run if available.


## 20. FINAL REVIEW MODE: `enableDiag` optional public argument (2026-11-04)

**Authoritative printing contract for all Three-Candle variants:** `three_candle_signal(tiker, datefrom, dateTo, enableDiag=False)`. There is **no** global diagnosis variable and **no** automatic date-based toggle. A researcher may use `enableDiag=True` for a single date to minimize output, but it also works for any requested interval.

In compact mode, print each candidate's C3 timestamp/price/BUY-SELL/GOOD-WAIT, current confirmed buy-side and sell-side liquidity line price and distance, structure/sweep/wick context, and active rejection reasons.

In detailed mode, **GOOD and WAIT alike** print **all 9 named method observations** with true/false, enabled/optional flags, **all 10 underlying trade-gate variables with observed value, live threshold comparison, stored pass outcome, and actual BLOCKS TRADE/PASS**, PLUS every stored key/value field (including C1/C2/C3 OHLCV, EMA20/200, VWAP, RSI, ATR, RVOL, candle anatomy, market structure, swing lines and both current liquidity levels). Never suppress GOOD metrics in detailed mode: visually promising setups must be fully auditable. Disabled informational observations can be false while GOOD remains legitimate.

Example:
```python
three_candle_signal("MES=F", "2026-10-29", "2026-10-30")
three_candle_signal("MES=F", "2026-10-30", "2026-10-30", enableDiag=True)
```

This changes **printing only**. It never changes scanning, filters, thresholds, plot formats, labels, or underlying CSV. Code commit `e61e2cf`, on top of full-audit implementation `0425384`.
