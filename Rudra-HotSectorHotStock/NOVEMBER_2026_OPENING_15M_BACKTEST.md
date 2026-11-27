# ASJR HotSector — November 2026 opening 15-minute strategy backtest

**Scope:** 18 US trading days, 2–25 November 2026 (not the entire November calendar month). 180/180 stock-day historical 5m files were validated in the ASJR master data. Read-only historical replay; no live trades.

## Exact strategy

1. At 09:45 ET / **14:45 UK**, select the strongest of the 11 sector ETFs from the completed 09:30–09:45 ET 15-minute candle.
2. Take that sector's 10 historical candidate stocks, rank on first-15-minute stock return, take the **top three**, and select the one with greatest cumulative **opening-15-minute share volume**.
3. Buy one position at the 14:45 UK five-minute candle **open**. Initial SL is **1% below fill**.
4. On reaching +1% from entry, raise stop to breakeven; at +2%, raise it to +1%; every additional 1% gain raises the stop another 1%. No fixed take-profit. Remaining positions exit at last regular-session 20:55 bar **close**.
5. Test two intrabar orderings, **O→L→H→C (low-first)** and **O→H→L→C (high-first)** for each five-minute candle. The actual order is not inferable from OHLC data.

## Overall results

| Metric | Low-first | High-first |
|---|---:|---:|
| Trades | 18 | 18 |
| Winners | 5 | 4 |
| Losers | 11 | 11 |
| Breakeven | 2 | 3 |
| Win rate (positive only) | 27.778% | 22.222% |
| **Sum of gross trade returns** | **+1.362%** | **-1.638%** |
| Average gross trade return | +0.076% | -0.091% |
| Fully allocated daily compounding | +1.132% | -1.814% |
| Max closed-trade peak-to-trough DD | -4.901% | -6.000% |
| Profit factor | 1.124 | 0.851 |

**R-unit view:** Because initial SL distance is 1% of entry, each +1% gross move is **+1R** and each −1% stopped loss is **−1R**. Across the 18 trades the arithmetic total is roughly **+1.362R or −1.638R**, depending on intrabar order. This is a gross return on 100% nominal stock exposure per trade, not an account return if capital allocation is smaller.

## Day-by-day ledger

| Date | Sector | Selected stock | Entry | Low-first P/L | High-first P/L | Exit (low / high) |
|---|---|---|---:|---:|---:|---|
| 2026-11-02 | XLY | CVNA | $72.380 | -1.000% | -1.000% | STOP 14:45 / STOP 14:45 |
| 2026-11-03 | XLK | APH | $85.030 | -1.000% | -1.000% | STOP 15:10 / STOP 15:10 |
| 2026-11-04 | XLK | ANET | $186.780 | -1.000% | -1.000% | STOP 15:20 / STOP 15:20 |
| 2026-11-05 | XLE | XOM | $172.450 | -1.000% | -1.000% | STOP 16:35 / STOP 16:35 |
| 2026-11-06 | XLV | HUM | $439.950 | -1.000% | -1.000% | STOP 14:45 / STOP 14:45 |
| 2026-11-09 | XLY | TSLA | $376.110 | +0.000% | +0.000% | STOP 16:35 / STOP 16:35 |
| 2026-11-10 | XLK | AMD | $518.460 | +3.000% | +0.000% | STOP 15:15 / STOP 14:50 |
| 2026-11-11 | XLP | KDP | $37.670 | +1.619% | +1.619% | EOD 20:55 / EOD 20:55 |
| 2026-11-12 | XLK | ANET | $199.300 | +2.000% | +2.000% | STOP 16:40 / STOP 16:40 |
| 2026-11-13 | XLC | META | $633.390 | -1.000% | -1.000% | STOP 15:20 / STOP 15:20 |
| 2026-11-16 | XLK | FLEX | $73.770 | -1.000% | -1.000% | STOP 15:00 / STOP 15:00 |
| 2026-11-17 | XLB | FCX | $56.830 | -1.000% | -1.000% | STOP 15:00 / STOP 15:00 |
| 2026-11-18 | XLY | CMG | $36.460 | +1.289% | +1.289% | EOD 20:55 / EOD 20:55 |
| 2026-11-19 | XLK | P | $112.050 | -1.000% | -1.000% | STOP 14:45 / STOP 14:45 |
| 2026-11-20 | XLY | ORLY | $94.450 | -1.000% | -1.000% | STOP 17:45 / STOP 17:45 |
| 2026-11-23 | XLV | MRNA | $211.330 | -1.000% | -1.000% | STOP 14:45 / STOP 14:45 |
| 2026-11-24 | XLV | MRNA | $219.760 | +0.000% | +0.000% | STOP 14:50 / STOP 14:45 |
| 2026-11-25 | XLE | SLB | $46.480 | +4.454% | +4.454% | EOD 20:55 / EOD 20:55 |

### What makes the result unreliable?

- **Material look-ahead bias:** The 10 stock candidates per sector/day were selected retrospectively from **full-day website gainers**. Those were **not knowable** at 09:45 ET. Ranking their first 15 minutes in retrospect is not an unbiased implementation of an IBKR live opening scanner.
- **Intrabar sequencing:** The single path-sensitive example is **AMD on 10 November:** +3% in the low-first path versus 0% in the high-first path. Neither OHLC-only scenario proves the executable outcome.
- **Idealised fills:** No spread, commissions, market-order latency, partial fills, tick-size stop rounding or stop slippage. An initial 1% stop can lose more than 1% if filled through the level.
- **Short and incomplete sample:** 18 sessions cover 2–25 November only. The rest of the calendar month is outside this source dataset.

**Conclusion:** 11 losses in both path models and a return that changes sign with five-minute intrabar ordering. This experiment does not establish a tradeable profitable strategy. The next meaningful validation requires point-in-time 09:45 candidate data across the whole eligible sector universe, then 1-minute or tick-level sequence confirmation and costs.

### Reproducibility

- Source [November daily Top 10 master CSV](november_2026_daily_top10_stocks.csv).
- Read-only backtest script: [backtest_nov2026_opening_15m.py](backtest_nov2026_opening_15m.py).
- Detailed [18-trade results CSV](november_2026_opening_15m_backtest_results.csv).

```bash
python Rudra-HotSectorHotStock/backtest_nov2026_opening_15m.py --output /tmp/asjr_nov2026_replay.csv
```
