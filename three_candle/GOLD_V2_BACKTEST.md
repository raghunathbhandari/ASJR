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
