# RudraEMA5 — COHR 5-minute bullish reversal study

**Status (2026-11-27 UK):** COHR IBKR 5-minute history successfully exported. Preliminary user strategy transcribed; **do not backtest until the pending rule choices below are confirmed.** Research only; no live orders.

## Historical data

- Stock: COHR (US stock, SMART/USD).
- Source: existing ASJR IBKR Research Bridge, `ibkr_range_download`, `TRADES`, `useRTH=False`.
- Requested: 2026-11-01 through 2026-11-27 inclusive, 5-minute bars.
- Backtest cutoff: **2026-11-27 18:00 Europe/London = 18:00 UTC**. The export includes later bars; filter by exact bar timestamp and do not use any price information after the cutoff.
- Job: `research-1795805412345`.
- [Raw file](../three_candle/data/ibkr_bridge/research-1795805412345/COHR_2026-11-01_2026-11-27_5min_UTC.csv).
- [Bridge result](../RudraScanner/ResearchBridge/results/research-1795805412345.json): `status=SUCCESS`, `exit_code=0`, `rows=3572`, `errors=[]`.
- First observed CSV row: `2026-11-02T09:00:00+00:00`. The CSV also contains 27 Nov 18:35 UTC, which is later than the requested backtest cutoff.
- Preserve raw CSV unchanged, and validate clipped dataset OHLCV/timezone/duplicates/session coverage before any performance claims.

## Intended LONG setup (pending parameter confirmation)

1. Work on completed 5-minute candles and a **5-period exponential moving average of closes**.
2. EMA5 must previously be sloping down significantly. Define a measurable slope over a lookback and a threshold before testing.
3. **C1**: a completed 5-minute candle with its full high-low range below EMA5, not touching it; thus its HIGH must be below the correctly time-aligned EMA5.
4. **C2 / entry update (user-confirmed 2026-11-27 19:10 UK)**: User sets the entry threshold at **0.2% above C1 CLOSE**: `entry_threshold = C1_close * 1.002`. C2 is the immediately following 5-minute candle and entry may trigger intrabar without awaiting its close. **Still unresolved:** must C2 ALSO break C1 HIGH before entry, as originally specified? If yes, effective trigger is `max(C1_high + tick, C1_close * 1.002)`. If no, use solely `C1_close * 1.002`. Do not silently assume either variant; avoid use of C2 final close/high to make earlier decisions.
5. Initial risk: user requests `-1R`, with mention of `1%`; confirm whether 1R is exactly 1% of entry price or anchored to C1 LOW.
6. Profit target: user requests `1R` / `1:1`; confirm whether this means complete exit, partial exit, or trigger for the trail.
7. Trailing stop: user requests `0.2%` beneath upside price; confirm that it trails peak price after first +1R, and whether it replaces the initial stop.
8. Apply stop-first conservative ordering to unresolvable intra-candle target/stop conflicts in a 5-minute OHLC backtest, and model fees/slippage independently. No simultaneous overlapping trades unless approved.

## Pending confirmations

- **Slope:** suggested first test: EMA5 at C1 close at least 0.15% below its value 3 completed 5-minute bars earlier; compare thresholds rather than optimizing one in hindsight. Should slope be checked precisely at C1 or only in the preceding decline?
- **Entry threshold:** confirmed **C1 CLOSE + 0.2%**, not a cent-based C1-HIGH buffer. Clarify whether C1-HIGH breakout remains an additional mandatory condition (it may be higher than the +0.2% threshold).
- **1R stop:** fixed -1% of filled entry, or C1 low as depicted in sketch?
- **Target and trail:** +1% profit = milestone that activates trailing 0.2% from highest price, or exit part/all at +1R? If trailing, clarify intrabar activation and conflict convention.
- **Session eligibility:** all available extended-hours or regular US session only? Existing export covers extended trading.
- **Re-entry:** first C1 only in each EMA down-slope episode vs repeated eligible C1s; max one open trade.

## Notes

The sketch portrays a falling EMA5, separated candles below it, then a bullish candle crossing the preceding candle's high. The stop is sketched below the reversal low; the written risk says 1R / 1%, so no stop anchor is assumed until clarified.
