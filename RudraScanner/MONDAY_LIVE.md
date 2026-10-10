# RudraScanner Monday US Session — Live SHADOW Deployment

**Prepared Saturday 10 Oct 2026. Intended next US session Monday
12 Oct 2026. Timezone: Europe/London BST (UTC+1) for all bot alerts.**

## VERIFIED user VPS retest — Saturday 2026-10-10 13:30 UTC

User pulled GitHub main from `1ce9a402` to
`2d1ee811` and reran the complete Phase 3 suite:

```text
Ran 83 tests in 0.887s
OK
```

**83/83 tests passed, zero failures.** Both
`test_pipeline_bridge` approval-gate test fixtures
were corrected and are now independently confirmed
on the user's VPS. The production scanner alerts
remain DISABLED; their fail-closed behaviour
is intentional.

Read-only `RudraScanner/live_preflight.py`
also returned `ready_to_shadow=true`. This
means the **checked code and scheduled configuration**
are ready, NOT that a connected IBKR live scan
has run. Actual values:

| Read-only check | User's observed result |
|---|---|
| Scheduled mode | `shadow` for 2026-10-12 |
| Research mode | `true` |
| Scanner Discord | `alerts_enabled=false`, `thresholds_approved=false` |
| Fixed-list rows eligible | **18** / 19 configured; excluded `ONDS` |
| Fixed status | `PARTIAL` (intentional exclusion) |
| AI candidates valid at Monday RTH | **1**; 10 expired |
| AI source state | `PARTIAL` |
| Four IBKR scanner codes / legacy Wicks / Reversal hooks | Present (code checks only) |
| Broker requests / orders / Discord from preflight | **0 / 0 / 0** |

**Current outstanding activation checks:**
1. Confirm the actual VPS-running Chakra process
   imports the updated modules after the user-controlled
   restart (Git pull alone does not reload Python).
2. Confirm that the external EWrapper/trading launcher
   really allows historical WAP and four scanner
   callbacks using the same running IBKR app.
3. Monday after a 5M run, inspect real
   `raw/scanner_status.json`, selected CSV and
   `reports/scalp_radar.txt`, timestamps, actual
   WAP/VWAP, index/sector alignment and Wicks/Reversal
   delivery.
4. Refresh the AI source **from actual new research**;
   do not extend the previous ten expiry timestamps
   or falsely claim 30/30 ticker coverage.

**SSH quick inspection after a real market-session cycle:**

```bash
cd /root/trading/ASJR
/root/trading/venv_new/bin/python RudraScanner/live_status.py --date 2026-10-12
```

No scanner Discord signals or trading orders should be
sent during SHADOW. The file-based mode becomes relevant
when the running Chakra code is reloaded; an explicitly
set `RUDRA_SCANNER_MODE=off` environment variable
overrides it. The older 81/83 failure section below
is historical and now resolved.

---

## User VPS preflight 2026-10-10 13:24 — two test mock failures FIXED IN GIT

**Actual observed console, NOT a full pass:** User fast-forward pulled
`368cf6d3..1ce9a402` on main and ran complete Monday suite.
**83 tests ran in 0.972 seconds, 81 passed, 2 failed**.
The two failures were ONLY in
`RudraScanner/tests/test_pipeline_bridge.py`:

- `test_scanner_batch_after_internal_wicks_reversal_dispatch`:
  expected `"QUEUED RESEARCH"` but got empty string;
- `test_external_mark_sent_falls_through_to_scanner_ack`:
  expected one acknowledged event but got zero.

**Root cause:** Both synthetic tests mocked the queue response but
did NOT mock `asjr_alerts._scanner_queue_approved()`.
The production method CORRECTLY refuses to prepare/send/ACK a
scanner message when `alerts_enabled=false` and
`thresholds_approved=false`, as required for Monday SHADOW.
Changed ONLY those two test fixtures to explicitly simulate the
approved queue state. No production Discord safety flags were
changed. This Git fix has NOT YET BEEN VPS RETESTED;
**expected 83/83 after pull; do not claim until terminal proves it**.

