## VERIFIED LIVE and RESEARCH EXPORT UPDATE — October 16, 2026

- GitHub bridge health result `results/research-2026101608501.json` is `SUCCESS` (Python 3.10.15, VPS execution confirmed).
- Batch 2 collection result `results/research-2026101610002.json` is `SUCCESS` (10/10 daily + 10/10 5-minute Yahoo data).
- Subsequent requests for batches 3, 4, 5, finalize, and `research_46_publish` are queued.
- The first worker version published **only status JSON**. New `research_46_publish` operation writes the dated OHLCV compressed files, `research_metrics_46.csv` and `RESEARCH_REPORT.md` to GitHub from an isolated temporary clone. It does not stage live DataLake or Chakra code.
- **To deploy the new operation once** via the existing working Discord script allowlist:

```text
!gitpull
!runpy RudraScanner/scan_now\.py --bridge-refresh
```

- The refresh restarts **only** `asjr-research-bridge.service`. It does not restart `trading_bot` or Discord.
- Confirm successful `research_46_publish` result in `results/research-20261016101902.json` and verify `ResearchData/EMA50_2026-10-15/research_metrics_46.csv` is present before claiming complete data availability.
- Data history and calculations require a further scientific audit: Yahoo 5-minute bars might cover fewer than 20 same-time-of-day sessions for some symbols; null/unknown metrics must not be scored as success. Catalyst and historical capitalization are not part of OHLCV exports.

---

## ACTIVATE VIA EXISTING WORKING DISCORD RUNPY (2026-10-16)

The external Discord `!runSCommand` handler was not reloaded after
`bridge-start` was added, returning UNKNOWN ADMIN OPERATION. Do **not**
restart Chakra or patch the external Discord process.

The already-working allowlisted `scan_now.py` now exposes two fixed
one-shot operations requiring no Discord handler reload:

```text
!gitpull
!runpy RudraScanner/scan_now\.py --bridge-start
!runpy RudraScanner/scan_now\.py --bridge-check
```

`--bridge-start` invokes the fixed no-arguments service installer.
It requires the existing Discord runner process to have sufficient OS
permissions for /etc/systemd/system/; if denied, do not relax Discord
permissions or make the entire bot root. A safer one-time external SSH
admin installation is required instead.

`--bridge-check` runs one worker polling iteration. **Do not run it
while the background systemd worker is active**, since v1 does not have
a durable multi-process lock.

V1 still lacks verified data CSV publishing; first validate the queued
health-check JSON. This is a prototype; use a non-root dedicated account
and isolated checkout for future hardened deployment.

---

## Verified deployment status — 2026-10-16 09:35 UK

**NOT OPERATIONAL YET.** Code and health-check request exist on GitHub,
but the result `results/research-2026101608501.json` is absent.
The user confirmed `!gitpull` succeeded and `!runSCommand bot`
reported tmux `trading_bot` running. However,
`!runSCommand bridge-start` returned
`DENIED | Unknown admin operation`: the already-running external
Discord command handler has not loaded the revised allowlist.
`!gitpull` alone does not reload a running Python module.

**Current limitation:** This chat can create job-request JSON in GitHub,
but cannot claim to execute VPS research until the worker is activated
and returns a successful health-check result. As implemented, v1 publishes
only job-status JSON, not research CSV or OHLCV data.

**External Discord handler:** ASJR GitHub contains
`ASJR_Analyst/Utils/discord_server_commands.py`, but the external bot
entry point and its service reload procedure are not established by the
handoff. `!mbdstop` / `!mbdstart` control `trading_bot`, **not**
a verified standalone Discord service restart. Never ask for a blind
Chakra or Discord restart. If administrator SSH is available, use the
read-only `--once` worker health test described below before enabling a
persistent service. Do not claim a direct connection until a GitHub result
is received. No secrets or Discord Admin ID should be posted in chat.

**Production safety requirements before enabling:** isolate the
worker from root privileges and the live trading worktree, restrict
GitHub request-writing privileges, guard against replay/concurrent workers,
and permit publication of approved research outputs only. The current
prototype assumes a writable root-based ASJR environment and is not
production-hardened.

---

# Rudra AI ↔ VPS Research Bridge (v1)

**Goal:** AI writes a fixed JSON job to GitHub main, the VPS polls it,
executes only approved research code, then pushes a JSON result to main.
No Discord command per job. This is **not SSH**. It is an asynchronous
GitHub-mediated job runner.

## Safety boundary
- Worker: RudraScanner/research_bridge_worker.py
- Jobs: RudraScanner/ResearchBridge/requests/research-XXXXXXXXXXXXX.json
- Results: RudraScanner/ResearchBridge/results/<job-id>.json
- Strict schema_version=1 and exact set of keys id, operation, batch.
- Allowed operations: health_check; research_46_batch (batch integer 1–5);
  research_46_finalize. All other operations rejected. No shell string eval.
- Research collector writes only RudraScanner/ResearchData/EMA50_2026-10-15
  to local disk. **It does NOT automatically push raw CSV/OHLCV files.**
  Only small status JSON records are pushed by v1. Data-export publishing
  will need a separate reviewed implementation.
- No Chakra hooks, IBKR sessions, Discord messages, or trade actions.
- Worker does not call git reset/stash/add/commit in the live ASJR checkout.
  It uses an isolated temporary Git clone to publish results.
- To avoid giving a bridge root access, run as a dedicated Unix account
  with read access to /root/trading/ASJR (note /root generally denies access).
  A separate non-root working clone with narrowly scoped Git credentials is
  recommended for production. The current script defaults to root-path
  /root/trading/ASJR, so deployment privileges must be considered.
- A malicious repository editor could still change executable Python and
  have worker run it. GitHub main WRITE access is therefore a trusted
  administrative boundary; use branch protection and restricted access.

## One-time setup (operator on VPS)
Requires Python 3.10+, yfinance, pandas and existing GitHub credentials.
The live bot is NOT restarted. First verify worker manually from SSH:
  cd /root/trading/ASJR
  git pull --ff-only origin main
  /root/trading/venv_new/bin/python RudraScanner/research_bridge_worker.py --once

If that succeeds, install the provided systemd **template** using your
existing administrator route only after reviewing it. Running as root is a
temporary compatibility choice; a dedicated service user is safer.
  cp RudraScanner/ResearchBridge/asjr-research-bridge.service /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable --now asjr-research-bridge.service
  systemctl status asjr-research-bridge.service --no-pager

## Health check
The AI creates a tracked GitHub request:
  {"schema_version":1,"id":"research-<13digits>",
   "operation":"health_check","batch":null}
Worker polls every 60 seconds; GitHub result shows SUCCESS/Python version.
If no worker is installed, request remains PENDING, not a successful test.

## Research operations
- research_46_batch (batch 1–5)
- research_46_finalize (requires completion of all five local batches)
Only use after the health check confirms worker execution.

## Cautions and limitations
- Job filenames are trusted only when strict schema and ID match.
- On any Git error worker reports a short generic status, not credentials.
- A result is considered completed only when pushed to GitHub.
- Research jobs may take minutes and Yahoo 5m availability varies.
- Worker retrieves its **requests** from origin/main and runs the
  **currently installed source**. Update installed code deliberately.
- The worker's Git remote needs push rights; the one-shot health check tests this.
- The current implementation lacks a durable multi-worker lock; install
  only **one** worker instance. For deployment use dedicated isolated account
  and ensure service is single-instance.
