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
