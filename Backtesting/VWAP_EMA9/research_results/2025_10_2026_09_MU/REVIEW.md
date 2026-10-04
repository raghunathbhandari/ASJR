# MU entry research: 60% in each of 12 months

**The expanded target is not achieved.** September improved to 62.5% while retaining all 10 previously Good entries, but only December and September reach 60% with the same rule across the available year. The best rule retaining all 89 reference winners is still insufficient: 241 trades, 89 Good, 152 Bad, 36.93% success, **-7.23% simulated gross compounded return** and -27.12% under a 0.10% round-trip cost stress assumption.

The 2,845-entry-rule pool, 256 SPY/NVDA market-context combinations and a learner trained exclusively on earlier months do not meet the target. None is promoted as a live system. Repeated searches on this data are exploratory, not independent confirmation of a 60% probability.

## Monthly results for the September-improved rule

| Month | Trades | Good | Bad | Success | CompoundPct | Net10bpPct |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-10 | 9 | 3 | 6 | 33.33% | -0.64% | -1.53% |
| 2025-11 | 18 | 4 | 14 | 22.22% | -4.96% | -6.66% |
| 2025-12 | 15 | 9 | 6 | 60.00% | 1.57% | 0.05% |
| 2026-01 | 19 | 6 | 13 | 31.58% | 2.51% | 0.59% |
| 2026-02 | 18 | 7 | 11 | 38.89% | 0.94% | -0.86% |
| 2026-03 | 23 | 9 | 14 | 39.13% | 2.86% | 0.52% |
| 2026-04 | 23 | 11 | 12 | 47.83% | 10.13% | 7.63% |
| 2026-05 | 31 | 10 | 21 | 32.26% | -4.60% | -7.52% |
| 2026-06 | 32 | 9 | 23 | 28.12% | -11.56% | -14.36% |
| 2026-07 | 19 | 4 | 15 | 21.05% | -5.11% | -6.90% |
| 2026-08 | 18 | 7 | 11 | 38.89% | 0.65% | -1.15% |
| 2026-09 | 16 | 10 | 6 | 62.50% | 2.40% | 0.78% |

October 2025 is partial: Oct 1 is missing. Coverage checks against the exchange calendar find all expected regular-session bars for the other eleven months. These are 12 observed calendar buckets, **not 12 complete months**.

Good/Bad means positive/negative gross price return. At the illustrative 0.10% round-trip cost, September's success rate is **50%**, although its simulated net compounded return remains +0.78%. Two retained Good trades make less than 0.02% each and become net losers. Fees and slippage need actual execution assumptions before treating any result as realizable profit. Compounding assumes full-notional reinvestment for non-overlapping trades, not fixed-risk sizing.

## Reusable rule and retained entries

BUY-only. At the signal close, price must be above continuous EMA9 and provisional daily VWAP (HLC3 weighted by 24-hour volume, midnight UTC reset). EMA9 must rise over three intervals. Five consecutive regular-session candles require positive high and low regression slopes and at least 0.2% midpoint improvement; not every candle must make a higher high. Close must exceed the previous 10 highs.

The final September research configuration adds:

- RSI14 between 60 and 90.
- MACD(12,26,9) histogram nonnegative: MACD line at least its signal line.
- Volume at least the mean of matching New York-time bars over the preceding 20 observations, with at least 10 valid regular-session observations. Early-close after-hours bars are excluded from this template.
- At least three higher-low intervals out of the last four (five candles).
- Bollinger BandWidth(20,2) at least 80% of its value three bars earlier. This permits modest contraction; it does **not** require width to rise.
- RSI no lower than three bars earlier.

Directional efficiency and median-based volume filters were removed in a 256-configuration ablation because they added no benefit to the September result. The same 16 trades remain.

Stop is the five-bar low minus $0.01. Exit is the first later candle closing below EMA9, with intrabar stop checked first; gaps below stop fill at open. Otherwise force exit on the last regular-session candle. There is no fixed target or 1:3 exit. Labels are candle **start times**; confirmation occurs five minutes later. Entries at the signal close are hypothetical closing fills.

All 10 September Good entries retain exactly the same entry, stop, exit, exit reason and gross return as the preceding 22-trade version. Six Bad entries were removed. Oct 1, 2026 **17:40 UK** remains Good (+1.898% gross), and the later Oct 1 losing entry is removed. Previously rejected flat entries (Oct 1 20:25 and Sep 24 15:25) and Sep 30 18:50 remain rejected.

The VWAP reset remains provisional: one Oct 2 premarket reference agrees, but the Oct 1 screenshot VWAP has not been fully matched. It would be misleading to claim exact TradingView equivalence across this year. Public chart quotes do not substitute for the same feed, session and indicator settings.

## Annual review and learning model

`review_all_months.py` evaluates each rule against every month and records trade counts, gross success, returns, cost stress and exact winner retention. A month with no trades does not pass. It separately records the 10 reviewed September winners and all 89 winners of the annual reference rule. The ranking cannot silently remove winners to report a higher success rate.

