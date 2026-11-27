# RudraEMA5 — V2 vs V3: Six-stock, three-month validation (2026)

**Study run:** 27 November 2026. **Status: NOT independently validated as profitable.** Static IBKR Gateway 5-minute `TRADES` data, including available extended-hours. No order routing. Frozen parameters; this study did **not** alter thresholds to make the cross-stock test look better.

## Coverage and quality

- **Six symbols:** AAPL, AMD, INTC, NVDA, PLTR and TSLA.
- **18 stock-month files:** September (4,032 bars/stock), October (4,224 bars/stock), November (3,456 bars/stock), **70,272 five-minute bars total**.
- Original CSVs: [September](../../ASJR-Three-Candle-Original/data/2026-09/), [October](../../ASJR-Three-Candle-Original/data/2026-10/), [November](../../ASJR-Three-Candle-Original/data/2026-11/).
- Original manifests report IBKR Gateway port 4002, 5-minute OHLCV, UTC timestamps and `errors: []`, but `verified_complete: false`. The dashboard audit found **no duplicate timestamps or invalid OHLC envelopes** in the 18 imported CSVs. Historical exchange/extended-hour coverage and corporate-action handling are not independently certified.
- Numerous zero-volume five-minute candles exist in some files, especially AMD and PLTR. They were NOT screened out in the original frozen V2 or V3 rules; their effect should be tested before claiming real-world execution feasibility.
- File time ranges: September 1 08:00 UTC to September 30 23:55 UTC; October 1 08:00 UTC to October 30 23:55 UTC; November 2 09:00 UTC to November 26 00:55 UTC. Dates and day end follow `Europe/London` daylight-saving conversion, including the 25 October 2026 transition.
- **COHR November** (additional **3,564 eligible five-minute bars**, through 27 November 18:00 UK) is **separate** and excluded from the six-stock statistical totals because its November performance was part of choosing V3.

## Frozen trading logic

- EMA5 of closes declines at least **0.15% over 3 consecutive complete five-minute bars** by C1 close.
- C1 high **strictly below EMA5(C1)**.
- The preceding 24 completed five-minute bars' highest high to C1 low drops **at least 2%** (rolling-high proxy; not a formal swing pivot algorithm).
- **Both V2 and V3:** Wilder RSI(14) of closes strictly below 36 at C1 close.
- **V3 only:** RSI(14) at C1 close is **greater than RSI(14) of the preceding completed candle** (strictly rising). V2 has no RSI-rising rule.
- C2 = immediately next 5-minute candle, intrabar BUY threshold = `max(ceil_cent(C1.close*1.002), ceil_cent(C1.high+0.02))`.
- Initial stop = 1% below entry; at +1% favorable price movement, retain all shares and activate a **0.2% trailing stop** beneath subsequent highest observed price. No fixed profit target.
- Previous 5%-of-C1 candle-range C2-low filter is **removed**.
- One active position per **UK calendar day**; mark any remaining position out at that day's final observed close. Trades measured as 1R = 1% share-price move, **not account equity percent**.
- 5-minute OHLC fill convention: assume stop-first when a newly entered bar also touches the initial stop; prior active stop checked before updating same-bar trailing stops. If the bar closes through a newly ratcheted trail, model an exit at that trail. **Tick-by-tick order is NOT known.**

## Cross-stock comparison (excludes COHR)

| Metric | V2 | V3 |
|---|---:|---:|
| Trades | **405** | **196** |
| Winning trades | 164 | 89 |
| Losing trades | 241 | 107 |
| Win rate | 40.49% | 45.41% |
| Gross summed price-based R | **-46.10117R** | **-0.54697R** |
| Stock-months positive / negative / zero | 6 / 12 / 0 | 8 / 9 / 1 |

V3 substantially cuts drawdowns **relative to V2 gross summed losses**, but its aggregate simulated expectancy is **-0.00279R/trade** before all trading costs. A near-zero gross result is NOT a positive net edge.

### V3 by stock and month (gross R)

| Stock | Sep 2026 | Oct 2026 | Nov 2026 | Total |
|---|---:|---:|---:|---:|
| AAPL | +0.000 | -1.000 | +3.184 | +2.184 |
| AMD | +7.544 | -0.001 | -5.282 | +2.262 |
| INTC | +0.631 | +1.276 | +3.011 | +4.918 |
| NVDA | +3.466 | -0.037 | -6.296 | -2.867 |
| PLTR | +0.865 | -3.872 | -0.686 | -3.694 |
| TSLA | -0.388 | -4.183 | +1.222 | -3.349 |
| **Total** | **+12.117** | **-7.817** | **-4.847** | **-0.547** |

Monthly V3 counts: September **33 trades / 21 wins**, October **58 trades / 22 wins**, November **105 trades / 46 wins**. The newer months performed worse than September; no evidence yet that the RSI-up condition is robust across different conditions.

### V2 by month, same six stocks

September **55 trades / +8.746R**; October **113 trades / -30.007R**; November **237 trades / -24.841R**. Total **-46.101R**.

### COHR in-sample reference only (not part of cross-stock totals)

November 2–27 (cutoff 27 Nov 18:00 UK): V2 **70 trades / 30 winners / -4.59185R**; V3 **23 trades / 14 winners / +8.64448R**. This was the original selection sample; its favorable V3 outcome must not be presented as out-of-sample validation.

## Dashboard and reproducibility

- [Interactive seven-stock dashboard](../dashboard/) with stock, month (Sep/Oct/Nov), date, version (V2/V3), timeframe (5m/15m/30m/1H), swing/RSI/EMA thresholds, trade markers and daily CSV export.
- [Single-file offline dashboard](../dashboard-offline.html) bundles all seven stock archives without a web server.
- [Complete machine-readable 18-stock-month daily ledger](RudraEMA5_6stocks_3months_V2_V3.json).
- [Read-only Python V3 single-instrument implementation](../backtest_rsi_rising.py). The dashboard's UK time handling is implemented in [engine.js](../dashboard/engine.js).
- When 15m/30m/1H is selected, complete native 5m bars are aggregated and **indicators, filters and trades are recalculated**; those are different strategies, not a mere rendering change. The validated reference numbers in this document are 5m only.

## Conclusions, limits and next experimental protocol

- The frozen November COHR V3 improvement **does not consistently transfer** to the other six stocks. Avoid declaring V3 a profitable strategy; the test is roughly breakeven before costs.
- The same three months have now been inspected. Subsequent parameter tuning on them would introduce selection bias; validate hypotheses on truly untouched months or forward paper trades.
- The trailing stop is just **0.2%**; confirm trigger, intrabar order, trailing-stop ratchets, spread and slippage using **1-minute and preferably tick data**; confirm if extended-hours participation and liquidity are realistic.
- Maintain position sizing, maximum slippage and actual commissions in separate research scenarios; price R is not account P&L.
- Inspect stock-specific regime filters if pursuing this strategy, but freeze candidates before an untouched comparison.
