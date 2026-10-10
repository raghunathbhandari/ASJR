# SSH manual RudraScanner request — same Chakra IBKR connection

**Implemented in GitHub Saturday 10 October 2026. Pending VPS acceptance.**
This is a real `RudraScanner/scan_now.py` command.
The original user command previously returned `[Errno 2] No such file`;
that was correct because the proposed CLI did not exist then.

## How it works

**IMPORTANT: this is NOT a standalone immediate broker scan.**
No separate IB Gateway, EClient connection, client ID, new
scheduler or bot process is created. The command **queues a request
for the NEXT existing 5-minute Chakra run**, then waits to read its
result by default. Chakra is already performing one full discovery
and WAP/VWAP/EMA9/research pass every five minutes on Mondays.
An SSH request **coalesces with that exact pass** rather than
generating duplicate scanner/broker requests or delaying original
Wicks and locked Rudra-Reversal.

New components:
- `RudraScanner/scan_now.py`: runnable SSH command.
- `RudraScanner/manual_request.py`: atomic, locked,
  single-pending-request file handshake.
- `ASJR_Analyst/Tests/test_asjr_pipeline.py`
  version **2026.10.10.13**: detects pending request just BEFORE
  the existing scanner stage and marks it completed only AFTER
  the same cycle attempts its discovery + 5M report + 1H cache.
- `ASJR_Analyst/rudra_scanner_manual_request.json`:
  local runtime request status, **excluded from Git** by
  `.gitignore`. The scanner research/report itself remains in
  the shared day's DataLake and goes through the existing Git
  submission if that cycle succeeds.
- `RudraScanner/tests/test_manual_ssh.py`: 10 new
  offline safety tests. Previously verified on VPS: **83/83**
  BEFORE this change; expected expanded count **93**,
  **not yet verified**. Do not report success before running tests.

## Safe deployment on VPS

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/scan_now.py --help
```

**Expected 93 tests, 0 failures** is a target, not a
confirmed VPS result. Confirm test output and manually
reload the existing Chakra process with the user's usual
Discord bot controls before expecting it to service
SSH requests. **Do not start another Gateway.**

### On Monday 12 October during an active US session

```bash
cd /root/trading/ASJR

# Ask for next 5-minute Chakra scan; wait for saved result.
# Does not open an IBKR connection itself.
/root/trading/venv_new/bin/python RudraScanner/scan_now.py

# Fast / non-blocking alternative: enqueue and exit.
/root/trading/venv_new/bin/python RudraScanner/scan_now.py --no-wait

# Check the pending/completed request without creating a new one.
/root/trading/venv_new/bin/python RudraScanner/scan_now.py --status

# Read last saved scanner report without requesting any scan.
/root/trading/venv_new/bin/python RudraScanner/scan_now.py --saved --date 2026-10-12
```

**Output semantics:**
- `QUEUED`: SSH request saved but Chakra has not yet
  completed a subsequent real scanner cycle. If the
  existing bot is stopped or running the older imported
  Python code, it remains queued and the wait will time out.
- `COMPLETE`: the current Chakra cycle wrote a new
  scanner 5M report; CLI prints its text plus discovery
  code/1H statuses. This does NOT prove a profitable signal.
- `DATA_NOT_READY`: cycle ran but scanner data/report
  did not pass the completion checks; inspect existing
  Chakra logs plus `live_status.py`.
- `MARKET SESSION CLOSED` on Saturday, e.g. 10 October:
  **refuses to enqueue any weekend live scan**. Use
  `--saved` for older data. Explicit `--date` must
  equal the currently scheduled ET session date.
- `TIMEOUT`: Chakra has not completed it within
  the CLI's wait budget; request stays queued.
  `--status` can inspect without re-running IBKR.

**Existing scanner Discord flags still OFF:**
`alerts_enabled=false`, `thresholds_approved=false`.
The request does **not** bypass trading/session/risk
gates, does not send Discord, does not place orders and
does not replace Wicks, locked Reversal or AI research.
Normal 5M Chakra still runs even if no request exists.

## Unverified yet

No VPS logs have proven the new CLI works with the
long-lived process after version 2026.10.10.13 reload.
No result is expected on Saturday or before the first
live Monday Chakra cycle. The user's existing IBKR
connection/scanner/OHLC are confirmed healthy for
OTHER tasks; this bridge uses the same app and
needs separate acceptance of four new scanner codes.
There is no independent sub-five-minute immediate
request listener in the external VPS launcher.