`market_context_review.py` uses simultaneous SPY and NVDA 5-minute bars from the existing Git datasets. It tests eight conditions and all 256 combinations: above EMA9, above RTH VWAP, rising EMA9 and positive five-bar return for each symbol. Its context VWAP is explicitly RTH-only; MU VWAP is unchanged. No later or stale forward-filled context candle is allowed. Every nonempty context filter loses at least one reference winner; none passes the annual requirement.

`walkforward_entry_model.py` uses 30 normalized candle/trend/volume features. It trains a fixed depth-3 gradient-boosted classifier only on completed historical setup outcomes from earlier months. Absolute price, month/date, future return, MFE and MAE are excluded from inputs. Training exits must precede the test month. Actual one-position trading is evaluated separately from overlapping historical setup labels. Model scores are uncalibrated estimates, not guaranteed probabilities.

Oct-Dec 2025 provide initial training. Jan-Sep 2026 are predicted forward with fixed score thresholds 0.5, 0.6, 0.7 and 0.8. The model fails the monthly success and winner-retention criteria. Very high thresholds produce few or zero trades; those months remain visible as failures rather than being omitted. To test this learner out of sample across Oct 2025-Sep 2026, at least three earlier months of 5-minute history plus the missing Oct 1 session are needed. Additional history enables the test; it does not guarantee 60%.

## Session fix and verification

The original wall-clock RTH mask incorrectly treated every weekday as a 16:00 New York close. `market_sessions.py` now uses a verified exchange-calendar profile with holidays, weekends and 13:00 early closes. It preserves overnight bars for continuous indicators. The supported calendar window is explicit; unknown dates require an updated verified profile. Calendar dates are market structure, not exceptions selected by trade outcomes. The correction changes some rejected candidates' yearly results but leaves the reference rule and September milestone unchanged.

Checks performed: early-close and holiday boundaries; prefix invariance of all added indicators and historical signal flags; identical September replay after correcting RSI slope ordering; exact preservation of all ten winning execution records; and chronological training-cutoff audits. The source datasets and importer were not changed.

## Reproduce

From the repository root, with pandas, numpy and scikit-learn installed:

```sh
python Backtesting/VWAP_EMA9/filtered_buy_detector.py --csv Backtesting/BacktestData/IBKR/MarketData24h/5m/MU_5m.csv --config Backtesting/VWAP_EMA9/research_results/2025_10_2026_09_MU/quality_config.json --start-date 2026-09-01 --end-date 2026-09-30 --output /tmp/mu_quality_replay
python Backtesting/VWAP_EMA9/review_all_months.py --csv Backtesting/BacktestData/IBKR/MarketData24h/5m/MU_5m.csv --candidate-table Backtesting/VWAP_EMA9/research_results/2026_09_MU/all_candidates.csv --ablation-table Backtesting/VWAP_EMA9/research_results/2025_10_2026_09_MU/september_ablation.csv --reference-config Backtesting/VWAP_EMA9/research_results/2025_10_2026_09_MU/quality_config.json --output /tmp/mu_annual_review
python Backtesting/VWAP_EMA9/walkforward_entry_model.py --csv Backtesting/BacktestData/IBKR/MarketData24h/5m/MU_5m.csv --reference-trades Backtesting/VWAP_EMA9/research_results/2025_10_2026_09_MU/annual_trades.csv --output /tmp/mu_walkforward
python Backtesting/VWAP_EMA9/market_context_review.py --csv Backtesting/BacktestData/IBKR/MarketData24h/5m/MU_5m.csv --spy-csv Backtesting/BacktestData/IBKR/MarketData/5m/SPY_5m.csv --nvda-csv Backtesting/BacktestData/IBKR/MarketData/5m/NVDA_5m.csv --reference-config Backtesting/VWAP_EMA9/research_results/2025_10_2026_09_MU/quality_config.json --output /tmp/mu_context
```

Full candidate and model logs are saved as gzip CSV files. They can be read directly with `pandas.read_csv(path)`.

## Primary sources consulted

[TradingView MACD](https://www.tradingview.com/support/solutions/43000502344-moving-average-convergence-divergence-macd-indicator/), [Relative Volume at Time](https://www.tradingview.com/support/solutions/43000705489-relative-volume-at-time/), [Bollinger BandWidth](https://www.tradingview.com/support/solutions/43000501972-bollinger-bandwidth-bbw/), [RSI](https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/), [Choppiness Index](https://www.tradingview.com/support/solutions/43000501980-choppiness-index-chop/) and [Chaikin Money Flow](https://www.tradingview.com/support/solutions/43000501974-chaikin-money-flow-cmf/). These document indicator definitions; our combined thresholds are research hypotheses, not source-promised success rates.

[NYSE calendar](https://www.nyse.com/trade/hours-calendars), [Nasdaq calendar](https://www.nasdaqtrader.com/Trader.aspx?id=Calendar), [Nasdaq 2025 PDF](https://www.nasdaqtrader.com/content/technicalsupport/2025tradingcalendar.pdf), and [scikit-learn classifier documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html).
