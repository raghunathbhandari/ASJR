# Rudra-Coder — verified handoff (20 October 2026)

Rudra-Coder is the assistant role for development, approved Yahoo historical-data imports, verification and documentation.

## Verified production evidence

- Independent Data Bridge installed; systemd service `asjr-data-bridge.service` active.
- Offline request validation: **10 tests passed**.
- Data Bridge health request `data-2026102016410`: **SUCCESS**, 20 Oct 2026 16:47:44 UTC; Python 3.10.15.
- MSFT 5-minute candles for **21 September 2026**, request `data-2026102016411`: **SUCCESS**, 190 rows, 14,476-byte CSV, first UTC timestamp 08:00, last 23:55.
- Result JSON and CSV were fetched and inspected separately:
  - https://github.com/raghunathbhandari/ASJR/blob/rudra-data-results/Rudra-DDB/DataBridge/results/data-2026102016411.json
  - https://github.com/raghunathbhandari/ASJR/blob/rudra-data-results/Rudra-DDB/DataBridge/exports/data-2026102016411/MSFT.csv

## Architecture

| Component | Purpose | Routine Git branch |
|---|---|---|
| Chakra trading bot | IBKR, DataLake, live alerts | `main` |
| Admin Bridge | Guarded diagnostics and maintenance | `rudra-admin-results` |
| **Data Bridge** | Yahoo import, CSV export and result JSON | **`rudra-data-results`** |

Data Bridge is a separate 60-second VPS polling service, independent of Chakra and IBKR. ChatGPT submits requests using GitHub; it does **not** have an interactive VPS shell. The bridge publishes via a temporary Git clone, not the Chakra working tree. Development branch: `rudra-data-bridge-v1-20261020`; draft PR #3. Avoid merging into `main` until the Chakra publisher's unrelated non-fast-forward issue is resolved.

## Request protocol

New requests are GitHub JSON files on `rudra-data-results` at `Rudra-DDB/DataBridge/requests/<unique data-13digits>.json`.

Example:

```json
{"schema_version":1,"id":"data-2026102017001","operation":"yahoo_import","symbols":["MSFT","NQ=F"],"interval":"5m","start":"2026-09-21","end":"2026-09-22"}
```

Start date inclusive; end date exclusive. Up to five unique valid symbols. Supported intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo. Worker date limits include 7 days for 1m; 60 days for most other intraday; up to 730 days for hourly; and up to 3650 days for daily and longer. These are worker request limits, not Yahoo data guarantees.

Results: `Rudra-DDB/DataBridge/results/<job-id>.json`; exports: `Rudra-DDB/DataBridge/exports/<job-id>/<ticker>.csv` on `rudra-data-results`. Special ticker characters are normalized in CSV filenames.

**Verification rule:** request submitted is not import complete. Check result JSON, per-symbol status and positive row count, then fetch the actual CSV and inspect timestamps/columns. Explicitly report NO_DATA or partial results; do not invent candles while requests are pending.

## Lessons and safeguards

1. Separate research imports from Chakra's frequent `main` Git writes. The Data Bridge never pushes research CSVs to `main`.
2. Use Data Bridge for research, Admin Bridge for diagnostics. Do not mix their roles.
3. Validate the actual CSV and result, not just service status.
4. 20 September 2026 was Sunday and MSFT returned NO_DATA; 21 September yielded 190 five-minute rows.
5. CSV timestamps are UTC; Yahoo includes extended hours with `prepost=True`. Some volumes are zero. Filter market session and check candle quality before backtesting.
6. Today's incomplete trading session must not be treated as final.
7. Yahoo 5-minute history is usually limited to ~60 days; older intraday dates require another data source.
8. Import starts when the VPS next polls, not synchronously on ChatGPT request.
9. Only approved health/Yahoo import operations are allowed. No unrestricted runpy, arbitrary commands, IBKR sessions or trading orders.
10. Separate Data Bridge success does not repair the existing Chakra DataLake git divergence and cleanup-scheduler concerns.
11. Service currently uses legacy privileged VPS location; stronger least-privilege separation and restricted Git credentials should be planned.

## Rudra-Coder future possibilities (not implemented)

- Approved, bounded research/backtest jobs with separate result exports.
- RTH versus extended-hours filters, timezone normalization and candle-gap checks.
- Validated data manifests, hashes, reproducibility and source comparisons.
- Existing-export inventory and retrieval; date-range chunking.
- Monitoring for stalled jobs, failures and backlogs; safe data retention.
- Alternate licensed historical intraday provider or safely engineered IBKR adapter.
- Dedicated non-root account, branch-scoped Git access and resource quotas.

## Next-session checklist

Read this handoff and README; use GitHub request and results branches, inspect returned CSVs, and maintain separation from Chakra `main`. Do not claim an unverified import completed. Keep communication concise and use explicit links. Persona: **Rudra-Coder**.
