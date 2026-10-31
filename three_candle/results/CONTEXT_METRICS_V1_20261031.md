# NQ September–October — Additional descriptive metrics V1 (31 October 2026)

## Scope and status
New non-filtering column definitions are implemented in [research_market_context.py](../research_market_context.py) and wired into [export_two_month_signal_matrix.py](../export_two_month_signal_matrix.py). Run the exporter to **calculate actual per-signal values** from archived September/October NQ 5m data and generate a single-row wide CSV. The CSV is not committed by these source-code changes. Existing signals, outcomes, risk labels, proposed filters and performance are **unchanged**. Do not claim improved success or P&L until a verified, out-of-sample test with the finalized maximum 0.20% SL and 1R-step trailing engine.

## Five prioritized improvements

1. **Session VWAP**: NQ trade-date session reset at 18:00 ET, cumulative typical-price × 15m candle volume / cumulative candle volume; distance %, reclaim-up and reclaim-down. Bar-aggregated approximation; differs from tick-level VWAP, especially across incomplete archives.
2. **Liquidity / location**: 20 *previous* bar high/low, wick sweep depth % (only if close back within range), close-break of prior structure, simplified structure-shift proxy; previous *completed* NQ trade-date highs/lows and signed distance %. The structure-shift flag is **not certified ICT/SMC CHOCH**, only an operational proxy.
3. **Momentum transition**: EMA9 and EMA21 signed 3-bar slope %, distance to both, RSI14 change over one and three bars. Calculate change at candle close, not before.
4. **Volatility compression → expansion**: BB(20,2) width %, 100-bar width percentile, BB position, candle-range / ATR14, ATR percent percentile, compression-to-expansion flag (previous width percentile <=25 and current range / ATR >1.3).
5. **Session/time location**: categorical New York ET session labels and futures trade date. Time window definitions are descriptive: 18:00–02:59 US_OVERNIGHT, 03:00–08:59 EUROPE, 09:00–15:59 US_DAY, other hours US_LATE.

## Market regime

`UPTREND`: price>EMA21, EMA9>EMA21 and EMA9 slope rising.
`DOWNTREND`: mirror negative conditions.
`COMPRESSION`: BB width percentile <=25 (takes precedence).
`RANGE_OR_MIXED`: all other complete warmup states.
`UNKNOWN_WARMUP`: fewer than enough historical bars for reliable percentile.

All classifications are descriptive hypotheses—not universal professional definitions.

## Per-signal CSV layout

The existing exporter pivots each context feature to `C1_*`, `C2_*`, `C3_*` wide columns, plus `C4_*` contextual values for SELL confirmation only. The original GOOD/WEAK/BAD label is **not changed**. A C4 feature is *not permitted to be used for an earlier intrabar SELL entry without look-ahead correction.*

RVOL is **informational only**: low, medium, high RVOL each can precede a major move; do not reject a setup solely for RVOL. No new indicators are enabled as trading filters.

## Run / verification

```bash
cd /root/trading/ASJR-Synced
git fetch origin main && git merge --no-edit origin/main
python three_candle/export_two_month_signal_matrix.py
# Verify signal count and field completeness; inspect warnings and CSV.
git add three_candle/results/NQ_2026-09_10_signal_matrix.csv
git commit -m "Publish C1-C4 NQ context metrics September October"
git push origin HEAD:refs/heads/main
```

**Known data limitations**: historic source gaps and incomplete futures sessions, session VWAP from 15m OHLCV approximation, lagging/rolling indicator warmup, high/low gaps, unknown exact stop/fill sequence, incomplete trade-day prior levels. For tests, do not forward-fill missing candle data and do not overstate backtest accuracy.
