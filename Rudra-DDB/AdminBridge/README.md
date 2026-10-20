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
