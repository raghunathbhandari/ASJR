# Rudra Admin Bridge v1 — 20 October 2026

## Purpose and limits
AI can create **strictly approved** maintenance requests through GitHub, and an installed VPS worker polls them every 60s. It returns JSON outcomes through an isolated GitHub branch. **This is NOT a root shell, Discord command runner, or guaranteed automatic repair.** The dedicated branch `rudra-admin-results` holds both requests and results, to avoid changing GitHub `main` every minute or triggering Chakra's non-fast-forward error.

Allowed operations:
- `health`: VPS worker and Python status
- `diagnose`: Git branch, tracked status, local/remote divergence, Chakra tmux state
- `maintenance`: invokes existing fixed `Rudra-DDB/asjr_maintenance.py`. When Chakra is RUNNING, it refuses merges. When STOPPED, it may preserve tracked DataLake changes, safely merge, push and report. It never restarts Chakra, force-pushes, resets, or deletes files.
- `cleanup_audit`: **DRY RUN** only, lists old `YYYY-MM-DD` DataLake folders under /root/trading/ASJR/ASJR_Analyst/DataLake. It does not alter cron, remove data or delete Git history. Production cleanup fix still requires identifying the actual cron/systemd scheduler on VPS.

## Safe installation — one time, after review
1. This code is on GitHub branch `rudra-admin-bridge-v1-20261020`, intentionally not on `main`. Review PR and merge only when Git history is synchronized with VPS. A direct GitHub `main` change while Chakra publishes can cause non-fast-forward errors.
2. On VPS, safely synchronize code (preserve DataLake changes and diverged local commits, use existing --maintenance if necessary), then verify `Rudra-DDB/AdminBridge/admin_bridge_worker.py` exists.
3. As VPS administrator run:

```bash
cd /root/trading/ASJR
python3 -m py_compile Rudra-DDB/AdminBridge/admin_bridge_worker.py Rudra-DDB/AdminBridge/install_admin_bridge.py
python3 Rudra-DDB/AdminBridge/install_admin_bridge.py
systemctl status asjr-admin-bridge.service --no-pager
```

Installer copies a **fixed** source-controlled systemd unit to /etc/systemd/system, daemon-reloads, enables/starts the worker. It does not stop or restart trading_bot.

## First health test
Prequeued job: `admin-2026102015460` on branch `rudra-admin-results`.

Read result after installation at:
`https://github.com/raghunathbhandari/ASJR/blob/rudra-admin-results/Rudra-DDB/AdminBridge/results/admin-2026102015460.json`

**PENDING** until that file appears with `"status": "SUCCESS"`. Do not assert live access before result is present.

## Safety and deployment caveats
- Worker uses fixed subprocess argv only; request JSON cannot supply shell parameters.
- Worker requires GitHub read/write credentials, access to DataLake/Git repo and the existing Python interpreter.
- The provided systemd service runs under the legacy account because the existing checkout resides under `/root`. This is **compatibility, not least privilege**. For hardened production deployment, relocate the bridge checkout to a dedicated account with bounded Git and read-only trading-data access. Review privileges before installing.
- Admin requests are created on branch `rudra-admin-results` and same branch receives responses; avoid merging this branch into `main`.
- The script takes a nonblocking file lock and handles one job per tick. A failed result publication can lead to retry of the same job; only safe/idempotent approved operations are permitted. More robust nonce/receipt handling is required for stronger exactly-once guarantees.
- This does not itself solve the dual-writer Git problem or repair the active cleanup scheduler. Those need a separately reviewed publisher/cleanup design.
- Never expose tokens, VPS passwords, or SSH private keys in GitHub.


## Verification matrix — 20 October 2026

Legend: **LIVE PASS** = result JSON from VPS confirms; **CODE ONLY** = code exists but not verified live; **NOT SUPPORTED** = current allowlist lacks capability. Do not conflate import scripts existing with completed imports.

| Capability | Evidence | Status |
|---|---|---|
| Admin service installation and health | `rudra-admin-results:results/admin-2026102015460.json`: SUCCESS, Python 3.10.15 | **LIVE PASS** |
| Git diagnosis | `results/admin-2026102017020.json`: SUCCESS, branch main, 44/1 divergence, Chakra stopped | **LIVE PASS** |
| DataLake retention audit | `results/admin-2026102017021.json`: SUCCESS, dry-run, two candidate dates | **LIVE PASS** |
| Fresh health and Git diagnosis | requests `admin-2026102016120`, `admin-2026102016121` | **QUEUED; awaiting results** |
| Fixed-path data inventory | new `data_inventory` branch code; requires VPS worker deployment/restart | **CODE ONLY** |
| Automatic safe Git maintenance | existing `maintenance` operation on installed worker | **NOT LIVE-TESTED** |
| Research Bridge Yahoo batch importer | `research_bridge_worker.py` allowlist `research_46_batch`; older ResearchBridge/README records successful batch 2 | **PREVIOUSLY REPORTED; not newly tested** |
| Research Bridge NQ imports | allowlisted `gann_nq_20261016` and `gann_nq_october_2026` | **CODE ONLY; success not established** |
| Arbitrary Yahoo ticker/date historical import | no parameterized allowlisted operation | **NOT SUPPORTED** |
| IBKR OHLCV import through either bridge | none in either bridge operation allowlist | **NOT SUPPORTED** |
| Arbitrary DataLake contents reading through Admin Bridge | no generic file read by design | **NOT SUPPORTED** |
| File deletion, cron edits, service restart | no operations; remains intentionally disallowed | **NOT SUPPORTED** |

### Deployment for new data_inventory (do not change GitHub main to deploy)

The initial Admin Bridge is already active. New branch code does not reach the running VPS process automatically. Administrator may update only the worker file from reviewed branch without merging main, then restart **only** the Admin Bridge service:

```bash
cd /root/trading/ASJR
git fetch origin rudra-admin-bridge-v1-20261020
git restore --source=FETCH_HEAD --worktree -- Rudra-DDB/AdminBridge/admin_bridge_worker.py
/root/trading/venv_new/bin/python -m py_compile Rudra-DDB/AdminBridge/admin_bridge_worker.py
systemctl restart asjr-admin-bridge.service
systemctl is-active asjr-admin-bridge.service
```

WARNING: `git restore` overwrites the specified **admin bridge worker file**, not DataLake, so first confirm no uncommitted manual edits to that file on the VPS. Do not run checkout/reset on main or restart Chakra. If Git root diverges, `git fetch` alone and targeted restore do not merge branches.

After deployment, submit JSON matching schema and ID format to `rudra-admin-results`:

```json
{"schema_version":1,"id":"admin-<13-digit-unique-id>","operation":"data_inventory"}
```

Look for corresponding results JSON on same branch. Only then mark inventory **LIVE PASS**.

### Future data imports for backtesting

Preserve the narrower, existing research import operations until tested. Add approved **read-only data manifests** and **fixed backtest data import actions** only with limits on ticker/date/timeframe, requests and maximum output sizes. Do not let AI submit shell strings, arbitrary file paths, Python code, IBKR credentials or unrestricted imports. Prefer an isolated Yahoo importer; IBKR imports should use the existing Chakra broker connection or an explicitly coordinated broker access window.
