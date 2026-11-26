# September 2026 — original ASJR Three-Candle on six high-volume US stocks

Study recorded: **26 November 2026 (UK)**. Data: existing verified IBKR Gateway 5-minute UTC files from `ASJR-Three-Candle-Original/data/2026-09/`, 4,032 rows per stock, total **24,192**. All 21 New York regular sessions per stock had 78 5m bars, 26 complete 15m bars, and no zero-volume RTH bars. The original entry-reference / target-touch counts for NVDA, INTC and PLTR match the October 25 ten-ticker research archive: NVDA 9/9/9/7, INTC 11/11/9/8, PLTR 11/11/11/10.

## 1. Frozen original signal rules (unchanged)
- Resample each New York 09:30–16:00 session of 5m IBKR OHLCV into complete 15m bars; do not connect bars across sessions. Display signal times in UK local timezone.
- C1 reference, C2 bullish (`close>open`), C2 lower wick (`open-low`) strictly greater than C2 body (`close-open`), C2 low below C1 low and C2 close above C1 low.
- C3 summed 15m volume strictly above C2 summed volume, C3 close above C2 close. No unrequested EMA, RSI, ADX, gap, or trend filters.
- Original *reference* entry is C2 close, SL=C2 open, and 1R price step = max(C2 bullish body, 0.10% of C2 close). A signal confirmed using later C3 close/volume **cannot** have been known at the reference entry.
- Ex-post 1R/2R/3R target touch means price later reached the reference level on C3 or a subsequent 15m candle in the same NY regular session, **without requiring the stop to have survived**.

## 2. Original retrospective target-touch results

| Ticker | Setups | 1R touches | 2R touches | 3R touches |
|---|---:|---:|---:|---:|
| NVDA | 9 | 9 | 9 | 7 |
| INTC | 11 | 11 | 9 | 8 |
| TSLA | 7 | 7 | 7 | 7 |
| PLTR | 11 | 11 | 11 | 10 |
| AMD | 8 | 8 | 4 | 4 |
| AAPL | 8 | 7 | 6 | 4 |
| **TOTAL** | **54** | **53 (98.1%)** | **46 (85.2%)** | **40 (74.1%)** |

Nominal gross TARGET-ONLY price return sums at each setup's **actual** R step: **+6.545% (1R), +11.455% (2R), +14.188% (3R)**. These are NOT realized P&L, portfolio return, executed wins, or a valid net strategy gain: earlier stop-outs, entry look-ahead, fees, overlap and intrabar order are excluded. Separate 1R/2R/3R alternative scenarios: do not add together.

## 3. After-C3 hypothetical execution replay (new, not original entry)

To remove the future-C3 look-ahead, wait for completed C3 and enter long at the next 5-minute **open**, no earlier. Keep C2 open as the structural SL; 1R step is max(actual entry–SL, 0.10% of actual entry). If no next RTH bar exists, reject. Five signals occurred on the final 15m regular-session bar (15:45–16:00 ET) and **had no next regular-session entry bar**: NVDA 4 Sep, INTC 3 Sep, TSLA 25 Sep, PLTR 22 Sep and AAPL 23 Sep. **None** was rejected for entry below the stop; 49 executable-price-reference simulations remain.

Stop first on a 5m candle if both stop and fixed target appear touched (unknown intrabar ordering). A stop update to the newly reached +kR becomes effective only on the **following** 5m candle; stops can be jumped by gaps. Liquidate at the last 5m regular-session close if no exit. No commissions, slippage or bid/ask, fractional-cent target rounding, capital constraints or overlapping-trade aggregation.

| Exit model | Simulated entries | Positive exits | Negative exits | Positive-exit rate | Sum of gross trade price returns |
|---|---:|---:|---:|---:|---:|
| Fixed 1R | 49 | 27 | 22 | 55.1% | +3.118% |
| Fixed 2R | 49 | 20 | 29 | 40.8% | +4.673% |
| Fixed 3R | 49 | 19 | 30 | 38.8% | +6.461% |
| Original-style step trailing (next-bar stop update) | 49 | 27 | 22 | 55.1% | +5.342% |

Positive exits include profitable **regular-session-close exits**, so the positive-exit fraction is not the same as target fill rate.

### Original-style step-trailing breakdown

| Ticker | Original setups | Valid after-C3 entries | Positive exits | Positive-exit rate | Sum gross trade price returns |
|---|---:|---:|---:|---:|---:|
| NVDA | 9 | 8 | 7 | 87.5% | +1.095% |
| INTC | 11 | 10 | 4 | 40.0% | +1.284% |
| TSLA | 7 | 6 | 4 | 66.7% | +0.402% |
| PLTR | 11 | 10 | 8 | 80.0% | +0.902% |
| AMD | 8 | 8 | 2 | 25.0% | +1.519% |
| AAPL | 8 | 7 | 2 | 28.6% | +0.141% |
| **TOTAL** | **54** | **49** | **27** | **55.1%** | **+5.342%** |

**Important interpretation:** The percentages are sums of unweighted, independently simulated trade *stock-price percentage changes*, not a capital-normalized portfolio/account gain. Some trades overlap in time; per-ticker price point moves cannot be added. Brokerage charges, realistic spread/slippage, capital limits and stop execution quality can materially change results. One month and six cherry-picked liquid stocks cannot establish general predictive value. Do not claim live profitability.

## 4. Assessment

The original pattern catches many bullish later-session highs but overstates achievable target success when using ex-post C3 confirmation. The stronger causal test has mixed individual-stock outcomes; **NVDA and PLTR** produced higher simulated positive-exit rates in this *single sample*, while AMD's aggregate gain depended on relatively few winning trades. Avoid cherry-picking rules based on these observations; validate on October and November without modifying the September frozen rules.

## 5. Evidence and reproduction

- [Full six-stock original / step-trailing ticker summary](SEPTEMBER_2026_SIX_STOCK_SUMMARY.csv)
- [Exit variant comparison CSV](SEPTEMBER_2026_SIX_STOCK_VARIANTS.csv)
- [Reproducible Python backtest](../backtest_september_six_stocks.py) — source added; **the Python script has not yet completed an independently verified end-to-end run in this session**. The numbers here were computed directly by a separate timestamp-aware replay of all six GitHub CSV datasets.
- [Monthly IBKR originals](../data/2026-09/), [data QA and job traceability](../data/README.md).
- Run from root: `python ASJR-Three-Candle-Original/backtest_september_six_stocks.py --verify-september`. Requires `pandas`; writes detailed signal/exit CSV, summary and source audit to the results directory. Do not mix with earlier ten-ticker September 2026 results or futures/MES variants.

No new downloads or trades were placed in this study.
