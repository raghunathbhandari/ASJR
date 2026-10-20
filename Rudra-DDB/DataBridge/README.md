> **Rudra-Coder handoff (verified 20 Oct 2026):** [Read RUDRA_CODER_HANDOFF.md](RUDRA_CODER_HANDOFF.md) for successful 190-candle MSFT CSV export, confirmed live status, operating lessons, research possibilities and next-session steps.

# Rudra Data Bridge — isolated Yahoo data import and Git export

Created 20 October 2026. This is **separate** from `Rudra-DDB/AdminBridge`; do not add data-import operations to the Admin Bridge again.

## Separation

| Component | GitHub branch | VPS service | Purpose |
|---|---|---|---|
| Chakra/live DataLake | `main` | `trading_bot` | IBKR/alerts/live processing |
| Admin Bridge | `rudra-admin-results` | `asjr-admin-bridge.service` | Diagnostics and guarded Git maintenance |
| **Data Bridge** | **`rudra-data-results`** | **`asjr-data-bridge.service`** | Yahoo OHLCV import + separate Git CSV export |

**No CSVs or routine result commits go to `main`.** Worker copies downloaded CSVs to a scratch Git checkout, fetches `rudra-data-results`, commits files and result JSON together, and retries optimistic push rejects. No live worktree staging/merge/rebase/reset. The request branch is used for both requests and results, but outputs are separate from the Admin Bridge and Chakra.

## Allowed actions

- `health` — fixed job to validate the data bridge.
- `yahoo_import` — up to five validated symbols and bounded Yahoo date range/timeframe.
- **No arbitrary `runpy`, OS shell, filesystem paths, broker access, trade orders, DataLake mutation, or arbitrary Git commands.**

Example request on **`rudra-data-results`** in `Rudra-DDB/DataBridge/requests/data-<13digits>.json`:

```json
{
  "schema_version": 1,
  "id": "data-2026102016401",
  "operation": "yahoo_import",
  "symbols": ["MSFT", "NQ=F"],
  "interval": "5m",
  "start": "2026-09-21",
  "end": "2026-09-22"
}
```

`start` is inclusive, `end` exclusive. Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo. Max windows: 1m=7 days, most other intraday=60 days, 1h/60m=730 days, daily+ max 3650 days. Actual Yahoo limits may be stricter. Ticker syntax restricted; no paths. Per symbol: max 25,000 bars / 3 MB CSV. The request is not an authorization to execute any arbitrary code.

## Exports

`Rudra-DDB/DataBridge/exports/<job-id>/<symbol>.csv` and `Rudra-DDB/DataBridge/results/<job-id>.json` on the **isolated `rudra-data-results` branch**. The result includes row counts, first/last timestamp, output size and GitHub paths. A result with `NO_DATA` or `PARTIAL_OR_FAILED` must not be counted as a successful import.

## One-time installation (admin privilege and GitHub access required)

Development code stays on `rudra-data-bridge-v1-20261020` — **not on `main`**, to avoid Chakra non-fast-forward errors.

```bash
cd /root/trading/ASJR
git fetch origin rudra-data-bridge-v1-20261020
git status --short -- Rudra-DDB/DataBridge/
# Confirm DataBridge files have no manual modifications before targeted restore.
git restore --source=FETCH_HEAD --worktree -- Rudra-DDB/DataBridge/
/root/trading/venv_new/bin/python -m py_compile Rudra-DDB/DataBridge/*.py
/root/trading/venv_new/bin/python Rudra-DDB/DataBridge/test_data_bridge.py
python3 Rudra-DDB/DataBridge/install_data_bridge.py
systemctl is-active asjr-data-bridge.service
```

This installer enables **only** the new Data Bridge. It does not restart Admin Bridge or trading_bot. Review and restrict permissions before production: legacy /root layout currently implies running service with root access. Move to a dedicated non-root checkout/account with only GitHub branch read/write and isolated export rights in a later hardening phase.

## Verification requirements

1. All 10 offline tests pass.
2. systemd service is active.
3. A fresh `health` job on `rudra-data-results` produces `status=SUCCESS`.
4. A fresh one-day `MSFT 5m` import returns `status=SUCCESS`, candles >0 and export CSV retrievable from **rudra-data-results**.
5. Confirm `main` wasn't changed by the Data Bridge. Keep results labelled **PENDING** until actually received and inspected.

## Next-session handoff

Use GitHub request files to run approved imports and read CSVs. GitHub commits to `main` can still cause Chakra conflicts through other workflows, but **this bridge does not write main**. Cleanup scheduler repair and isolated Chakra DataLake publisher are separate tasks. Do not claim they are fixed by this Data Bridge.

