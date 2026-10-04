# MU September 2026 BUY detector research

The 60% target has **not** been met while keeping every baseline Good entry. A September-tuned candidate reached 66.7%, but missed one winning move and changed five other winning entry times. It also performed poorly on separate months. It is rejected as the final detector.

| Version | Trades | Good | Bad | Gross success | Simulated compound gain | All 9 baseline Good entries retained |
| --- | --- | --- | --- | --- | --- | --- |
| Frozen baseline | 38 | 9 | 29 | 23.7% | -3.504% | 9/9 |
| Target-only research candidate, rejected | 12 | 8 | 4 | 66.7% | +2.629% | 3/9 exact; 8/9 overlapping profitable moves |
| Best tested configuration retaining all winners | 22 | 10 | 12 | 45.5% | -0.196% | 9/9 |

The winner-retaining version also keeps Oct 1 **17:40 UK**, with an EMA9 exit on the 19:05 candle and +1.898% gross price return. It still loses on Oct 1 19:55. Nothing here is ready for live signal deployment. The existing `buy_close_detector.py` has not been replaced.

## Rules and findings

All variants are BUY-only, regular-hours entries. EMA9 runs continuously on close. Daily VWAP is HLC3 weighted by volume across the 24-hour data, with a **provisional midnight UTC reset**. TradingView permits different anchor/source/session settings; the chart match is still incomplete. The Oct 2 08:45 UK reference gives EMA9 1094.116 and VWAP 1092.069, but the Oct 1 screenshot VWAP remains different. Do not apply an arbitrary price buffer to claim a match.

The baseline requires close above EMA9 and VWAP, three rising EMA9 intervals, five contiguous RTH candles with positive high and low slopes, midpoint movement >=0.2%, and close above the previous 10 highs. No future pivots or outcome labels enter the detector.

The winner-retaining configuration adds five-bar directional efficiency >=0.6, volume at least the median of the same NY-time bucket over the preceding 20 observed sessions (minimum 10), and RSI14 between 60 and 90. It uses a **five-bar low minus $0.01 stop**, wider than the baseline signal-low stop. This changes risk; it is an experimental configuration, not a production change. Efficiency is `(current close - close five bars ago) / sum(abs(close changes) over five bars)`.

Candle tests included green candle, body >=30% of range, upper wick <=50% of range, and their combinations with momentum and volume. They did not improve the strongest winner-retaining result. We also compared EMA reclaims, pullbacks, 3/10-bar breakouts, EMA21, completed 15-minute trend, RSI/ADX and several stop placements. The target-only rule uses rising EMA momentum >=0.75 ATR over three bars and ADX14 <=25, with no 10-bar breakout requirement. That ceiling happened to select early September rallies; it is not evidence of a universal high-probability rule.

## September candle results, all times UK BST

| CandleTimeUK | Status | GainPct | Reason |
| --- | --- | --- | --- |
| Sep 01 15:40 | Good | +0.801% | EMA9 exit |
| Sep 02 18:45 | Bad | -0.276% | EMA9 exit |
| Sep 02 19:45 | Bad | -0.209% | EMA9 exit |
| Sep 02 20:50 | Bad | -0.272% | RTH end |
| Sep 03 16:00 | Bad | -0.759% | EMA9 exit |
| Sep 03 19:00 | Good | +0.168% | EMA9 exit |
| Sep 03 20:50 | Good | +0.018% | RTH end |
| Sep 04 17:20 | Bad | -0.194% | EMA9 exit |
| Sep 04 19:40 | Bad | -0.195% | EMA9 exit |
| Sep 04 20:50 | Good | +0.284% | RTH end |
| Sep 09 14:50 | Good | +0.719% | EMA9 exit |
| Sep 14 16:30 | Bad | -0.604% | EMA9 exit |
| Sep 14 17:45 | Good | +0.665% | EMA9 exit |
| Sep 18 14:55 | Good | +0.016% | EMA9 exit |
| Sep 18 17:50 | Good | +1.273% | EMA9 exit |
| Sep 21 19:10 | Good | +0.102% | EMA9 exit |
| Sep 22 15:00 | Bad | -0.667% | EMA9 exit |
| Sep 22 17:05 | Bad | -0.257% | EMA9 exit |
| Sep 22 20:00 | Good | +0.107% | RTH end |
| Sep 24 17:35 | Bad | -0.341% | EMA9 exit |
| Sep 24 19:55 | Bad | -0.413% | EMA9 exit |
| Sep 28 17:20 | Bad | -0.135% | EMA9 exit |

