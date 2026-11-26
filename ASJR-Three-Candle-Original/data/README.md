# ASJR Original Three-Candle — IBKR 5-minute Stock Data

**Collection completed and imported 26 November 2026:** 18/18 VPS jobs returned `SUCCESS`, exit code 0, no downloader errors. All 18 original CSVs and manifests were inspected. They have the expected row count, aligned 5-minute UTC timestamps, no duplicate timestamps and no invalid OHLCV envelopes.

IBKR Gateway, Stock/SMART/USD, TRADES, 5-minute bars with premarket and after-hours (`useRTH=False`). All CSV timestamps are UTC; format research results in Europe/London. November covers completed New York sessions from 2 to 25 November (the final after-hours bar is stamped 26 November 00:55 UTC).

## Record counts and data QA

| Ticker | Sep 2026 | Oct 2026 | Nov 1–25 | Total rows | Zero-volume bars |
|---|---:|---:|---:|---:|---:|
| NVDA | 4,032 | 4,224 | 3,456 | 11,712 | 0 |
| INTC | 4,032 | 4,224 | 3,456 | 11,712 | 0 |
| TSLA | 4,032 | 4,224 | 3,456 | 11,712 | 0 |
| PLTR | 4,032 | 4,224 | 3,456 | 11,712 | 351 |
| AMD | 4,032 | 4,224 | 3,456 | 11,712 | 207 |
| AAPL | 4,032 | 4,224 | 3,456 | 11,712 | 31 |
| **Total** | **24,192** | **25,344** | **20,736** | **70,272** | **589** |

21 regular sessions in September, 22 in October, 18 from 2–25 November. The source downloader deliberately retains extended-hours candles, including zero-volume bars. **Source manifests still state `verified_complete: false`**; row-count and basic OHLC checks do not guarantee every market or corporate-action adjustment. Especially audit PLTR, AMD and AAPL zero-volume periods before using C3 volume filters. No fabricated candles.

## Imported files (shared original Git blob objects)

- [2026-09](./2026-09/) — six stocks, `TICKER_5min_UTC.csv` and `TICKER_manifest.json` each
- [2026-10](./2026-10/) — six stocks, `TICKER_5min_UTC.csv` and `TICKER_manifest.json` each
- [2026-11](./2026-11/) — six stocks, `TICKER_5min_UTC.csv` and `TICKER_manifest.json` each

Original immutable files also remain in `three_candle/data/ibkr_bridge/<job-id>/`. Importing reuses the original Git object SHA; no duplicate downloads or re-encoding.

## Traceability

| Ticker | Month | Job ID | Requested range | CSV rows | Job status |
|---|---|---|---|---:|---|
| NVDA | 2026-09 | `research-1795685200001` | 2026-09-01 to 2026-09-30 | 4,032 | SUCCESS; imported |
| NVDA | 2026-10 | `research-1795685200002` | 2026-10-01 to 2026-10-31 | 4,224 | SUCCESS; imported |
| NVDA | 2026-11 | `research-1795685200003` | 2026-11-01 to 2026-11-25 | 3,456 | SUCCESS; imported |
| INTC | 2026-09 | `research-1795685200004` | 2026-09-01 to 2026-09-30 | 4,032 | SUCCESS; imported |
| INTC | 2026-10 | `research-1795685200005` | 2026-10-01 to 2026-10-31 | 4,224 | SUCCESS; imported |
| INTC | 2026-11 | `research-1795685200006` | 2026-11-01 to 2026-11-25 | 3,456 | SUCCESS; imported |
| TSLA | 2026-09 | `research-1795685200007` | 2026-09-01 to 2026-09-30 | 4,032 | SUCCESS; imported |
| TSLA | 2026-10 | `research-1795685200008` | 2026-10-01 to 2026-10-31 | 4,224 | SUCCESS; imported |
| TSLA | 2026-11 | `research-1795685200009` | 2026-11-01 to 2026-11-25 | 3,456 | SUCCESS; imported |
| PLTR | 2026-09 | `research-1795685200010` | 2026-09-01 to 2026-09-30 | 4,032 | SUCCESS; imported |
| PLTR | 2026-10 | `research-1795685200011` | 2026-10-01 to 2026-10-31 | 4,224 | SUCCESS; imported |
| PLTR | 2026-11 | `research-1795685200012` | 2026-11-01 to 2026-11-25 | 3,456 | SUCCESS; imported |
| AMD | 2026-09 | `research-1795685200013` | 2026-09-01 to 2026-09-30 | 4,032 | SUCCESS; imported |
| AMD | 2026-10 | `research-1795685200014` | 2026-10-01 to 2026-10-31 | 4,224 | SUCCESS; imported |
| AMD | 2026-11 | `research-1795685200015` | 2026-11-01 to 2026-11-25 | 3,456 | SUCCESS; imported |
| AAPL | 2026-09 | `research-1795685200016` | 2026-09-01 to 2026-09-30 | 4,032 | SUCCESS; imported |
| AAPL | 2026-10 | `research-1795685200017` | 2026-10-01 to 2026-10-31 | 4,224 | SUCCESS; imported |
| AAPL | 2026-11 | `research-1795685200018` | 2026-11-01 to 2026-11-25 | 3,456 | SUCCESS; imported |

Bridge request: `RudraScanner/ResearchBridge/requests/<id>.json`. Job result: `RudraScanner/ResearchBridge/results/<id>.json`. Source CSV and manifest: `three_candle/data/ibkr_bridge/<id>/`.

**Backtest compatibility:** existing `original_three_candle.py` expects a legacy CSV column `Datetime` or `datetime_source` and filenames ending `_5m.csv`; these new IBKR exports instead have `Datetime_UTC` and are named `_5min_UTC.csv`. Update the loader/adapter explicitly (without changing frozen strategy logic) before applying its CLI to these datasets. Download completion is not a strategy backtest and no trades were placed.
