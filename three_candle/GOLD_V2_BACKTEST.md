# Rudra-Gold V2 — Independent 15-Minute Backtest

**Status:** Experimental / research. This is NOT a validated profitable strategy.
**Date created:** 2026-10-31. The NQ Three-Candle strategy remains separate.

## Files
- `three_candle/backtest_gold_v2.py`: standalone command-line backtest.
- `three_candle/data/multi_asset_5m/GOLD_20260901_20261031_5m_UTC.csv`: historical Yahoo GC=F 5-minute OHLCV.

## Goal
Find **2–3 high-quality Gold setups per day**, not 12 low-quality trades.
However **2–3 is a research target, NOT a proven daily signal count**.
Never select the "best" trades using outcomes or later bars.

## Gold V2 entry model
1. Build complete 15-minute OHLCV from consecutive 5-minute candles; no synthetic gap-filled candles.
2. **C1** = preceding 15-minute candle.
3. **C2 always is the sweep candle**, independent of its colour:
   - BUY: C2 low strictly below C1 low.
   - SELL: C2 high strictly above C1 high.
   - C2 may close outside the C1 range; do not require a C2 reclaim.
4. **C3** = confirmation:
   - BUY: C3 closes above its open, with C3 low above C2 low.
   - SELL: C3 closes below its open, with C3 high below C2 high.
   - C3 does **not** have to reclaim the C1 high/low. Optional stricter filters can be researched separately.
5. **Entry** = following C4 15-minute open after C3 has closed. Never credit a 09:00 entry that needs information from the 09:00–09:15 candle.
6. **Initial structural SL** = C2 low for BUY, C2 high for SELL. Must be favourable side of entry and no farther than **0.20%**. Reject, rather than tighten or widen, an ineligible structural stop.
7. Optional minimum C2 sweep depth expressed as a multiple of 15m ATR14, `--min-sweep-atr`. Default 0 means no depth filter; this is **not** a validated threshold.
8. Rank/selection is **not yet validated**. `--daily-cap 3` merely takes the first 3 chronologically, NOT the strongest 3. It must not be mistaken for a quality-scoring algorithm.

## Exit modes
- `step`: original +0.20% favourable price milestone => stop locked at that price milestone.
- `swing`: trail beyond **confirmed 15-minute 2-left / 2-right swing highs for SELL** or swing lows for BUY. Confirmation needs two following complete 15m bars; update stop causally, never retrospectively. Default buffer is $0.20 per ounce (research setting).
- `partial_swing`: sell/buy back 50% at +0.20% favourable movement, move remainder's stop to entry, then trail its stop using confirmed swings.
- Backtest uses original 5-minute OHLC for stop checks, **stop-first on each ambiguous 5-minute bar**. Gap through stop fills at opening price; the 5m path is not true trade/tick data.
- Default mark/close cutoff is **21:00 UTC**. For futures, cutoff and trading sessions need explicit validation; open positions are marked at available close. Gross price returns are **not** contract/account equity returns.
- Multiple signals are simulated independently even if they overlap. No commissions, exchange fees, spread, slippage, rollover adjustments or capital constraints.

## User-identified reference examples
**29 Oct 2026 (UK GMT):** C2 05:15 SELL, 08:45 BUY, 20:00 SELL.
**30 Oct 2026 (UK GMT):** C2 07:45 BUY, 08:45 SELL.

### Key 30 Oct SELL reference
C1 08:30 (O 3995.00 H 3999.60 L 3994.70 C 3998.80).
C2 08:45 (O 3998.60 H **4009.20** L 3998.40 C 4007.20, vol 3179).
C3 09:00 (O 4007.10 H 4008.60 L 4000.40 C 4001.20, vol 1667).
C4 entry 09:15 **4001.60**, C2-high stop **4009.20**, risk **0.190%**.
C2 breaks C1 high by **$9.60 (0.240%)**; C2 volume is **3.54x** C1 and ~1.81x previous 20-candle mean.
**Historical illustrative simulations only:**
- 0.20% step trail: +0.200%, exit ~10:15.
- 15m confirmed swing-high trail: +2.684%, exit ~19:55 at 3894.20.
- 50% partial + swing trail: +1.442%.
The 08:45 SELL is a **selected reference**, not an independent out-of-sample proof.