Good means positive gross exit-minus-entry. Two Good trades gain only about 0.016% and 0.018%; these become losses with a 10-basis-point round-trip cost assumption. The winner-retaining version then has **36.4% net success and -2.369% simulated compounded return**. The 66.7% candidate drops to 58.3% net success under the same cost assumption.

## Separate dates

The 66.7% candidate scores 21.4% in June, 31.3% in July and 41.7% in August. The winner-retaining version scores 18.8%, 21.7% and 40.0%, respectively. These checks reject a general 60% success claim. September was used to select the final reported candidates, so its figures are in-sample. Earlier split-based attempts also failed the later September dates. Multiple iterations have now inspected May-August; those months should not be called untouched holdouts for future revisions.

## Reproduce

From the repository root:

```sh
python Backtesting/VWAP_EMA9/research_mu.py --csv Backtesting/BacktestData/IBKR/MarketData24h/5m/MU_5m.csv --output /tmp/mu_search --selection September
python Backtesting/VWAP_EMA9/review_candle_patterns.py --csv Backtesting/BacktestData/IBKR/MarketData24h/5m/MU_5m.csv --output /tmp/mu_retention
python Backtesting/VWAP_EMA9/filtered_buy_detector.py --csv Backtesting/BacktestData/IBKR/MarketData24h/5m/MU_5m.csv --config Backtesting/VWAP_EMA9/research_results/2026_09_MU/retention_config.json --start-date 2026-09-01 --end-date 2026-09-30 --output /tmp/mu_replay
```

`signals.csv` contains every RTH candle's indicators and possible BUY marker; `trades.csv` contains executed research entries and Good/Bad outcomes. The same `signal_mask` is used for backtesting and reusable chart markers. Possible signals while a position is open are not counted as additional trades.

## Audit and limitations

Data: 71,962 bars; UTC 2025-10-02 00:05:00+00:00 to 2026-10-02 23:55:00+00:00. CSV SHA256 `d83c0b716414564aed29d69412569d67d7d6b70f39640d11d956a0e207007406`. Final systematic sweep: 2,253 configurations including duplicates; candle-retention sweep: 256. The CSV tables include rejected candidates. Earlier iterations were exploratory; their poor checks informed later revisions.

Entries assume the signal candle's close; its conditions are known only five minutes after its start label. This is a hypothetical closing fill, not an executable-fill guarantee. Stops begin on the next bar; an opening gap below stop fills at open. Stop takes priority over EMA9 close exit, and positions close at the last available RTH bar. There is **no fixed target and no 1:3 exit**. Compounded gains assume reinvestment of the full notional for each non-overlapping trade; they are not a risk-sized portfolio return. MFE/MAE include the exit bar, whose intrabar sequence is unknown, and are diagnostic only.

Prefix comparisons passed for EMA9, VWAP, ATR, RSI, ADX, momentum and completed 15-minute features at three reference cutoffs. Removing all later bars does not change historical signals. No bars were deleted as losing outliers. RTH OHLC bounds passed basic validation. Yahoo daily highs/lows agreed for Sep 29-30, but last five-minute closes and volume differed from the daily feed; this is not an exact chart validation. Yahoo's interactive chart could not be opened in this session. No importer or production bot was changed.

Reference documentation: [TradingView VWAP](https://www.tradingview.com/support/solutions/43000502018-volume-weighted-average-price-vwap/), [TradingView EMA](https://www.tradingview.com/support/solutions/43000592270-exponential-moving-average/), [IBKR historical data filtering](https://interactivebrokers.github.io/tws-api/historical_data.html).

The reusable audit identifies every previously Good candle a candidate loses. Retaining known winners retrospectively cannot guarantee retaining future winners. Further progress needs a rule supported by entry structure and independent evidence; selecting dates or hardcoding winning situations would invalidate this detector.
