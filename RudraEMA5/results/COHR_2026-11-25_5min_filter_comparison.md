# RudraEMA5 — COHR Wednesday 25 November 2026 (5-minute)

**Research replay date:** 2026-11-25 UK (GMT). Source: IBKR `TRADES` `useRTH=False` from [full November CSV](../../three_candle/data/ibkr_bridge/research-1795805412345/COHR_2026-11-01_2026-11-27_5min_UTC.csv). The day has 192 rows, 00:00–23:55 UK. Indicator EMA5 was warmed up with preceding available history.

## Trading rules

1. EMA5(close) falls at least 0.15% from 3 consecutive prior completed 5m bars to completed C1.
2. Completed C1 entire range below EMA5: `C1_high < C1_EMA5`.
3. C2 is the immediate next bar, breakout buy threshold `max(ceil_cent(C1_close * 1.002), ceil_cent(C1_high + 0.02))`.
4. Initial stop `entry * 0.99`; +1% favorable movement activates trailing stop `max(old_stop, highest_seen_price * 0.998)`, no automatic full TP. Single open position.
5. Filter 1: swing-down at least 2% from the highest high of **24 previously completed 5m bars (excluding C1)** to C1 low. This rolling two-hour-high proxy is provisional: a formal swing/pivot definition is not yet supplied.
6. Filter 2: `C2_low >= C1_high - 0.05 * (C1_high - C1_low)` (C2 remains in top 5% of C1's high-low range).
7. **Causality caveat:** Filter 2 examines the completed C2 low, which is not known at the moment of an intrabar breakout. It is a strict ex-post diagnostic, NOT a verified executable strategy. Rejecting a whole C2 when low breaches the line may reject a valid breakout that happened first. Use 1-minute/tick data for sequencing.
8. Price execution inferred from 5m OHLC; stop first on already-active stops; gaps through stops filled at candle open; trail activated after +1R, same-bar trail only when candle closes below new trailing stop. Same-entry-bar stop ambiguity filled conservatively; no commissions, spreads, slippage or fills/liquidity constraints. Flat at end-of-day for this daily comparison, no carry.

## Comparison — 25 November 2026

| Strategy | Trades | Wins | Losses | Gross summed R | Sequential compounding (1% price-based risk, fully reinvested) |
|---|---:|---:|---:|---:|---:|
| Original EMA5, no new filters | 10 | 6 | 4 | +3.22198R | +3.20769% |
| + 2% two-hour swing down | 9 | 5 | 4 | +1.65308R | +1.61347% |
| + 5%-of-C1 candle guard | **0** | 0 | 0 | **0R** | **0%** |

Different filters can produce a different number of candidate C1 bars because single-position state suppresses overlapping new entries. The strict dual-filter pass screened **29 raw EMA/C1 opportunities**: 5 fail the 2% swing criterion; the remaining 24 *all fail* the C2 top-5% guard. No qualifying entry remained.

## Examples — candidate C1 times (UK/GMT)

| C1 | Swing decline | C2 Low | Required minimum C2 low | Outcome |
|---|---:|---:|---:|---|
| 14:00 | 2.8879% | 183.09 | 183.6615 | Reject Filter 2 |
| 14:50 | 6.0671% | 177.77 | 178.9985 | Reject Filter 2 |
| 15:25 | 6.5673% | 176.05 | 176.5765 | Reject Filter 2 |
| 20:40 | 3.2363% | 193.86 | 194.1245 | Reject Filter 2 |

There are also two examples where C2 meets top-5% criterion but fails swing >=2%: 11:40 C1 (1.4247% decline) and 23:05 C1 (1.3733% decline).

**Conclusion:** Filter 2 is so restrictive that none of the 24 candidates passing Filter 1 remain. Do **not** label this rule profitable or verified. Establish the intended intrabar sequencing and/or reassess C2 range threshold before applying to other dates.