**30 Oct 07:45 BUY reference:** C2 sweeps 3974.70 low, C3 08:00 bullish. Structural stop is too far from C4 confirmed entry (~0.45%) and **must be rejected** by V2 0.20% entry risk cap.

## Prior baselines — do not mix result sets
- Previous strict C3 reclaim + fixed 0.20% step trail study: 34 detected, 12 eligible, 2 wins, 10 losses, **16.7% winners and -0.987% summed gross** on 30 Oct.
- Earlier model: 21 detected, 8 eligible, 4 wins, **50% and +0.151% summed gross** on 30 Oct.
- Neither is a complete validated V2 result: entry logic and exit logic differ. **Do not claim Gold V2 full-day win rate or gain from these figures.**

## Usage
From repository root:

```bash
python three_candle/backtest_gold_v2.py --date 2026-10-30 --mode swing --out three_candle/results/gold_v2_20261030.csv
python three_candle/backtest_gold_v2.py --date 2026-10-30 --mode step
python three_candle/backtest_gold_v2.py --date 2026-10-30 --mode partial_swing
python three_candle/backtest_gold_v2.py --date 2026-10-30 --mode swing --min-sweep-atr 0.25
```

The code prints each eligible trade with timestamps, entry, structural stop, risk, sweep/ATR, volume ratio, exit and gain. Verify the 08:45 reference against the emitted record, and check missing/gapped bars before relying on summary statistics. Different continuous Gold contracts can have different rolling/adjusted price series.

## Validation still required
- Execute and independently verify the script against VPS dataset; check exact 08:45 reference.
- Define a **causal** quality-score and limit of <=3 trades per day (no ranking by future outcome).
- Compare September and October, day by day, with out-of-sample tests.
- Add overlapping-trade portfolio rules, transaction costs, exchange tick size, futures margin and rollover handling.
- Verify single-bar OHLC stop/target ambiguities with higher-resolution data.


## 2026-10-31 update — Swing-turning C2 detector (separate detection stage)
File: `three_candle/detect_gold_v2_swings.py`.

This is **detection only**, not the full trading/backtest implementation. Detect all strong turning-area setups irrespective of entry stop distance. A later entry engine may reject some.

Experimental causal requirements:
- C2 is a *meaningful* new local high (SELL) or low (BUY) compared with preceding **8 completed** 15m candles.
- C2 high–low range >= **1.00 × 14-bar ATR**; swing penetration >= **0.50 × ATR**. ATR is from **14 bars preceding C2**; no C2/future leakage.
- C1 candle body / total range >= **40%** (avoid flat/doji C1).
- C3 directional confirmation body / range >= **60%**; C3 high stays below C2 high for SELL, C3 low stays above C2 low for BUY.
- Pattern is known only at **C3 close**. C2 is the sweep candle even if its close is outside the previous range.
- The scanner records optional following-candle structural risk but **does not discard** a strong pattern just because its risk >0.20%; this is an execution problem to test separately.

Independent calculation on 30 October 2026 found three reference matches:
- **05:30 C2 SELL:** range/ATR 1.40, swing penetration/ATR 0.72, next-open C2-high stop distance ~0.497% (not executable under 0.20% rule).
- **07:45 C2 BUY:** range/ATR 2.07, sweep/ATR 1.65, ~0.448% SL (not executable).
- **08:45 C2 SELL:** range/ATR 1.17, sweep/ATR 1.01, ~0.190% SL (eligible under risk cap).

The first chart annotation appeared around 05:15 on the TradingView screenshot; 05:30 is the matching *detected historical Yahoo GC=F candle* in this 15m data. Check contract/timestamp differences before claiming exact equivalence.

