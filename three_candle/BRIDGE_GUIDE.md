# Three-Candle VPS Bridge Guide

Updated: 2026-11-01 (UK time)
Repository: `raghunathbhandari/ASJR`
Bridge worker: `RudraScanner/research_bridge_worker.py`
Requests: `RudraScanner/ResearchBridge/requests/research-<13 digits>.json`
Results: `RudraScanner/ResearchBridge/results/<same ID>.json`

## Read this before using the bridge

The VPS Research Bridge is an asynchronous **GitHub → VPS → GitHub** job queue, not SSH. When the `asjr-research-bridge.service` worker is running with deployed code, an AI session can create a validated JSON request on GitHub `main`, then poll the matching result JSON until complete. **The user does not need to SSH for each supported request.**

The worker runs from `/root/trading/ASJR` on the VPS and normally polls at roughly 60-second intervals, one job at a time. The bridge must already have the requested operation installed and allowlisted. A request commit alone is **not** proof of execution.

**Do not overwrite or re-download verified September/October NQ and GC history.** Existing market-data files are read-only unless the user explicitly authorizes replacement. The old `three_candle_nq_october_2026` operation was removed from the allowlist; its legacy downloader is disabled. Never re-enable it merely to test connectivity.

## 1. Verified channels and setup

| Channel | Status (2026-11-01) | Test evidence |
|---|---|---|
| Yahoo Finance through VPS | **Verified** | AMD 5m probe: 609 bars, `research-1793562084207`; no dataset files saved |
| IBKR Gateway through VPS | **Verified** | AMD single 5m candle: `research-1793562594927`; no dataset files saved |
| Dynamic IBKR date range | **Code committed, live test pending** | Worker and downloader introduced in commit `296edd690` |
| Generic dynamic Yahoo date range | **Not implemented** | Existing AMD Yahoo operation is a read-only fixed probe, not a parameterized exporter |

IBKR Gateway connectivity is **127.0.0.1:4002** on VPS, confirmed with `ss -lntp`. Port `1045` refused connections and must not be used. IBKR uses `ib_insync` from the VPS Python environment. All bridge test and download actions are **historical data only; no orders**.

## 2. Submit a dynamic IBKR range request (preferred)

Only after the VPS has pulled commit `296edd690` or later **and restarted the bridge service**, create this exact JSON under `RudraScanner/ResearchBridge/requests/research-<13 digits>.json` on GitHub `main`:

```json
{
  "schema_version": 1,
  "id": "research-1793563000000",
  "operation": "ibkr_range_download",
  "batch": null,
  "ticker": "MSFT",
  "start_date": "2026-10-01",
  "end_date": "2026-10-30",
  "timeframe": "5min"
}
```

The sample ID is illustrative: **generate a fresh unique 13-digit ID every time**, and keep the filename and JSON `id` identical. A reused request ID will be rejected or collide with historical results.

Parameters:

- `ticker`: uppercase US stock symbol, e.g. `MSFT`, `AMD`, `INTC`, `NVDA`; Stock/SMART/USD only, not futures, options or Forex.
- `start_date` and `end_date`: ISO `YYYY-MM-DD`, inclusive, no future end date.
- `timeframe`: one of `1min`, `5min`, `15min`, `30min`, `1h`, `1d`.
- Range: 1–31 calendar days inclusive; for `1min`, maximum 7 calendar days. Split larger intervals into multiple unique requests and audit the joins.
- The downloader requests IBKR `TRADES` with `useRTH=False`, including available extended-hours stock bars. It requests each weekday separately. Session coverage is **not guaranteed**; daily API errors are reported.
- The Python code writes UTC timestamps, OHLCV and a manifest into a **new directory** only.

Example output layout for a successful request:

```text
three_candle/data/ibkr_bridge/research-<13 digits>/
  MSFT_2026-10-01_2026-10-30_5min_UTC.csv
  manifest.json
```

It uses a temporary Git clone for publication, never stages or rebases the live production checkout, and refuses to overwrite an existing request directory. The CSV and manifest are committed to GitHub on success. `verified_complete: false` means downloaded rows have **not** passed a full exchange-session coverage audit.

## 3. How an AI session executes and checks a job