**Preflight actually returned:**
`scheduled_mode=shadow`, `research_enabled=true`,
`live_scanner_alerts_enabled=false`,
`approved_thresholds=false`,
`same_chakra_pipeline_hook=true`,
`legacy_wicks_still_present=true`,
`locked_reversal_still_present=true`,
`discord_queue_bridge=true`, `ready_to_shadow=true`
(meaning CODE HOOKS configured, NOT real IBKR verified).
At the first check, `fixed_today=0`, `fixed_state=MISSING`,
`ai_valid_at_monday_open=1`,
`ai_expired_at_open=10`.

**Fixed-list blocker addressed in Git:** Created
`ASJR_Analyst/DataLake/2026-10-12/config/fixed_watchlist.csv`
as a **byte-for-byte copy** of Friday's canonical
`2026-10-09/config/fixed_watchlist.csv`.
This preserves all 19 manually configured rows, existing
`INTC`, and positions `AKAM` / `WTTR` without altering
the legacy Wicks membership. RudraScanner excludes
`ONDS` from its own capped selection. On pull,
`read_fixed_watchlist()` should find the Monday list;
the scanner ranks up to 10 fixed names, not all 19.
This change itself has NOT YET BEEN VPS RETESTED.

**AI still needs real refreshing:** Ten Saturday AI rows expire
Monday **2026-10-12 12:00 UTC / 13:00 BST**. The one
still eligible at Monday open is `INTC` as a
permanent unverified WATCH, and it is already in
the fixed selection; so there may be **zero unique
fresh AI bucket names** at open. Don't mislabel a
10+0+10 partial result as 30/30. Do not silently
extend expiry or invent Monday catalysts. No reliable
hourly AI-to-GitHub update task is configured.