Usage:
```bash
python three_candle/detect_gold_v2_swings.py --date 2026-10-30
python three_candle/detect_gold_v2_swings.py --date 2026-10-30 --out three_candle/results/gold_v2_turns_20261030.csv
```

**No full V2 result is claimed by this detection test.** The thresholds were selected from 30 Oct reference signals (in-sample), so verify on other dates before adoption. Existing `backtest_gold_v2.py` has NOT yet been modified to use this new detector automatically.


## 2026-10-31 BODY-EDGE ENTRY UPDATE — corrected research rule
The C2 candle's **body**, not wick high/low, supplies the trigger threshold:
- BUY and C2 RED: C2 **OPEN** (upper body edge).
- BUY and C2 GREEN: C2 **CLOSE** (upper body edge).
- SELL and C2 RED: C2 **CLOSE** (lower body edge).
- SELL and C2 GREEN: C2 **OPEN** (lower body edge).
In equations BUY threshold=max(C2.Open,C2.Close), SELL threshold=min(C2.Open,C2.Close).
The first qualifying 5-minute crossing after C2 completes is the simulated entry; the C2 **wick extreme remains the structural stop**. Do not substitute C2 open for a bearish C2 SELL or for a bullish C2 BUY.
Code: `three_candle/research_gold_v2_early_body_cross.py` updated accordingly (separate from confirmed C4-entry `backtest_gold_v2.py`).

30 Oct 2026 15m turning-point reference events (five-minute execution):
| C2 GMT | Side | C2 body threshold | First trigger GMT | Entry | C2 structural stop | Risk | Swing-trail exit | Gross swing gain |
|---|---|---:|---|---:|---:|---:|---|---:|
| 05:30 | SELL (red C2) | 4011.80 (close) | 05:45 | 4011.80 | 4021.20 | 0.234% | 08:15 @ 3997.80 | +0.349% |
| 07:45 | BUY (red C2) | 3990.00 (open) | 08:00 | 3990.00 | 3974.70 | 0.383% | 11:55 @ 3974.70 | -0.383% |
| 08:45 | SELL (green C2) | 3998.60 (open) | 09:35 | 3998.60 | 4009.20 | 0.265% | 19:55 @ 3894.20 | +2.611% |

Gross backtest (three ex-post C3-confirmed selected references, all over the max .20% SL):
- Swing trailing 2 wins / 1 loss (66.7%), +2.5764% summed.
- Step trailing 3/3 wins (100%), +0.6891% summed.
- Half profit + swing 3/3 wins (100%), +1.7800% summed.
- **Under locked 0.20% structural risk: 0 eligible, no executable return.**

CRITICAL CAUSALITY: These three events were initially selected by a filter that checks C3 confirmation; an entry occurring during C3 **cannot know its close**. Therefore all the above are retrospective research hypotheses, not a valid causal signal-by-signal live backtest. The scanner must evaluate C2-only size/swing conditions at C2 close and independently test all ensuing body-edge triggers, including patterns whose C3 later fails. Avoid look-ahead and selection bias. 5m bars can hide crossing-vs-stop ordering; tick data needed for exact fills.


## CURRENT GOLD V2 STATUS — 2026-10-31 18:06 GMT (supersedes older research interpretations)

The **correct current research model** is in `research_gold_v2_early_body_cross.py`.
The older `backtest_gold_v2.py` tests C4 entry with a C2-wick structural stop and is a **different baseline**, not the latest body-stop strategy.

