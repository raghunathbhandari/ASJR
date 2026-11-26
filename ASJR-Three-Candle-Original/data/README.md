# ASJR Original Three-Candle — IBKR 5-minute stock market data

Requested on 26 November 2026 for six highly traded US stocks, September, October and November 2026 (November through 25 November, last completed date before request). **This is a request manifest, not proof downloads succeeded.**

Data source: IBKR Gateway via existing VPS worker `ibkr_range_download`, Stock/SMART/USD, TRADES, 5-minute, extended-session (`useRTH=False`). Original strategy tests resample the US regular session to 15-minute C1/C2/C3 candles. No automatic strategy run is implied.

The deployed downloader writes successful exports to **unique** `three_candle/data/ibkr_bridge/<job-id>/` GitHub directories. Existing files remain unchanged. Once jobs complete and the CSV and manifest are verified, source files may be linked or imported here without re-downloading.

| Ticker | Month | Requested calendar dates | VPS bridge job | Status as of request |
|---|---|---|---|---|
| NVDA | September 2026 | 2026-09-01 — 2026-09-30 | `research-1795685200001` | Pending verification |
| NVDA | October 2026 | 2026-10-01 — 2026-10-31 | `research-1795685200002` | Pending verification |
| NVDA | November 2026 | 2026-11-01 — 2026-11-25 | `research-1795685200003` | Pending verification |
| INTC | September 2026 | 2026-09-01 — 2026-09-30 | `research-1795685200004` | Pending verification |
| INTC | October 2026 | 2026-10-01 — 2026-10-31 | `research-1795685200005` | Pending verification |
| INTC | November 2026 | 2026-11-01 — 2026-11-25 | `research-1795685200006` | Pending verification |
| TSLA | September 2026 | 2026-09-01 — 2026-09-30 | `research-1795685200007` | Pending verification |
| TSLA | October 2026 | 2026-10-01 — 2026-10-31 | `research-1795685200008` | Pending verification |
| TSLA | November 2026 | 2026-11-01 — 2026-11-25 | `research-1795685200009` | Pending verification |
| PLTR | September 2026 | 2026-09-01 — 2026-09-30 | `research-1795685200010` | Pending verification |
| PLTR | October 2026 | 2026-10-01 — 2026-10-31 | `research-1795685200011` | Pending verification |
| PLTR | November 2026 | 2026-11-01 — 2026-11-25 | `research-1795685200012` | Pending verification |
| AMD | September 2026 | 2026-09-01 — 2026-09-30 | `research-1795685200013` | Pending verification |
| AMD | October 2026 | 2026-10-01 — 2026-10-31 | `research-1795685200014` | Pending verification |
| AMD | November 2026 | 2026-11-01 — 2026-11-25 | `research-1795685200015` | Pending verification |
| AAPL | September 2026 | 2026-09-01 — 2026-09-30 | `research-1795685200016` | Pending verification |
| AAPL | October 2026 | 2026-10-01 — 2026-10-31 | `research-1795685200017` | Pending verification |
| AAPL | November 2026 | 2026-11-01 — 2026-11-25 | `research-1795685200018` | Pending verification |

For each job:
- Request: `RudraScanner/ResearchBridge/requests/<job-id>.json`
- Result: `RudraScanner/ResearchBridge/results/<job-id>.json`; require `status=SUCCESS`, `exit_code=0`
- Manifest and CSV: `three_candle/data/ibkr_bridge/<job-id>/`; verify actual count, dates, gaps, errors and `verified_complete` flag
- The worker processes at most one job per poll. Jobs marked pending in this static manifest might have since finished; check result files.
- November 26 is incomplete at time of request; it is excluded. Next completed November dates can be requested separately.
- Do not commit live broker credentials or duplicate raw data when an immutable Git blob already exists.
