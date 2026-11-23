# COHR — Gann Date Circle / 15-minute bar cycles (23 November 2026)

**Research only — no trading or orders. Prospective watch dates frozen before their outcomes.**

## Provenance
- Source: `three_candle/data/ibkr_bridge/research-1795424533000/COHR_2026-10-23_2026-11-22_15min_UTC.csv`
- IBKR read-only Gateway 4002, requested 2026-10-23 through 2026-11-22, native `15min`, `TRADES`, `useRTH=False`.
- Download manifest: `three_candle/data/ibkr_bridge/research-1795424533000/manifest.json`.
- Bridge completed SUCCESS, 1,344 rows, 0 reported request errors; manifest `verified_complete=false` means the export has not been independently reconciled to exchange records.
- All candles from 2026-10-23 08:00 UTC to 2026-11-21 00:45 UTC; 21 US trading dates, 64 bars each, representing approximately 04:00–20:00 ET. **No separate IBKR overnight-venue bars are verified.**
- Regular US hours (09:30–16:00 ET) subset: 546 bars, 26 per date.
- Time stamps for intraday anchor and test results are UTC (identical to UK GMT in November).

## Frozen methodology
1. Keep **calendar-day Gann date-ring** separate from **15-minute bar cycles**. Never equate 90° with 90 bars or a 90-calendar-day quarter-year cycle.
2. Two previously discussed anchors: **2026-10-20** calendar-date anchor, not inspectable in this export; and **2026-11-05 16:00 UTC**, COHR's `160.23` low candle (earlier visual estimate was `160.26`, a 0.03 difference).
3. Experimental square-root date ring, with anchor counted as day 1: `N = elapsed_calendar_days + 1`; `angle = 180 * (sqrt(N) - 1)`. For each 90° milestone, `N=(1+angle/180)^2`, project `anchor + round(N-1) calendar days`. Round to nearest whole day before testing; a weekend target is listed as its actual date, optionally watch next open session. This is a chosen **experimental spiral time mapping**, not a verified fixed Gann law or the classical 90/180/360-calendar-day method.
4. Objective **daily major pivot**: session date's high exceeds highs of the *two preceding and two subsequent sessions*, or its low is below lows of both pairs. Confirm only if two subsequent sessions are in the downloaded dataset. Both full extended+RTH and RTH-only variants are considered.
5. Calendar date ring scores a hit if the selected major pivot date is within **±1 calendar day** of the exact target. No directional success is inferred from the date.
6. Objective **15-minute local pivot**: bar high greater than highs in 8 previous and 8 following data bars with both nearby price reversals ≥2% (or symmetrical condition for a low). An 8-bar future look-ahead is used only to **label historical outcomes**, never to generate live signals. Cycle hit if projected bar at anchor index + `k*cycle` is within ±2 data bars of a pivot. Bar offset can span a weekend on sparse sequences; these are *bar* tolerances, **not guaranteed 30-minute clock tolerances**.
7. Preserve periods `90,95,96,99,100` from earlier chart discussion; report every cycle and both session choices, not just winners. Anchor is included as index 0; the first projection is 90/95/etc *subsequent* candles.
8. Sample too small for validated performance. No transactions, signal returns, transaction costs, win rates, or future direction asserted.

## Major observed date pivots

| Date (ET) | Extended+RTH | RTH-only |
|---|---|---|
| 2026-10-28 | HIGH 262.23 (after-hours spike) | No RTH major pivot; the corresponding RTH swing HIGH was **Oct 29 at 246.90** |
| 2026-11-05 | LOW 160.23, at 16:00 UTC | LOW 160.23 |
| 2026-11-11 | HIGH 245.73 | HIGH 245.73 |
| 2026-11-16 | LOW 196.12 | LOW 196.12 |

These are 2-session local extrema, not promises of a turn.

## Oct 20 date ring: 90° milestones

| Angle | Calculated target | Full-session major pivot within ±1 day |
|---:|---|---|
| 180° | 2026-10-23 | Excluded: dataset's first day cannot confirm preceding 2 days |
| 270° | 2026-10-25 (Sunday) | NO; next US session 2026-10-26 |
| 360° | 2026-10-28 | **YES:** high 262.23 exact date; RTH pivot high Oct 29 |
| 450° | 2026-10-31 (Saturday) | NO; next US session 2026-11-02 |
| 540° | 2026-11-04 | **YES:** low 160.23 on Nov 5 |
| 630° | 2026-11-08 (Sunday) | NO; next US session 2026-11-09 |
| 720° | 2026-11-13 | NO confirmed 2-day major pivot |
| 810° | 2026-11-18 | NO confirmed 2-day major pivot |
| 900° | **2026-11-24** | **FUTURE; outcome unknown as of Nov 23** |