### Safe retest now, without any IBKR or bot restart

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/live_preflight.py
```

Expected: `Ran 83 tests ... OK`; no failures;
`fixed_today` positive and `fixed_state` no longer
`MISSING`; `ai_valid_at_monday_open` still 1 until
valid future-dated sourced research is refreshed.
Do **not** restart Chakra until actual test output
has been reviewed, and never enable scanner
Discord or ACTIVE solely because the preflight
returns `ready_to_shadow=true`.

---

## What was applied to GitHub MAIN

The existing five-minute Chakra pipeline
`ASJR_Analyst/Tests/test_asjr_pipeline.py` (new version
`2026.10.10.12`) now reads
`ASJR_Analyst/config/rudra_scanner_runtime.json`.
It schedules **SHADOW** mode on or after Monday 12 Oct ET.

**The actual automatic method is the same existing Chakra call:**
`ibkr_trading_sudarsan_chakra(app)` ->
`run_asjr_manual_pipeline(app,...)`, with four-code
IBKR discovery and independent 5M/1H scanner sidecar
**after** original Wicks and locked 1H Reversal dispatch.
No new tmux process, scheduler, connection, or buy/sell order function.

- Four scanner codes: `TOP_PERC_GAIN`,
  `TOP_PERC_LOSE`, `HOT_BY_VOLUME`, `MOST_ACTIVE`.
  **No fixed 4% gain/loss rule** on the new scanner.
  Source provenance in same dated DataLake.
- Strict 10 fixed + up to 10 valid AI + up to 10 IBKR
  (30 unique US stock names max).
  No extra borrowing of source quotas.
  Source status `PARTIAL` or missing is reported;
  missing ETF/benchmark => WAIT.
- **Preserve** entire original legacy 5M Wicks import universe,
  its detector and message state; **preserve** locked
  Rudra-Reversal 1H universe, Yahoo NQ and Discord priority.
  Active scanner candidate stocks are a **separate sidecar**
  and DO NOT replace Wicks. One existing app, no order calls.
- Actual historical IBKR WAP capture is passively installed
  before legacy 5M import so scanner reuses collected WAP.
  Source-aligned extra 5M requests download only missing
  selected stocks + SPY + QQQ + evidenced sector ETFs.
  A symbol without enough completed historical candles,
  actual WAP or a same-time benchmark cannot produce a signal.
- The extra 1H selected-stock data collection uses the same
  app, is cached for 60 minutes per day/selection,
  and stored in `raw/intraday_1h.csv`. **SHADOW
  DOES NOT invoke the locked Reversal on those new names**
  or change its alert state. >150 bars for new symbol
  is diagnostic until later integration approval.
- Extra 5M indicators: continuous EMA9 through available
  premarket/overnight bars, IBKR-WAP VWAP reset at true
  09:30 ET, true 20-prior-full-RTH RVOL20 whenever
  sufficient prior coverage exists.
- Top-down live signal gate uses **as-of-completed 5M**
  SPY and QQQ versus previous regular-session close,
  then relative sector ETF with same 5M timestamp.
  NEVER uses a Yahoo end-of-day sector value as though
  it were available intraday. Unknown ETF => WAIT.
- Research pattern detectors: Hitchhiker, Back$ide,
  Rubberband, Second Chance, Fashionably Late for
  LONG and SHORT. Friday Oct 9 was retrospectively
  10 distinct research entries, 40% positive, with
  provisional 30-minute markouts before costs.
  These are **NOT validated production buy/sell signals**.
- Scanner Discord support is integrated into the
  existing caller's `prepare_alert()` /
  `mark_alert_sent()` / optional immediate `send_alerts()`.
  The scanner keeps an **independent pending + sent + batch**
  state. Wicks and Reversal always take message priority.
  Only enabled if BOTH flags are true (currently BOTH OFF).
  The external VPS utility code at
  `/root/trading/utils/trading_sudarsan_chakra.py`
  is NOT in this GitHub repo and could not be audited
  directly from the connector.
- Read from GitHub/VPS:
  `ASJR_Analyst/DataLake/YYYY-MM-DD/reports/scalp_radar.txt`,
  `reports/rudra_scanner_live_status.json`,
  `reports/rudra_scanner_research.txt`,
  `raw/scanner_status.json`,
  `processed/scalp_radar_candidates.csv`,
  `raw/intraday_1h.csv`.

## Current GitHub runtime switch

```json
{
  "schema_version": 1,
  "enabled_from_et": "2026-10-12",
  "mode": "shadow",
  "research": true,
  "alerts_enabled": false,
  "thresholds_approved": false,
  "preserve_legacy_wicks": true,
  "preserve_locked_reversal": true
}
```

**Git pull alone does not activate new Python imports inside a
long-running process.** The user must do their established
Discord-controlled bot restart after pulling the code.
If `RUDRA_SCANNER_MODE=off` is explicitly set in that
process's environment, it overrides the JSON schedule
and keeps it OFF (not a code failure).

## Weekend VPS tests — no IBKR requests or bot restart

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m compileall -q RudraScanner ASJR_Analyst/Tests/test_asjr_pipeline.py ASJR_Analyst/Utils/asjr_ibkr.py ASJR_Analyst/Utils/asjr_alerts.py
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/live_preflight.py
```

**Expected (NOT yet VPS verified): 81 total test methods, OK.**
There were 65/65 VPS-verified before these Monday integration
changes; 16 NEW source tests now need real VPS output.
If errors appear, STOP before restarting Chakra, send
the entire traceback, and fix Git code first.

Preflight checks the runtime schedule and both existing
alert hooks. It also warns if Monday's AI CSV is expired
or fixed_watchlist hasn't been bootstrapped for that day.
An empty Monday fixed list before day bootstrap is not proof
that old fixed stocks were deliberately removed.

## Monday 12 Oct staged acceptance

1. Read successful latest VPS **81-test output** and
   resolve all exceptions. Ensure `git status --short`
   contains no unintended unstaged bot files. Do not
   force-push, reset the repo or touch manual positions.