1. Read this guide and `GIT_SAFETY_HANDOFF.md` on current GitHub `main`.
2. Confirm the operation is deployed and the bridge service is running. A previously successful test does not prove present availability.
3. Create a **new**, valid request file via the GitHub connector. Do not edit an old request or reuse an ID.
4. Wait for the bridge poll (normally around 60 seconds). Fetch `RudraScanner/ResearchBridge/results/<job-id>.json`. A 404 means **pending**, not success.
5. Require `status: SUCCESS`, `exit_code: 0`, and parse `stdout_tail` for the downloader's `status`, `rows`, `file`, and `errors`.
6. Fetch the resulting `manifest.json` and CSV path from GitHub; inspect first/last timestamps, row count, missing periods, duplicated timestamps and zero-volume bars before using for a backtest.
7. Report precise source (`IBKR` or `Yahoo`), instrument, timeframe, sessions, UTC/UK time conversion, requested versus actual date coverage, any partial gaps, and repository path.
8. If the worker fails, report the actual error and keep source data unchanged; do not modify existing historical files to make the test pass.

**Never infer success from the fact that GitHub accepted a request.** If the result is not returned, check worker status or request the user to run read-only diagnostics; do not queue multiple duplicate downloads blindly.

## 4. Existing safe single-candle IBKR and Yahoo probes

For a quick connection-only check, existing allowlisted requests use the original 4-field schema:

```json
{"schema_version":1,"id":"research-<fresh13digits>","operation":"three_candle_ibkr_one_candle","batch":null}
```

This operation uses `three_candle/probe_ibkr_one_candle.py`. It is currently configured for an MSFT 5m historical candle on 2026-10-30, and **does not create CSVs**.

```json
{"schema_version":1,"id":"research-<fresh13digits>","operation":"three_candle_amd_probe","batch":null}
```

This operation uses `three_candle/probe_amd_direct_download.py`, requests approximately 5 days of recent AMD Yahoo 5m data, returns a row-count summary and **saves no CSVs**.

The static probes are for connectivity only. To vary date/ticker/timeframe, use the dynamic IBKR operation (once deployed); a generic dynamic Yahoo exporter is not yet available.

## 5. One-time VPS deployment vs routine work

Only when Python bridge/collector code changes is an operator deployment needed:

```bash
cd /root/trading/ASJR
git fetch origin
git merge --ff-only origin/main
python3 -m py_compile RudraScanner/research_bridge_worker.py three_candle/ibkr_bridge_range_download.py
sudo systemctl restart asjr-research-bridge.service
sudo systemctl is-active asjr-research-bridge.service
```

Expected final status: `active`. If Git refuses a merge due to local changes, **stop and inspect**; do not force, reset, clean, or delete the bot's runtime files. The older `git pull --ff-only origin main` once reported `Cannot fast-forward to multiple branches`; `git fetch origin` + `git merge --ff-only origin/main` worked without rewriting history.

For normal supported data requests after deployment, **no SSH, no editor, no bot restart**: submit job JSON and verify the result through GitHub.

If the bridge seems stuck, user-side read-only diagnostics:

```bash
sudo systemctl status asjr-research-bridge.service --no-pager
sudo journalctl -u asjr-research-bridge.service -n 60 --no-pager
ss -lntp | grep ':4002'
```

## 6. Preservation and Git safety

- **Do not overwrite verified NQZ2026/GCZ2026 September–October IBKR CSVs**, coverage files or any existing market-data CSV.
- New data goes to unique `three_candle/data/ibkr_bridge/research-<job-id>/` paths. Review output rather than replacing a previous file.
- Do not stage unrelated runtime logs, live state, locks or CSVs. Do not force-push main.
- Separate source quality clearly: Yahoo public intraday data and IBKR historical bars can differ in coverage, exchange, session and timestamps.
- UK time must be displayed to the user. CSV timestamps use explicit UTC, and comparisons must account for BST/GMT transitions.
- Single-candle and AMD Yahoo bridge results are proven. **The date-range pipeline must still be validated by an actual end-to-end request** before claiming it is production reliable.

## 7. Handoff status

Last verified:

- Yahoo read-only AMD probe: SUCCESS, 609 rows, zero saved files.
- IBKR read-only AMD probe: SUCCESS on port 4002; 2026-10-30 18:55 UTC candle OHLC `494.42/496.49/494.13/495.45`, volume `228606`, zero saved files.
- NQ overwriting operation disabled.
- Generic IBKR range code committed as `296edd690`; **VPS deployment confirmation and live test still outstanding at document creation**.

For future sessions: protect existing historical data first; use approved bridge operations, fresh request IDs, source-specific manifests and evidence-backed result verification.