Result: **2 / 7** eligible historical date targets matched a ±1-calendar-day major pivot for both all-session and RTH-only variants.
As a negative-control sensitivity check, shifting the Oct 20 anchor by -10 to +10 calendar days produced 16 candidate shifted anchors with >=6 eligible targets; **15/16 equalled or exceeded the original 2/7 match rate**, so observed coincidences do not demonstrate predictive superiority. Alternate-anchor checks have unequal counts and are descriptive sensitivity tests, not formal p-values.

## Nov 5 low date ring

| Angle | Target | Verified daily 2-session pivot within ±1 calendar day |
|---:|---|---|
| 180° | Nov 8 (Sunday) | NO |
| 270° | Nov 10 | YES: Nov 11 HIGH 245.73 |
| 360° | Nov 13 | NO |
| 450° | Nov 16 | YES: Nov 16 LOW 196.12 |
| 540° | Nov 20 | Not scoreable: only final historical session (Nov 20 low 180.43 not confirmed by two later sessions) |
| 630° | **Nov 24** | **FUTURE** |

Result **2/4** tested eligible historical targets; tiny sample and hindsight validation of Nov 5 anchor's significance (though its date was discussed before this run).

## Intraday 15-minute cycle results

All projections begin at **Nov 5 16:00 UTC** low candle; each test includes consecutive *available* bars, but an RTH chart has fewer bars/day than an extended-session chart.

| Bar cycle | RTH-only | RTH+extended |
|---:|---:|---:|
| 90 | 0/3 | 5/8 |
| **95** | **0/3** | **2/7** |
| 96 | 1/3 | 1/7 |
| 99 | 1/3 | 4/7 |
| 100 | 1/3 | 4/7 |

The visually observed 95-bar setting did **not** reproduce robustly with objective matching. 90 bars matched more all-session pivots in this sample, but **no cycle is validated or declared the best**. Different chart session options completely change projection dates.

A full 90-/180-/360-**calendar-day** Gann cycle **cannot** be tested using only the 31-day request range. The date-ring square-root angles above and traditional 360-day/year divisions are distinct hypotheses.

## Forecast log — frozen as of 23 Nov 2026

| Date | Original anchor | Experimental angle | Direction | Evaluation protocol |
|---|---|---:|---|---|
| **2026-11-24** | 2026-10-20 | 900° | NEUTRAL | Date-only watch: ±1 calendar day against confirmed 2-session major pivots after complete data arrive |
| **2026-11-24** | 2026-11-05 16:00 UTC low | 630° | NEUTRAL | Same protocol; confluence with Oct20 angle, not independent evidence |
| 2026-11-23 | 2026-10-06 historical high anchor from prior date-ring study | 1080° | NEUTRAL | Not included in COHR scoring: high anchor lies outside source CSV and is unverified in this data |

No automatic BUY/SELL is justified by a time cycle alone. The question to test later is **whether a predeclared date window contains a subsequent objectively confirmed turning point more often than simple baseline windows**, not whether price happened to move in the neighborhood.

## Next research steps
- Preserve this method, anchor selection and tolerances. Never optimize 95 to the best hindsight fit and then count those same candles as an independent test.
- Extend COHR history to cover the claimed October 6 and October 20 swing anchors before validating them as **market** pivots.
- Continue out-of-sample tracking for at least several months and compare against random-anchor and fixed-calendar-date baselines.
- For intraday monitoring freeze whether TradingView displays only RTH or RTH+extended. Do not mix both in one cycle score.
- Date-only forecast direction is **NEUTRAL** until separate pre-specified, validated directional time rules are studied; no news, indicators, discretionary market bias, or order entry used.

_Source reference for historical Gann interest in squares, 90 and 95–100 counts: W.D. Gann, "Natural Resistance Levels & Time Cycle Points" (1935), https://sacredtraders.com/wp-content/uploads/Gann-W.D.-Natural-Resistence-Levels-Time-Cycle-Points.pdf. The empirical cycle testing and square-root date mapping are this project's documented research conventions._