2. The AI research CSV used on Saturday expires
   **Monday 12 October 12:00 UTC (13:00 UK)**.
   There is **NO successfully configured hourly
   AI-to-GitHub automation**: the attempted new task was
   rejected because the user has reached the five-active-task
   limit. Without a refreshed verified AI CSV, AI candidates
   may legitimately fall below 10; **do not substitute
   Friday stale names or invent research**.
3. If the user chooses, use the existing **Discord bot
   controls** to restart the already configured trading
   process **once** after Git pull. This is required for
   new `test_asjr_pipeline.py` imports to take effect;
   do not start a second bot process. Verify
   `ASJR Analyst Version: 2026.10.10.12` in the log.
   The SHADOW switch is date-scoped; Friday/weekend
   historical job remains OFF.
4. On Monday 12 October US premarket, observe the
   next real Chakra 5M job. Inspect logged
   `RUDRA SCANNER | shadow`, the four exact scan-code
   statuses and the selected source counts; any
   `TIMEOUT`/`ERROR` must be documented, NOT called
   complete discovery.
5. Check that original Wicks/Reversal output and
   Git submission still occur. Verify original
   Wicks stock count unchanged, and new scanner
   candidates are separately limited <=30.
6. At 14:30 UK (09:30 ET), inspect the next first
   completed RTH bars; proper pattern evaluation
   starts after first 30 minutes, **15:00 UK**.
   Look for `WAP AVAILABLE`, ETF timestamp,
   `TOP DOWN LONG/SHORT/WAIT`, EMA9, VWAP, data
   freshness and true RVOL20 status. It is normal
   for RVOL20 to remain NOT READY until 20 complete
   prior RTH reference sessions accumulate.
7. Review CPU/time/broker request pacing. Initial
   extra stock+ETF historical requests plus 1H import
   can increase runtime; if a Chakra 5M cycle over-runs
   or IBKR permissions fail, **disable only scanner**
   via runtime JSON `mode=off` plus Git pull / bot
   reload. Never break existing wick alerts to keep
   Scanner online.
8. Scanner 5M live technical research is **ON**;
   Discord scanner pattern delivery is **OFF**
   until the user deliberately accepts unvalidated
   thresholds and BOTH JSON flags are enabled.
   No buy/sell orders are implemented.

## Read report on-demand without restarting bot

```bash
cd /root/trading/ASJR
cat ASJR_Analyst/DataLake/2026-10-12/reports/scalp_radar.txt
cat ASJR_Analyst/DataLake/2026-10-12/raw/scanner_status.json
```

The chatbot can analyse current GitHub-synced DataLake
output when requested; no permanent direct SSH access
to the running VPS from this chat is claimed.

## Emergency rollback / fail-safe

Set `mode` to `off` in
`ASJR_Analyst/config/rudra_scanner_runtime.json`
on GitHub/main or set `RUDRA_SCANNER_MODE=off` in the
bot's process environment, then perform user's normal
Git pull and controlled process reload/restart if needed.
SHADOW must not alter old Wicks/Reversal source tickers,
rules, state, NQ Yahoo or ACK files. Scanner results under
the common DataLake are not order instructions.

## Current limits and truthful acceptance

No actual **Monday** broker scanner callbacks, streaming
WAP freshness, negative-direction alerts, selected
AI research rollover, scanner Discord sends or 5M
timing benchmarks have been observed. The previous
Friday test verified historical 5M IBKR WAP retrieval,
not the newly wired live Chakra callback. The
external `/root/trading/utils/trading_sudarsan_chakra.py`
is not in GitHub; we cannot claim it was reviewed
without actual VPS file/console output.
The intended scheduled SHADOW code has been COMMITTED,
but is **not yet live-verified/deployed in the VPS process**.

**Current status: GitHub implementation ready for Monday
SHADOW acceptance, pending 81 tests and user-controlled
reload. Do not mark Discord trading alerts live.**
