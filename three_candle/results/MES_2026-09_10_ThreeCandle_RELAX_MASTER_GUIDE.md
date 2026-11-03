# MES September–October 2026: ThreeCandle candidate master and pattern study

Instrument: **MESZ2026** (Micro E-mini S&P 500), 5-minute historical IBKR trades, full available session, resampled into aligned complete 15-minute candles; output times in **UK timezone (BST/GMT)**. Research dry run, **not trade executions or a profitability backtest**.

## Source files (read-only)
- `three_candle/data/MESZ2026_IBKR_5m_2026-09.csv` — 6,024 bars, 234 zero-volume bars, 0 duplicates, 0 invalid OHLC, 0 reported download errors.
- `three_candle/data/MESZ2026_IBKR_5m_2026-10.csv` — 6,048 bars, 0 zero-volume bars, 0 duplicates, 0 invalid OHLC, 0 reported download errors.
- Original coverage TXT files remain unchanged. Their status says **NEEDS REVIEW**, not certified complete.
- 4,024 complete aligned 15-minute candles; incomplete 15-minute windows discarded; no bridging missing timestamps.

## Master outputs
- `MES_2026-09_10_ThreeCandle_RELAX_ALL_CANDIDATES_MASTER.csv`: **593 rows**, **100+ descriptive/filter columns**, all raw pattern candidates including rejects, UK C1/C2/C3 timestamps, individual OHLCV, wick/sweep/body, C2 RVOL20, volume quality, session, EMA20/200, RSI14, ATR14, BB20 (population SD), VWAP, previous-20 levels, prior session levels, pivot support/resistance and six original V3 filter pass flags. All candidate rows retained.
- `MES_2026-09_10_ThreeCandle_RELAX_PATTERN_SUMMARY.csv`: monthly and combined candidate/direction/filters/profile counts and descriptive patterns.

## State machine / candidate detection
The implementation follows the existing `three_candle_learing.py` `scan_core_candidates` logic:
1. C1 anchors while following 15m bars stay inside C1 high/low.
2. C2 sweeps C1 low (BUY) or high (SELL); two-sided sweeps are ambiguous and reset.
3. Any later C3 crossing C2 body top/bottom confirms if it does NOT also invalidate C2 sweep extreme. Intra-15m invalidation+confirmation is reset, not claimed filled.
4. A confirmed C3 becomes the next C1. Break across a 15m timestamp gap resets state.
5. Detected **593**: Sep 276 (BUY 149 / SELL 127), Oct 317 (BUY 141 / SELL 176); 258 intrabar ambiguous confirmation/violation events reset and excluded from candidate rows.

## Original #3–#8 filter flags
- **F3_location**: opposing confirmed 2L/2R pivot support/resistance room >= 1R; study **MES risk=3.0 S&P points**.
- **F4_v_shape**: directional preceding-10-candle approach, recovery C2->C3 >0, and last-20-bar price range >= 1R (expressed %).
- **F5_volume**: C2 RVOL20 >=1.2 **OR** C3 volume / C2 volume >=1.0.
- **F6_session**: all five recognised time buckets currently enabled, hence all pass by construction.
- **F7_wick**: C2 directional rejection wick / body >=0.5 OR strong directional C3 close (research rule).
- **F8_daily_range**: room to previous completed futures session high/low >=1R, if an opposing level remains. Sessions roll at 18:00 New York time.
- `passed_six` is the legacy all-6 AND gate: just **23** of 593 pass, so Relax profiles are separately flagged, not discarded.
- Body, wick and RVOL Relax profiles: **Broad** C3 body <0.10%; **Balanced** body <0.10%, C2 wick/body>=0.25 and RVOL20>=0.3; **Quality** body <0.10%, wick/body>=0.5 and RVOL20>=0.5; **Wick 1–10** body <0.10%, wick/body [1,10); **Clean** Broad without zero-volume five-minute bars in C2 or C3. Zero-body wick/body yields blank and cannot meet wick filter.

## Monthly dry-run summary
| Metric | September | October | Both |
|---|---:|---:|---:|
| Raw BUY+SELL candidates | 276 | 317 | 593 |
| BUY | 149 | 141 | 290 |
| SELL | 127 | 176 | 303 |
| All 6 V3 checks pass | 15 | 8 | 23 |
| F3 location pass | 53 | 29 | 82 |
| F4 V-shape pass | 122 | 157 | 279 |
| F5 volume pass | 184 | 200 | 384 |
| F6 session pass | 276 | 317 | 593 |
| F7 wick/direction pass | 256 | 310 | 566 |
| F8 prior-session room pass | 235 | 253 | 488 |
| Broad profile | 264 | 274 | 538 |
| Balanced profile | 183 | 220 | 403 |
| Quality profile | 138 | 172 | 310 |
| Wick 1–10 | 128 | 151 | 279 |
| Broad+clean | 227 | 274 | 501 |
| C2/C3 contains any zero-volume 5m bar | 39 | 0 | 39 |

**Interpretation:** F3 support/resistance room is the most restrictive original filter (82/593), while F6 accepts all known sessions. C2/C3 zero-volume contamination is September-only. Balanced count differs by 1 from the earlier quick exploratory scan because this final master applies the original module's strict 20-prior-candle RVOL warm-up (a missing RVOL cannot pass the filter).

## Metrics implementation and caveats
- Derived from original complete IBKR 15-minute candle series, with all 593 rows preserved; filters are computed using information available through C3 only.
- Rolling EMA20/EMA200 (adjust=False recursive), RSI14 and ATR14 EWM-style, BB20 using rolling close standard deviation with ddof=0, per-session typical-price VWAP, directional wick body/range, pivots and daily level fields.
- Initial September EMA200 warmup lacks previous-month data and is provisional. Early rows have blank rolling indicators/levels where 20 prior bars or a previous session are unavailable.
- Pivot S/R highs/lows are 2-left/2-right and become known only once two right-hand bars close. Re-evaluate any marginal matches against the canonical Python scanner before automating trades.
- This tabular research output was calculated independently from GitHub IBKR data; the VPS Python dry-run executable has **not been run** in this session. Results are **candidate counts and observed metrics**, not signal success, win rate or fees-adjusted P/L.
- The provisional MES study setting is **3-point planned SL / 6-point TP** (1 MES=$5 per index point). This report does not simulate that trade outcome, and changing this setting could change F3/F4/F8 thresholds.

## Next evidence to collect
Backtest MES trade exits with explicit entry at the 5-minute OPEN after C3 closes, compare 3/6, 4/8, 5/10, 6/12 point SL/TP, model gaps through stops, stop-first in ambiguous 5-minute candles, exclude overlaps under one-open-trade constraint, estimate MES exchange/IBKR fees, then validate on unseen months. Avoid selecting a winning profile from only September and October.