### Rules
- Identify significant turning-area sweep using C1 / completed C2 only: C2 range ≥1.0× *preceding* ATR14; C2 sweep of preceding 8-bar extreme ≥0.5× ATR14; C1 body/range ≥40%. These threshold values were fitted to the 30 Oct examples.
- **BUY trigger** = upper C2 body edge, `max(C2.Open,C2.Close)`; **SELL trigger** = lower edge, `min(...)`. Enter on the **first post-C2 5m crossing** (at level unless opening beyond).
- **BODY stop**: BUY at `min(C2.Open,C2.Close)`, SELL at `max(...)`. C2 wick remains useful for *sweep detection*, not as the body-stop entry risk level.
- Initial body-risk cap (provisional): **0.20%**; risk measured from executed entry, not necessarily the trigger if price gaps.
- Price movement **≥+0.20%** is called *fixed milestone reached*, NOT true R when risk is different from 0.20%. True 1R = actual entry-to-body-stop risk, which differs for each trade.
- C3 confirmation is recorded **after the fact** and not used to allow the earlier C2-body entry, avoiding look-ahead. Compare C2-only candidates against C3-confirmed candidates separately.
- 5m OHLC can touch entry AND stop in the same candle; mark **UNRESOLVED_ENTRY_STOP_5M**, neither win nor loss until reliable 1m/tick sequencing. Do not assume a favorable path.

### 30 October 2026 highlighted three candidates
| C2 time UK | Side | Body entry trigger | Actual early-trigger time | Body stop | Body risk | Fixed +0.20% observed? | Swing trailing research illustration | Execution notes |
|---|---|---:|---|---:|---:|---|---|---|
| 05:30 | SELL | 4011.80 | 05:45 | 4016.10 | 0.107% | YES | +0.349% | Simulatable, inside 0.20% cap |
| 07:45 | BUY | 3990.00 | 08:00 | 3984.50 | 0.138% | YES (subsequent high 4009.20) | **NOT VALIDATED** | The 08:00 5m candle had low 3982.20 and high 3996.00; crossed both entry 3990 and stop 3984.50. Intrabar ordering unknown, so NO confirmed win or loss. |
| 08:45 | SELL | 3998.60 | 09:35 | 4007.20 | 0.215% | YES | +2.611% | Simulatable but EXCEEDS 0.20% cap |

These are **user-selected historical turning-point examples**, not proof that the whole C2-only scanner generates only three candidates, nor that the rules have 100% forward success. A later historical price excursion at +0.20% does not demonstrate a successful live fill if an entry candle is ambiguous.

### Three different, non-interchangeable rates
- **Fixed +0.20% historical favourable movement:** **3/3 (100%)** for the three retrospectively highlighted patterns. This is a *price-path statistic*, not a realised trading win rate.
- **Simulated swing-exit outcomes (body-stop model):** 05:30 SELL +0.349%; 08:45 SELL +2.611%; **07:45 BUY unresolved**. On the two assessable historical cases, 2/2 positive, +2.960% summed gross; this is NOT a 3/3 verified strategy win rate.
- **Within the ≤0.20% body-stop cap and with 5m unambiguous fill:** 05:30 SELL only, +0.349% simulated swing gain. 08:45 SELL is 0.215% risk and ineligible. 07:45 BUY is below cap but its entry/stop sequencing is unresolved. Hence do NOT report +2.960% as risk-compliant portfolio P&L.

The prior historical **07:45 BUY -0.383%/-0.448%** was from the older *C2 wick stop* or hypothetical holding model, and must **not be reused** as an outcome under the revised BODY stop. Prior step/partial “all three winners” numbers were also hypothetical and not valid verified execution results.

### Reproducible scripts
```bash
python three_candle/detect_gold_v2_swings.py --date 2026-10-30
python three_candle/research_gold_v2_early_body_cross.py --date 2026-10-30 --reference-only
python three_candle/research_gold_v2_early_body_cross.py --date 2026-10-30 --out three_candle/results/gold_v2_body_c2_all.csv
```
Use the **full-candidate** run (without `--reference-only`) for signal count and unbiased research metrics. The reference-only run deliberately isolates the three examples the user selected. Verify fills and report date/time in UK local timezone (GMT for 30 Oct).

### Validation outstanding
- Acquire 1m/tick data to resolve the 07:45 BUY first-bar ordering; don't invent a fill.
- Full-day C2-only cohort execution and September/October out-of-sample analysis.
- Compare Gold body-stop SL minimum thresholds (0.08% suggested but not validated) and 0.20% cap without cherry-picking.
- Portfolio overlap, stop slippage, futures contracts, costs, timezone, price ticks and Yahoo/TradingView rolling differences.
