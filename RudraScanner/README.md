# RudraScanner — canonical instructions and implementation plan

Updated: 10 October 2026, Europe/London.

**Read this document first in every future session.** Repository: `raghunathbhandari/ASJR`, production branch `main`. Operational history: `ASJR_Analyst/OPERATIONAL_HANDOFF.md`.

**LATEST MONDAY DEPLOYMENT PREP (code committed, VPS tests still pending):** See `RudraScanner/MONDAY_LIVE.md` and the `MONDAY 12 OCTOBER 2026` checkpoint below. **The verified 65-test Friday baseline is historical.**\n\n**PRIOR VERIFIED FRIDAY BASELINE — 10 Oct 2026 12:46:59 UTC:**
User pulled GitHub `main` successfully to commit `368cf6d3`
and ran the COMPLETE `RudraScanner/tests/` suite on their VPS:

```text
Ran 65 tests in 0.784s
OK
```

**65/65 PASSED, zero failures/errors.** The previously failing Friday
markout test, `test_markout_entry_next_bar_and_exit_after_six`,
now passes with its mocked signal respecting the 15-RTH-bar
detector warm-up. No real pattern logic needed changing.

**Friday 2026-10-09 historical test VERIFIED in earlier VPS output:**
40 IBKR instruments / 22,290 actual historical 5M WAP bars;
9,360 RTH session-reset VWAP-ready bars; 11 tagged
LONG research signals but 10 unique next-bar entry
opportunities (4 positive, 6 negative), **40% positive and
+0.0147% average hypothetical 30-minute return before costs**.
The saved IBKR backfill lives in the SAME dated ASJR DataLake;
do not redownload it for a simple replay. This was a
hindsight-selected retrospective cohort with overlapping
possible positions, provisional setup thresholds and no
slippage or fees: NOT a prospective or profitable live backtest.

**Next stage:** audit live Chakra IBKR historical/scanner callbacks,
then (with user-controlled restart and approval) test
`RUDRA_SCANNER_MODE=shadow` during a genuine US session.
The four live scanner code results, live WAP, per-stock
1H warm-up, real-time technical signals and Discord delivery
are NOT yet verified. Production remains **OFF**; Wicks
and locked Rudra-Reversal are unchanged.
Detailed Friday results: `RudraScanner/FRIDAY_REPLAY.md`.
Older checkpoints later in this file are historical, superseded
by this verified entry.


### Additional safety tests added after initial Phase 2 checkpoint

- Added `RudraScanner/tests/test_reversal_bridge.py` (2 tests):
  new selected 1H Reversal tickers require >=150 completed bars
  before first-use state seeding; no historical signal flood.
- The current source inventory is **55 unittest methods total**:
  24 previously VPS-passed + 31 new as yet UNVERIFIED tests.
  The test/activation checklist is
  `RudraScanner/FULL_TEST.md`. Its 50/50 outcome must be
  checked from the actual user's VPS terminal, not assumed.

### Pattern symmetry and request-scoped WAP tests added

- `RudraScanner/tests/test_patterns.py`: five deterministic
  pattern-family tests, **both LONG and SHORT** per family,
  using constructed OHLC candles. These test the current
  provisional detection logic, NOT audited profitability.
- Real WAP capture is now scoped to registered 5M historical
  request IDs only; all other EWrapper history responses are
  left alone to prevent sidecar memory growth. Original 6-column
  callback continues to work in OFF mode.
- The final source inventory after these additions is
  **55 offline test methods (24 earlier VPS-verified + 31
  new, UNVERIFIED)**. See `RudraScanner/FULL_TEST.md`
  for the exact SSH commands. No new test PASS is claimed
  until the user shares actual VPS output.

## MONDAY 12 OCTOBER 2026 — Live Chakra SHADOW implementation committed

**LATEST IMPLEMENTATION — read this BEFORE older Friday snapshots.**
The user authorised putting RudraScanner into the existing
live Chakra scanning code for Monday and reviewing all code.
The GitHub implementation is now ready for a controlled
Monday **SHADOW** production-data run, with ALL existing
Wicks and locked Reversal alerts/monitored names
preserved. **Real Monday execution is NOT yet verified.**

**Authoritative deployment document:**
`RudraScanner/MONDAY_LIVE.md`.

### What code is now applied

1. `ASJR_Analyst/config/rudra_scanner_runtime.json`
   schedules `mode=shadow` on **2026-10-12 ET**,
   `research=true`, `alerts_enabled=false`,
   `thresholds_approved=false`. Env
   `RUDRA_SCANNER_MODE` overrides this mode.
2. Existing `ASJR_Analyst/Tests/test_asjr_pipeline.py`
   version `2026.10.10.12` sets up PASSIVE WAP
   callback capture before existing 5M bars, then
   performs Wicks and locked 1H Reversal delivery
   BEFORE the new four-code IBKR discovery,
   new selected-stock/sector 5M sidecar and
   hourly-cached 1H data import. Preserves legacy
   `universe.build_universe()` and its alert list.
3. `RudraScanner/bot_hook.py` has hot-read
   Monday runtime mode, separate fixed/AI/IBKR
   capped selection (up to 10/10/10); four scanners
   TOP_PERC_GAIN, TOP_PERC_LOSE, HOT_BY_VOLUME,
   MOST_ACTIVE with no default 4% gain filter.
   Source/status files inside **one shared DataLake**.
4. `RudraScanner/live_round.py` reuses original
   IBKR WAP-containing 5M stock bars and fetches
   only missing selected stocks plus SPY/QQQ/
   evidenced sector ETFs from SAME app. Uses
   as-of completed 5M index+sector alignment
   versus previous verified RTH close;
   unavailable benchmark/sector => WAIT.
   Computes actual IBKR WAP-VWAP, continuous
   EMA9, rolling RVOL20 reference and five
   experimental LONG/SHORT setups. Writes
   `reports/scalp_radar.txt`, scanner CSV
   and JSON diagnostics in common date DataLake.
5. `RudraScanner/hourly.py` caches up to
   30 selected 1H stock histories every hour for
   later Reversal research; it does **not** change
   locked Reversal indicators, ticker list, states
   or Yahoo NQ live alerts in Monday SHADOW.
6. `RudraScanner/delivery.py` and
   `ASJR_Analyst/Utils/asjr_alerts.py` wire a
   **separate** scanner message queue through the
   existing Chakra `prepare_alert()`,
   `mark_alert_sent()` and optional sender,
   preserving Wicks first, Reversal second, Scanner
   last. Double-gate remains DISABLED: no
   new Discord pattern alerts until approved;
   no order placements are implemented.
7. `RudraScanner/live_preflight.py` adds a
   read-only Monday readiness check, including
   scheduled mode, current AI CSV expiry, fixed
   config, original alerts and scanner bridge.

**Current test evidence:** the user previously
**verified 65/65 offline tests** (0.784s,
zero errors). The newest GitHub source contains
**81 unit tests total** after 16 Monday cases
(7 sidecar, 2 scanner queue, 2 preflight,
5 Chakra bridge) were added. These newest tests
have **NOT** yet been run on user's VPS.
No claim of 81/81 PASS is authorised until user
shares console output.

### Mandatory VPS commands BEFORE restarting existing Chakra

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m compileall -q RudraScanner ASJR_Analyst/Tests/test_asjr_pipeline.py ASJR_Analyst/Utils/asjr_ibkr.py ASJR_Analyst/Utils/asjr_alerts.py
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/live_preflight.py
```

**Expected, not yet observed:** 81 tests, OK.
The user-controlled Git pull/restart is necessary:
GitHub commits do not reload an existing running
Python `tmux` process. Never start a second
Chakra process. Monday first RTH open is 14:30
UK BST; patterns are gated until at least 15:00 UK.

**AI-hourly blocker:** The attempted additional
ChatGPT hourly GitHub AI CSV update schedule
FAILED because the account already has five
active tasks. There is NO automatic AI
CSV refresh created by this change. Saturday's
AI news rows expire **2026-10-12 12:00 UTC**
(13:00 UK), before Monday RTH; such rows
correctly become ineligible unless refreshed.
The new live IBKR and Fixed scanners can still
work with fewer than 30 total stocks, but do
not claim a verified 10+10+10 full list if AI
is expired. Existing AI research tasks must
be changed/paused before one can be scheduled;
do not silently alter the user's other alerts.

**Remaining live acceptance blockers:** VPS external
`/root/trading/utils/trading_sudarsan_chakra.py`
is not in GitHub and has not been code-audited;
new Monday real four-scanner callbacks, actual
live WAP and ETA/pacing are unverified. Friday
was only retrospectively 10 independent
opportunities, 40% positive markouts before
costs — no validated strategy threshold edge.
Discord flags OFF and no production scanner
buy/sell signals are promised. Keep existing
Wicks/Reversal protected.

---

## LATEST VPS TEST UPDATE — 2026-10-10 12:41 UTC

**User observed new Friday replay suite: 65 tests ran, 64 passed
and 1 failed** (`Ran 65 tests in 0.746s;
FAILED (failures=1)`). All eight other Friday tests and
previous 56 unit tests completed OK.

Only failure:
`test_friday_round.FridayReplayTests.test_markout_entry_next_bar_and_exit_after_six`.
Its synthetic `fake_signal()` was unconditional, allowing a
mocked trade at Friday RTH candle **index 6** (the 30-minute
execution gate). The test asserted a real detector's
minimum **15 completed RTH bars** (index >=14), which its
mock had skipped, so `AssertionError: 6 not greater
than or equal to 14`. **No failing live rule or
incorrect historical backtest signal was observed.**

**Fix COMMITTED, not yet VPS-retested:** Only
`RudraScanner/tests/test_friday_round.py` was changed,
to make the mocked detector return no signals before
15 completed RTH bars. The existing real `patterns.py`,
`friday_round.py`, and live Chakra logic were NOT altered.
Suite remains **65 cases**. Do not claim 65/65 passed
until user supplies new output.

**Friday retrospective backtest is independently confirmed:**
cached 22,290 real historical IBKR WAP 5M bars across
40 symbols and 9,360 valid RTH VWAP bars; 11 pattern
labels but **10 deduplicated entries**, 4 positive,
6 negative, **40%** positive, **+0.0147%**
mean 30-minute markout per distinct opportunity before
costs. The duplicate was one AMZN candle tagged twice.
The saved backtest remains a hindsight-biased retrospective
study with no portfolio P&L and no live signals.
Output status `FRIDAY_RESEARCH_ONLY`,
`selection_hindsight: true`, 0 Discord sends.

**Next direct SSH validation** (no IBKR redownload required):

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
```

Expected (unverified after fix): `Ran 65 tests`, `OK`.
Optional saved Friday summary already exists; no need to run
`--download-ibkr` again. If later regenerated, use
`/root/trading/venv_new/bin/python RudraScanner/friday_round.py
--date 2026-10-09 --save`.

**Production:** RudraScanner feature gate OFF; Wicks,
locked 1H Rudra-Reversal and Discord delivery unchanged.

---

## LATEST VPS OBSERVED — Friday 9 Oct historical IBKR/WAP research replay

**User tested on 2026-10-10:** after pulling new source files,
`friday_round.py --date 2026-10-09 --download-ibkr
--host 127.0.0.1 --port 4002 --client-id 91 --save`
succeeded using the user's IBKR historical API connection.
**40/40** instrument requests returned bars; **22,290**
historical 5M candles across 30 test stocks + SPY/QQQ
+ eight sector ETFs; **22,290 actual historical WAP
values**; **9,360** RTH bars with valid reset VWAP;
**zero reported IBKR backfill failures**.

**Actual Friday outcome:** **11 tagged five-pattern research
signals**, 5 positive / 6 negative, **45.45% pattern-level
positive**, +**0.0311%** mean 30-minute markout before costs.
Hitchhiker 6 (2 wins, −0.0364% mean); Back$ide 4
(2 wins, +0.0914% mean); Second Chance 1
(1 win, +0.1947%). Rubberband/Fashionably Late 0.
All 11 were LONG. **1,853** of 2,160 eligible
stock RTH candles lacked aligned index/sector context;
36 blocked for incomplete setup history and eight
late-horizon events had no complete 30-minute exit.

**CRITICAL non-independent labels:** AMZN's **20:25 UK**
Hitchhiker and Second Chance are the SAME underlying
next-open entry and +0.1947% markout.
Unique-entry diagnostic: **10 possible entries**,
**4 positive / 6 negative = 40.00%**, and
**+0.0147% average return before costs**. Other
entry opportunities can overlap in time; no
position sizing, stop, slippage, commission or
portfolio P&L is simulated. The Saturday-selected
30-name candidate set is hindsight-biased for
Friday discovery, and the 30-minute exit horizon
is a temporary research comparison, not approved.

**Follow-up source change COMMITTED, awaiting VPS test:** 
`RudraScanner/friday_round.py` now prints
both raw pattern and **distinct-entry** metrics,
and `tests/test_friday_round.py` adds a regression
case. **65 source test methods**, of which the earlier
56-unit baseline was VPS VERIFIED; the nine Friday
replay tests are NOT yet observed as passing.
The user's **IBKR WAP backfill was successfully
saved in the Friday common DataLake**, so next
time no extra API requests are required:

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/friday_round.py --date 2026-10-09 --save
```

Research result interpretation and source files:
`RudraScanner/FRIDAY_REPLAY.md`.

**Production remains unchanged:** mode OFF, no
real-time four-code scanner verification,
no scanner Discord signal, no orders.
Next proper research step after replay QA:
separate retrospective candidate analysis from
as-of-open scanner universe, deconflict overlapping
entries, and compare realistic exits with costs
across more dates before locking thresholds.
Continue to preserve Wicks and locked Reversal.

---

## LATEST IMPLEMENTATION — Friday 2026-10-09 one-round historical research

**User request (Saturday 2026-10-10 UK):** "any way we can run
this total code for Friday, to do a one round Backtest?"
The Friday replay entry point is now committed to GitHub as
`RudraScanner/friday_round.py`, with instructions in
`RudraScanner/FRIDAY_REPLAY.md` and **8 additional offline
unit tests** in `RudraScanner/tests/test_friday_round.py`.

### Immediate available test on the saved Friday DataLake

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/friday_round.py --date 2026-10-09
```

The script does one complete Friday RTH 5-minute historical pass
using the **same `build_scanner_features` and
`detect_five_patterns` code**, not the live bot. It requires
actual IBKR bar WAP for VWAP and fresh as-of-candle SPY,
QQQ and sector-ETF prices. The saved Friday DataLake did not
include WAP or usable same-time sector ETF history, so an
offline-only run correctly reports **NO EVALUABLE SIGNALS**
with blockage counts — this is NOT a 0%-win backtest.

### If IBKR Gateway/TWS API is available on the weekend

Run the separate **read-only historical bar request** via
`ib_async` (no bot restart, no live trading):

```bash
/root/trading/venv_new/bin/python RudraScanner/friday_round.py \
  --date 2026-10-09 --download-ibkr \
  --host 127.0.0.1 --port 4002 --client-id 91 --save
```

The code requests real historical `TRADES` 5M candles
from Friday and two earlier days, from the frozen retrospective
30 names + SPY/QQQ + sector ETFs. It reads
`ib_async.BarData.average` (historical bar WAP), not
invented HLC3, and enforces 09:30 ET RTH VWAP reset.
It checks IBKR stock contracts but does **not** claim to
verify issuer fundamentals or market cap. The gateway
may be disconnected or have weekend/pacing/permissions issues;
such errors are reported as failures, not made-up results.
The source is saved **only** as named test data under the
same 2026-10-09 DataLake:
`raw/rudra_friday_ibkr_wap.csv` and
`reports/rudra_friday_ibkr_backfill_status.json`.

Bar-by-bar replay gates direction using the last completed
5M candle SPY/QQQ/sector ETF return versus the immediately
preceding verified 15:55 ET RTH close; requires each benchmark
to have the SAME current 5M timestamp. Five patterns are
evaluated only with all candles completed **as of signal time**;
exits require strictly consecutive bars and are labelled as
hypothetical **next 5M open to close after six 5M bars**
(30-minute fixed-horizon markout, no fees/slippage).
One test also verifies that stale sector/index candles cannot
quietly authorise entries.

**CRITICAL HINDSIGHT BIAS:** The Friday frozen candidate
list was selected using Saturday news and Friday-after-close
movers. Even with exact WAP, this is a retrospective
**technical RESEARCH replay**, **not** a valid unbiased
Friday-morning stocks-in-play discovery backtest. The
numerical pattern thresholds and 30-minute exit are NOT
user-approved locked strategies, and overlapping signals
are not a realistic portfolio equity curve.
No Wicks or locked 1H Reversal rules are changed.

### Verification status after this addition

- Prior **56/56 unit tests on user VPS PASSED**, verified
  in 0.497s. These results precede this new Friday code.
- New `tests/test_friday_round.py` adds **8 tests** for
  historical 30-universe, missing WAP, missing/stale QQQ,
  as-of-5M context, hypothetical next-open/six-bar exit,
  weekend date and direction gating.
- **Current suite source inventory: 64 cases**, but the
  new 8 tests and the Friday research runner
  have **NOT YET BEEN VPS VERIFIED**.
- Scanner mode stays `OFF` by default. No broker API
  call, Discord send, VPS restart, order or bot state
  change was initiated by the assistant.
- **Next session:** review actual SSH test output, fix
  any failures, review broker returned WAP/ETF availability
  if the user opts to run a read-only Gateway request,
  then interpret genuine pattern counts and markouts
  without conflating them with validated strategy profit.

---

## CURRENT VERIFIED STATE — 2026-10-10: **56 / 56 VPS tests passed**

**Authoritative resumption checkpoint.** User ran from
`/root/trading/ASJR` after a successful `git pull --ff-only
origin main` (fast-forward from `e3250e40` to `42c45aae`):

```text
Ran 56 tests in 0.497s
OK
```

All original 55 Phase 2 tests and the new pandas empty-baseline
`FutureWarning` regression test passed; **zero errors, zero
failures and no pandas warning in the supplied output**.
The updated `RudraScanner/volume_history.py` empty-concat fix
is therefore **VPS VERIFIED**. The user did not run a new
connected IBKR scanner or live bot cycle in this test.

**Prior verified offline evidence remains**: 2026-10-09 legacy
historical DataLake replay selected **30/30 candidates** (10
FIXED + 10 AI + 10 old IBKR mover-list substitute);
`datalake_test.py` processed **56,027 historical completed
five-minute bars from 106 tickers**, with continuous EMA9 OK,
but actual IBKR WAP VWAP **0 rows READY**, RVOL20 **0 rows
READY**, experimental detectors and Discord **DISABLED**.
Historical replay **does not** prove four live IBKR scanners,
VWAP correctness on a real feed, Reversal shared 1H coverage,
new live trade signals, or reliable Discord sending.

**Next controlled stage:** audit the deployed VPS external
`EWrapper` callback and the existing Chakra runner, then
run new IBKR four-code discovery in **SHADOW** only during an
actual US trading session, preserving the legacy Wicks and
Rudra-Reversal import universe. Check scanner callback statuses,
real contract identity, 5M WAP, session timestamps, pacing,
DataLake files, and version. Keep
`RUDRA_SCANNER_MODE=off` in production until user-controlled
activation. Do not turn on ACTIVE, five-pattern Discord,
or alter Wicks' ticker scope without explicit review.
The AI research snapshot expires Monday 12 October 2026
at 12:00 UTC / 13:00 UK and must be refreshed before RTH.

**Operational handoff:** `RudraScanner/FULL_TEST.md` and
`ASJR_Analyst/OPERATIONAL_HANDOFF.md` carry the same
verified 56/56 state. Older 55-test / "pending" sections
below are historical chronological records, superseded here.

---

## VERIFIED VPS TEST — Saturday 2026-10-10, 55/55 PASSED

**LATEST USER-OBSERVED TEST:** User ran the entire Phase 2 offline
VPS test sequence. All **55 Python unit tests PASSED** in **0.531 s**
with **zero failures/errors** and the `compileall` syntax check
returned with no errors. These are actual user-supplied console results,
not estimates.

- Friday 2026-10-09 historical **bot-hook REPLAY**:
  `LEGACY_GAPUP_REPLAY_NOT_LIVE`, **84** old mover-list
  rows passed the replay's limited daily price/volume screen;
  **30/30 candidates = 10 FIXED + 10 AI + 10 historical IBKR**.
  Read-only: **no IBKR API calls, live alerts or saved reports**.
- Friday shared raw DataLake **5-minute indicator replay**:
  **56,027 completed bars**, **106 archived tickers**, continuous
  EMA9 **OK**, exact IBKR-WAP VWAP **WAP_MISSING_OR_INCOMPLETE_RTH**
  with **0 valid RTH VWAP bars**, RVOL20
  **INSUFFICIENT_20_FULL_RTH_SESSIONS** with **0 ready rows**.
  `TOP-DOWN context gate = 0 WAIT` is a count from the
  **DISABLED** detector mode; **it does NOT mean SPY/QQQ
  or any sector context was verified**. The five experimental
  detectors were **DISABLED** and **0 trade signals** existed.
  `Discord` was **DISABLED**, as intended.
- Pandas printed only a nonfatal `FutureWarning` at
  `RudraScanner/volume_history.py` for concatenating an
  empty DataFrame. **Fixed in a new GitHub commit** by avoiding
  empty inputs; a new unit regression test explicitly treats that
  warning as an error. **This follow-up fix has not yet been
  VPS-tested**: new source inventory is **56 unit tests**.
- AI/FIXED status remain `PARTIAL` because some article timestamps
  are unavailable and legacy `ONDS` is deliberately excluded;
  neither caused a unit-test failure.
- Production **`RUDRA_SCANNER_MODE=off`**, no observed real
  connected 4-code IBKR scanner or historical WAP callback test,
  no activated new 30-name imports, no real 1H coverage
  confirmation or scanner Discord send.
  **Do not restart/activate Chakra automatically.**

### Small follow-up test after pulling warning fix

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/datalake_test.py --date 2026-10-09
```

**Expected, not yet VPS-observed for the fix:** 56 tests, final OK,
no `FutureWarning`; 5M quality results remain unchanged
except warnings disappear. Keep actual WAP/RVOL20 shown as not
ready until their required sources/history are present.

### Next step after the 56-unit regression test

Review the VPS external IBKR `EWrapper.historicalData`,
`scannerData` and `scannerDataEnd` callback contracts;
then conduct a **controlled one-session SHADOW scan** using the
existing Chakra IBKR application only when the user enables it.
Record actual scan-code states, selected source counts, WAP fields,
bar timestamps, pacing and CSV output from the one common DataLake.
SHADOW does **not** replace Wicks/Reversal ticker coverage.
Do not promote the historical 30/30 replay as a live 30-stock scan.

**Activation blockers:** fully verified live four-scanner callbacks,
actual WAP VWAP and true time-matched RVOL20 historical readiness,
hourly 1H Reversal coverage and first-use state, eligible stock
contracts, research threshold approval, and Discord acknowledgements.
The ten AI news candidates expire **2026-10-12 12:00 UTC /
13:00 UK**; refresh before Monday US open.

---

## PHASE 2 CODE CHECKPOINT — 2026-10-10: full gated Scanner / Reversal integration

**AUTHORITATIVE LATEST STATE:** User's existing VPS evidence is
**24/24 old unit tests OK** and **30/30 historical ticker replay OK**.
Following user request to implement the full system, code for the
remaining indicator, shared data, research detectors, 1H bridge,
rolling volume reference and separately gated scanner delivery was
COMMITTED. **The NEW extended suite now has 55 test methods and has
NOT YET BEEN RUN on the user's VPS. Real IBKR/Gateway and actual
production messages remain UNVERIFIED.** Do not call the scanner
fully deployed on the basis of committed code alone.

### New committed files and safe integration paths

- `RudraScanner/features.py`: completed 5-minute continuous EMA9;
  exact RTH VWAP from **IBKR bar WAP × volume**, reset 09:30 ET;
  no HLC3 substitution; annotated missing WAP. Local 12-bar
  volume ratio explicitly NOT labelled RVOL20.
- `RudraScanner/wap_capture.py`: feature-gated capture of actual
  bar WAP on the **existing** `EWrapper.historicalData` callback;
  preserve old six-field callback and align WAP to parser timestamps.
  `ASJR_Analyst/Utils/asjr_ibkr.py` attaches an extra WAP column
  only when the callback sidecar really supplies matching values.
- `RudraScanner/volume_history.py`: true time-matched 20-prior-complete-
  RTH-session cumulative volume baseline, persisted **inside the common
  dated ASJR DataLake**. Each new day's
  `processed/rudra_scanner_rvol20_baseline.csv` can read the latest
  earlier trading-day baseline and combine real complete sessions.
  Protects reference against five-day raw-folder cleanup; 78 exact
  RTH five-minute bars are required to qualify a reference day.
  Until enough real sessions exist, RVOL20 is **UNAVAILABLE**.
- `RudraScanner/patterns.py`: five symmetric 5M
  LONG/SHORT detectors (Hitchhiker, Back$ide, Rubberband,
  Second Chance, Fashionably Late). Their numerical thresholds
  remain **PROVISIONAL / RESEARCH ONLY**, not user-approved or
  demonstrated by backtesting.
- `RudraScanner/topdown.py`: **Index → Sector → Ticker**
  directional gate requiring same-date SPY/QQQ and sector ETF
  evidence; missing or mixed data means WAIT.
- `RudraScanner/engine.py`: shared DataLake
  `processed/rudra_scanner_features.csv` and namespaced
  `reports/rudra_scanner_research.txt` /
  `reports/rudra_scanner_research_status.json`; these are
  **not** authoritative live signals while testing.
- `RudraScanner/hourly.py`: bounded existing-IBKR-connection
  1H historical fetch for up to 30 selected stocks; refresh at
  most once per hour when ACTIVE, store
  `raw/intraday_1h.csv` + status under common DataLake,
  retaining >=150 completed 1H-bar eligibility.
- `RudraScanner/reversal_bridge.py`: seed new Reversal symbols
  from the most recent completed 1H candle only after >=150
  historical bars; prevents accidental historical signal floods
  without rewriting locked BB(20,2) strategy.
- `RudraScanner/delivery.py`: independently deduplicated scanner
  Discord messages, separate from Wicks and Reversal.
  Two explicit controls required:
  `RUDRA_SCANNER_ALERTS=1` AND
  `RUDRA_SCANNER_THRESHOLDS_APPROVED=1`.
  Default DISABLED. Failed sends remain unacknowledged.
  No automated orders.
- `ASJR_Analyst/Tests/test_asjr_pipeline.py` version
  `2026.10.10.5`: calls scanner from the existing 5M Chakra
  method, reuses same 5M request; in SHADOW saves indicator
  diagnostics, in explicitly opted-in ACTIVE selects common
  up-to-30 stock list, fetches shared 1H cache, sends the
  *same locked Reversal method* these names plus NQ, and
  retains unchanged Wicks detection logic. Market/sector
  matching and research calculations only when enabled,
  with independently gated scanner Discord.
  Exception paths for scanner stages are isolated from
  existing production alerts.
- `RudraScanner/datalake_test.py`: read-only offline
  historical 5M input/indicator coverage report from Friday's
  common DataLake, expected to show missing exact WAP
  until real callback capture is verified.
- New tests: `test_features.py` (9), `test_hourly.py` (3),
  `test_topdown.py` (5), `test_delivery.py` (4),
  `test_volume_history.py` (3), plus the previously
  VPS-verified 24 tests: **55 in source**.

### Flags and safety status

| Flag / mode | Default | Behaviour |
|---|---|---|
| `RUDRA_SCANNER_MODE=off` | **OFF** | No new scanner API requests, no strategy changes |
| `RUDRA_SCANNER_MODE=shadow` | Opt in later | Four real IBKR scanners + WAP tap + research diagnostics from existing legacy 5M import; original ticker universe and alerts unchanged |
| `RUDRA_SCANNER_MODE=active` | **NOT ENABLED** | Experimental new <=30 stock 5M universe and hourly common 1H Reversal source; **changes the set of names Wicks monitors** even though its detection rules are unchanged; requires user approval, pacing/contract verification and 55-test pass first |
| `RUDRA_SCANNER_RESEARCH=1` | OFF | Evaluate provisional five-pattern research only with actual WAP and current index/sector context |
| `RUDRA_SCANNER_ALERTS=1` plus `RUDRA_SCANNER_THRESHOLDS_APPROVED=1` | BOTH OFF | Scanner Discord delivery requires both flags; do not approve pattern thresholds by assumption |

**VERY IMPORTANT:** Weekend historical replay is only a test of
ticker membership; it does not supply actual IBKR WAP or current
20-session RTH volume data. Before activating ACTIVE, verify whether
Wicks should monitor the new shared 30 stocks or retain a separate
legacy watch universe (which would increase data requests).
Also verify the external VPS EWrapper callback and paced historical
requests. No live bot restart, remote IBKR call, or Discord test
was performed by the assistant.

### Execute the full weekend VPS test now

Canonical checklist with explanations:
`RudraScanner/FULL_TEST.md`.

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m compileall -q RudraScanner ASJR_Analyst/Tests/test_asjr_pipeline.py ASJR_Analyst/Utils/asjr_ibkr.py
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/bot_test.py --date 2026-10-09 --ibkr-source-date 2026-10-09
/root/trading/venv_new/bin/python RudraScanner/datalake_test.py --date 2026-10-09
```

**Expected**, not observed for new files: 55 tests, final `OK`;
30/30 historical ticker candidate report; 5M feature report
with EMA9 present but actual WAP/VWAP flagged unavailable
because Friday's stored OHLCV lacks WAP. A correctly blocked
research setup is a PASS, not a missed live trading alert.
Do not enable SHADOW/ACTIVE/RESEARCH/ALERTS based merely
on expected numbers. Wait for actual test stdout/stderr and
repair any failures; verify state in this README next session.

**Pending acceptance:** new 55-case test outputs, real connected
four-code scan, accurate actual WAP and sector data, IBKR 1H
historical coverage, 5M/1H performance and alert deliveries,
user agreement on numerical pattern thresholds and Wicks scope,
plus automated hourly sourced AI research refresh.

---

## VERIFIED VPS CHECKPOINT — 2026-10-10, Friday replay + 24/24 tests

**LATEST OBSERVED STATE (supersedes older pending-test notes below):**
The user executed and shared the actual SSH output after pulling the
latest GitHub code; `git push` said `Everything up-to-date` and
`git pull` said `Already up to date`. The new offline Chakra
bot-hook replay and **all 24 offline tests passed**.

### Exact output verified from the user's VPS

Command:

    /root/trading/venv_new/bin/python RudraScanner/bot_test.py --date 2026-10-09 --ibkr-source-date 2026-10-09

Observed:

| Check | Actual output |
|---|---|
| Mode | `BOT HOOK REPLAY | HISTORICAL DATA - NOT LIVE` |
| DataLake and IBKR legacy source | `2026-10-09` |
| AI and FIXED status | `PARTIAL` and `PARTIAL` (previously diagnosed publication-time/ONDS exceptions) |
| IBKR source | `LEGACY_GAPUP_REPLAY_NOT_LIVE` |
| Historical screened names | **84** |
| Candidate selection | **30 / 30**, deduplicated |
| Selected by source | **FIXED 10**, **AI 10**, **IBKR 10** |
| Signals | `NOT IMPLEMENTED; 0 live alerts sent` |
| Broker calls | **None**; source was archival DataLake, NOT four live scans |
| Write mode | **Read-only**; `--save` was NOT passed; no replay files written by this command |

**Exact selected lists observed:**

- FIXED (10): `AKAM, AMAT, CRDO, INTC, MSFT, ORCL, QCOM, SMCI, WDC, WTTR`.
- AI (10): `AAPL, AMT, AMZN, HUM, JPM, LITE, NVDA, PLTR, SPCX, TMUS`.
- Historical IBKR replay (10): `ASTS, AXTI, DDOG, DE, MRNA, SNOW, SWKS, T, VZ, ZS`.
- This is input provenance and weekend offline selection, **not verified
  market-cap, financial-quality eligibility or a recommendation to trade**.

Full test command observed:

    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v

**Actual result: `Ran 24 tests in 0.170s / OK`, 24 passed,
0 failures, 0 errors.** The suite includes the previous 18 discovery,
EMA9, fixed/AI/IBKR cap and storage tests plus the six
`test_bot_hook.py` tests for OFF, gated SHADOW call, guarded REPLAY,
non-lookahead and namespaced optional save. This verifies offline code
on the user's VPS; it does **not** verify the connected live IBKR scan.

### Exact implementation status and next step

| Component | State after verified VPS run |
|---|---|
| Fixed + AI + historical IBKR candidate union/cap | **VPS VERIFIED** |
| Bot method hook `run_asjr_manual_pipeline` call present in GitHub | **CODE COMMITTED**; feature gate defaults OFF |
| Offline replay path `bot_test.py` | **VPS VERIFIED, READ-ONLY** |
| New 4-code IBKR live scanner via connected Gateway | **NOT YET LIVE-VERIFIED** |
| Actual WAP capture, RTH VWAP calculation and 5M indicator join | **NOT YET IMPLEMENTED/VERIFIED** |
| Actual 5M five-pattern LONG/SHORT detectors | **NOT YET IMPLEMENTED** |
| Shared 1H IBKR import for newly selected Reversal stocks | **NOT YET IMPLEMENTED** |
| Scanner Discord output / dedup / ack; hourly AI automation | **NOT YET IMPLEMENTED/ACTIVATED** |
| Wicks and locked 1H Reversal | **UNCHANGED BY THIS TEST** |

**Next stage: connected scanner SHADOW verification inside the existing
five-minute Chakra job**, then careful data integration, real WAP/VWAP
and replay-tested detector implementation. SHADOW should be enabled
only when the user approves a controlled live-session test and the
existing IBKR app's scanner callbacks are checked. Historical
`ibkr_gapup.csv` is only a weekend TEST substitute: do not continue
using it as if it were Monday's current IBKR scanner output. The AI
research expires **Monday Oct 12 at 12:00 UTC / 13:00 UK** and needs
refresh before RTH.

**Do not assume:** There is no evidence of a live market scan,
correct live output delivery, or 5M/1H real pattern alerts yet.
Production operation remains **feature-gated OFF** until validation.
Older historical "tests pending"/"integration not started" paragraphs
elsewhere in this README describe earlier checkpoints and are
superseded by this verified update. Continue updating this latest
checkpoint and `ASJR_Analyst/OPERATIONAL_HANDOFF.md` after changes.

---

## LATEST UPDATE — 2026-10-10: Bot method wired, weekend historical replay ready

**User decision:** after all 18 original offline tests passed on the VPS,
implement the RudraScanner bot call now. Since the US market is closed
Saturday, use **Friday 2026-10-09 existing DataLake ticker sources as a
historical IBKR candidate replay**, without pretending the four new IBKR
scanner codes have run live.

### VERIFIED by the user before this change

- VPS SSH read-only smoke test: **20/30**, FIXED 10, AI 10, IBKR 0,
  missing IBKR scan correctly labelled NOT_YET_SAVED; ONDS excluded.
- Full offline suite **18 tests passed, 0 errors/failures, 0.181 seconds**
  with `python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v`.
  This was before adding the new bot/replay tests. The previous
  handoff's "unittest results pending" wording is SUPERSEDED by this
  measured result.

### Actual code committed in this change

- **Production bot method integration**:
  `ASJR_Analyst/Tests/test_asjr_pipeline.py` version
  `2026.10.10.1` imports
  `RudraScanner.bot_hook.run_bot_shadow` and invokes it from
  `run_asjr_manual_pipeline(app,...)` before legacy universe building.
  Scanner hook exceptions are separately logged and cannot interrupt
  legacy Wicks or Reversal; the hook status is added to returned result.
  **Default `RUDRA_SCANNER_MODE=off`** means no additional live IBKR
  requests or behavior changes until explicitly enabled.
- `RudraScanner/bot_hook.py`: existing connected IBKR app, no second
  connection/scheduler. Explicit `RUDRA_SCANNER_MODE=shadow` runs
  the four new IBKR discovery scanners, saves deduplicated capped
  FIXED/AI/IBKR candidates inside common DataLake and records health.
  It does **not** swap production tickers, request 1H or 5M bars for
  the new list, alter Wicks/Reversal, generate five-pattern signals
  or send scanner Discord alerts. Shadow scans are real IBKR requests
  ONLY if enabled with a connected gateway on a market session.
- **Weekend replay path**:
  `RudraScanner/replay.py` and
  `RudraScanner/bot_test.py` call the SAME bot hook with explicit
  `mode=replay,allow_replay=True`. Live pipeline does not authorize
  this mode. No broker requests; no bot startup/restart needed.
  Historical source:
  `ASJR_Analyst/DataLake/2026-10-09/raw/ibkr_gapup.csv`
  (an OLD +/-4% era mover list, not a four-code live scan) and
  `raw/daily_30d.csv` (20-session historical price/volume screen).
  Tickers with fewer than 20 valid sessions, non-current saved daily
  last bar, price <= $5 or average shares/day <= 1 million are
  rejected for the replay. Rank by average 20-day DOLLAR VOLUME,
  then deduplicate against 10 fixed + 10 AI and fill up to 10
  IBKR-source slots: historical/replay list is **NOT** a new 4% gate
  for the intended live scanner.
- Friday October 9 archived mover file **inspected in GitHub**:
  87 historical tickers; of those 84 qualify on saved 20-day
  price/volume data.
  Based on the same archived inputs (independent data check, **not** an
  executed VPS replay), the 10 historical IBKR-slot names are expected to
  be **MRNA, SNOW, VZ, T, DE, DDOG, ASTS, SWKS, ZS, AXTI** after
  removing fixed/AI overlaps. **Fundamentals have not been screened for
  these names**, so they are test-only candidates and must not trigger
  investment recommendations or live technical alerts. These figures are archival-source inspection,
  not observed execution of the new VPS replay command. 2026-10-09
  exact provenance is retained. **Historical market capitalization,
  company fundamentals, and realtime contract validity NOT verified**
  for the replay; names are ONLY input-test candidates, not approved
  investments or technical signals.
- Optional `--save` mode writes explicitly labelled
  `raw/ibkr_scanner_replay_list.csv`,
  `processed/rudra_scanner_replay_candidates.csv`,
  `reports/rudra_scanner_replay_report.txt`, and
  `reports/rudra_scanner_replay_status.json`
  under the SAME chosen shared day DataLake, never overwriting
  `raw/ibkr_scanner_list.csv` or the future authoritative
  `reports/scalp_radar.txt`. It never commits, pushes or sends Discord.
- Historical replay provenance uses `LEGACY_GAPUP_REPLAY`;
  `discovery.merge_candidates` preserves this label without
  treating it as any new live `SCANNER_CODES`.
- New `RudraScanner/tests/test_bot_hook.py` contains **six
  additional offline tests** for OFF mode, replay restriction
  in live bot, historical candidate screening, 10 slot cap,
  separate saved artifacts, future date rejection and the
  shadow call forwarding the existing app.

### NOW run this on SSH (outside market hours)

First safely pull the committed code, preserving local changes:

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
```

Test the new 10-source fallback DIRECTLY, calling the same bot hook
that the production pipeline imports (read-only by default):

```bash
/root/trading/venv_new/bin/python RudraScanner/bot_test.py --date 2026-10-09 --ibkr-source-date 2026-10-09
```

The expected replay is **up to 30/30 selected stocks** (10 fixed +
10 AI + 10 historical IBKR). The report MUST identify the IBKR bucket
as **LEGACY_GAPUP_REPLAY / HISTORICAL_NOT_LIVE**, never a successful
four-code IBKR scan. It must also show **0 live signals**.
Do not confuse candidate selection with five-pattern success.

After preview verification, saving TEST-only replay artifacts is
optional and explicit:

```bash
/root/trading/venv_new/bin/python RudraScanner/bot_test.py --date 2026-10-09 --ibkr-source-date 2026-10-09 --save
```

Then run **all tests including the six new ones**:

```bash
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
```

**Expected new test count is 24 (18 old + 6 new)**; not yet
observed on VPS after committing this change. Do not report 24 passed
until the user supplies actual output. Any failure must be fixed
before activating a production bot feature gate.

### Remaining implementation boundaries

The real bot call is **wired but default OFF**; legacy imports
and signals are unchanged. Do **not** restart the working bot or
enable live shadow scans until the user verifies the new tests and
chooses to proceed. To opt in later, configure
`RUDRA_SCANNER_MODE=shadow` in the EXISTING bot process environment,
not in a competing scheduler. Do not enable the historical
`replay` mode in the live bot; it explicitly refuses such use.

Still missing: real connected IBKR four-code verification;
true live 30-stock download replacement; 1H data for new Reversal
names; IBKR bar WAP capture and RTH VWAP; five approved pattern
detectors and numerical thresholds; genuine scanner Discord
delivery/ack and hourly AI source refresh. These are NOT
implemented by a historical replay. Existing Reversal, Wicks
and NQ data paths remain unchanged.

**Next user action:** run the direct `bot_test.py` weekend
replay and the complete unittest suite; share actual console output.
After that, validate/enable shadow on a live US trading session
with the user's restart control, then develop/import/alert
integration in safe stages.

---

## START HERE NEXT SESSION — latest checkpoint (2026-10-10 UK)

**STATE: Phase 1 VPS VERIFIED, including original 20/30 CSV preview, historical replay 30/30 candidate selection and 24/24 offline tests. Feature-gated bot method hook COMMITTED, default OFF. Live IBKR four-code scans, 1H/5M expanded imports, VWAP, five real detector families and scanner Discord alerts NOT yet implemented/verified.** This is the main
resumption point for any future assistant session. Read this section
before making code changes. Do not claim live scanner signals or successful
VPS testing without observing real outputs.

### Next user action and exact SSH tests

User has supplied a successful read-only SSH smoke-test output. The
separate full Python unittest output is still pending. Saturday 2026-10-10 is
a closed US equity trading day, but these OFFLINE checks work on the
previous US session 2026-10-09. Run in the VPS repository:

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
    /root/trading/venv_new/bin/python RudraScanner/ssh_smoke_test.py --date 2026-10-09

If Git has local changes or conflicts, do not reset or force-push. Inspect
and resolve safely. The SSH preview does not connect to IBKR, send Discord,
alter the DataLake, or start/restart Chakra. Unit tests use local fixtures.

**Now VPS-verified preview:** With the October 9 saved fixed
list and current AI CSV, the selected candidates should total up to
10 FIXED + 10 AI + 0 IBKR = 20 DISTINCT stocks, until the multi-code
IBKR scanner creates a real saved CSV. Missing IBKR list is
NOT_YET_SAVED, NOT a successful live scan. INTC is in both fixed/AI but
occupies one fixed slot. The old fixed file enables ONDS but the new
universe correctly excludes and reports it. Some AI published_at_utc
times are unknown; a PARTIAL evidence warning is expected, not
automatically a Python error. Compare actual output before claiming
that remaining unit tests passed; only the input smoke test passed.

### Confirmed system contracts

- **Shared DataLake:** ASJR_Analyst/DataLake/YYYY-MM-DD/ for ALL modules,
  including RudraScanner and Rudra-Reversal. No second collector or scheduler.
- **Shared stock candidate cap:** maximum 30 UNIQUE names:
  10 FIXED from dated watchlist + 10 AI web research + 10 IBKR scanners.
  Duplicates fill from next eligible candidate in the same source.
  Cap applies BEFORE future 5M and 1H historical imports. Legacy Wicks
  import and locked 1H Reversal stock list not changed yet.
- **Discovery filters retained:** corporate US stocks over $5,
  average daily volume over 1 million, market cap over $500 million;
  50 results per IBKR scan code. Four codes: TOP_PERC_GAIN,
  TOP_PERC_LOSE, HOT_BY_VOLUME, MOST_ACTIVE. No fixed +/-4% gate
  for new scanner membership or technical entry.
- **Indicators:** completed 5-minute EMA9 across available trading days,
  including premarket and extended hours, NO EMA9 daily reset or
  fabricated gap-filling. VWAP is used TOGETHER with EMA9 and resets
  at US RTH 09:30 ET. The user accepted real IBKR historical-bar WAP
  as VWAP input, but callback collection and calculation are NOT built.
  Include volume, price structure, Index -> Sector -> Ticker, fresh data.
- **Separate strategies, shared stock candidates:** 5M RudraScanner
  LONG/SHORT five detectors; locked Rudra-Reversal 1H Bollinger Band
  logic unchanged. NQ remains an additional Yahoo 1H instrument outside
  the 30 US stock cap. Reversal needs >=150 completed 1H bars per
  eligible name and cannot use missing 1H as a zero-signal finding.
- **Five requested scanner setup names:** Hitchhiker (momentum hold/break),
  Back$ide (reversal), Rubberband (extension snapback), Second Chance
  (breakout/breakdown retest), Fashionably Late (EMA9 and VWAP transition).
  Their numerical thresholds, backtests and production detectors
  remain UNIMPLEMENTED.
- **New expected trading-day behavior, NOT ACTIVE:** One existing
  five-minute Chakra cycle pulls Git, reads source CSVs, imports up to
  30 names, calculates indicators and five detector types, publishes
  saved plain report in shared DataLake, Git commits/pushes once,
  and delivers only new qualifying signals to Discord with ack/retry.
  Hourly AI researches/refreshes its own list and reviews that same
  mechanical report. SSH/on-demand AI reads saved signals without a
  separate market-data request. No valid setups -> no made-up alerts.
  Earlier example ticker signals shown to the user were ONLY
  ILLUSTRATIVE, never a real scan result. No hourly automation is
  actually running yet.
- **Source file status:** AI research CSV
  ASJR_Analyst/config/ai_scanner_list.csv holds permanent INTC plus
  SPCX, PLTR, LITE, AMT, HUM, AMZN, TMUS, AAPL, JPM, NVDA,
  researched after the Friday October 9 session. The news rows expire
  2026-10-12T12:00:00Z (13:00 UK Monday). These are WATCH ideas,
  not real LONG/SHORT trade signals; quality statuses are UNVERIFIED.
  SPCX stock/sector eligibility must be checked against actual IBKR.
  Fresh AI research is needed before Monday RTH.
- **Development files committed:** RudraScanner/discovery.py,
  universe.py, storage.py, ema9.py, ssh_smoke_test.py,
  print_saved.py, package init, and tests/test_discovery.py,
  test_universe.py, test_selection_caps.py, test_ema9.py.
  Their GitHub existence is verified; the user's VPS input smoke test passed, but the full unittest suite has not yet been observed.

### First engineering task AFTER receiving valid SSH output

**Integrate RudraScanner into the existing Chakra bot method**, not a
new process or independent scheduler. Audit
ASJR_Analyst/Tests/test_asjr_pipeline.py and the external VPS caller
/root/trading/utils/trading_sudarsan_chakra.py (its actual current
runtime content was not fetched). Preserve existing Wicks and Reversal
delivery, separate state/acknowledgements, and the user's restart control.
Add shared 30-name selection before downloads; use one common DataLake,
bounded 5M and 1H imports, and validate WAP/time/volume units and
live historical-feed lag. Implement RTH VWAP, sector context and the
five replay-tested detectors before live Discord messages. Require
feature-gated, nonintrusive tests, Git sync without force-push,
and observed logs/version/saved results/Discord deliveries before
calling scanner deployed. Ranking tie-breakers and numerical thresholds
are still subject to user approval; do not assume.

**After every material change:** update this section, add a dated
chronological note below, and update
ASJR_Analyst/OPERATIONAL_HANDOFF.md. This is the user's explicit
continuity requirement.

---


## VPS EVIDENCE UPDATE — 2026-10-10: SSH smoke test VERIFIED

**User supplied the actual VPS terminal output** from host
`nostalgic-mirzakhani` using this exact command:

```bash
/root/trading/venv_new/bin/python RudraScanner/ssh_smoke_test.py --date 2026-10-09
```

**RESULT: PASS for the intended READ-ONLY DISCOVERY / SELECTION smoke test.**
This is a new **observed VPS result**, not merely a synthetic expectation.

| Diagnostic printed by user's VPS | Observed result | Interpretation |
|---|---|---|
| AI status | PARTIAL; eligible rows **11**, expired **0** | AI CSV read successfully. Status PARTIAL from incomplete source publication timestamps; INTC duplicated as intended across sources. |
| Fixed status | PARTIAL; enabled **18**; exclusions **ONDS** | Fixed list read successfully; ONDS excluded under user policy despite enabled legacy row. |
| IBKR scanner CSV | **NOT_YET_SAVED**, rows **0** | New live IBKR multi-code scans **have not run**, not a scanner failure/success measurement. |
| Selected / max | **20 / 30** distinct stocks | **Correct** under the confirmed hard limit. |
| Per selection source | **FIXED 10**, **AI 10**, **IBKR 0** | Correct per-source quota and deduplication. |
| Unused slots | FIXED 0; AI 0; IBKR 10 | Expected without real IBKR scanner output. |
| NQ | Yahoo 1H separate from 30-stock cap | Correct displayed contract. |

**Exact selected candidates from the actual VPS printout:**

- **FIXED 10/10:** AKAM, AMAT, CRDO, INTC, MSFT, ORCL,
  QCOM, SMCI, WDC, WTTR.
- **AI 10/10:** AAPL, AMT, AMZN, HUM, JPM, LITE, NVDA,
  PLTR, SPCX, TMUS.
- **IBKR 0/10:** None; saved new scanner CSV does not exist yet.
- **One deduplicated shared list (20):** AAPL, AKAM, AMAT,
  AMT, AMZN, CRDO, HUM, INTC, JPM, LITE, MSFT, NVDA,
  ORCL, PLTR, QCOM, SMCI, SPCX, TMUS, WDC, WTTR.

**Observed warnings:**
- AI: LITE, HUM, NVDA — source calendar date known but
  `published_at_utc` exact time unavailable. Do not invent times.
- Fixed: ONDS — enabled old fixed watchlist row conflicts with
  user exclusion and is correctly omitted.
- IBKR: `NOT_YET_SAVED`; does not query IBKR from smoke test.

**Verification levels — DO NOT CONFLATE:**

- [x] Source files and documentation committed and checked on GitHub.
- [x] **User VPS SSH read-only ticker input smoke test output observed**;
      expected source counts and dedupe confirmed.
- [ ] Full Python `unittest discover` output received and passed.
- [ ] IBKR connected 4-code scanner callback verified in a session.
- [ ] 5M raw bars + actual WAP and 1H stock history validated.
- [ ] EMA9 + RTH VWAP and five pattern detectors replay-tested.
- [ ] Existing five-minute Chakra method integration implemented and tested.
- [ ] Scanner result saved, Git-pushed and correctly delivered to Discord.
- [ ] Hourly automatic AI CSV research refresh actually running.

**Important:** This result is **input selection**, not any
technical LONG/SHORT signal. It was executed during a closed US
market Saturday, using the October 9 daily fixed configuration.
It is not a live scanner or production bot run.

**Next recommended command to finish Phase 1 offline verification:**

```bash
cd /root/trading/ASJR
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
```

The user previously requested the subsequent implementation stage:
**integrate RudraScanner into the EXISTING Chakra 5-minute method**,
with a feature gate and preservation of live Wicks and locked
Rudra-Reversal alerts. Begin engineering work after reviewing test
results and resolving any actual failures; keep the live bot untouched
until integration testing and user-controlled activation.

## Current implementation checkpoint — 2026-10-10

This is the quick-start summary of **all decisions and implementation activity
from the 10 October 2026 session**. Detailed chronological records and caveats
follow below; amend this checklist after every subsequent change.

| Topic | Confirmed rule | Implementation state |
|---|---|---|
| DataLake | **One** `ASJR_Analyst/DataLake/YYYY-MM-DD/` shared by RudraScanner, Rudra-Reversal and other ASJR modules | Existing root inspected; new scanner discovery writes there only when explicitly invoked; live Reversal shared 1H ingestion not complete |
| Shared candidates | Fixed day watchlist + AI hourly research CSV + IBKR multi-scan CSV | `RudraScanner/universe.py` and `storage.py` committed |
| Hard ticker limits | Max **10 fixed + 10 AI + 10 IBKR = 30 distinct US-stock symbols** for both strategies; duplicates consume one slot | Code enforces cap before future 5M/1H imports; live bot not connected |
| Eligibility filters | US corporate stocks, price above $5, average volume above 1M, market cap above $500M, 50 returned per scanner code; **no ±4% entry/discovery gate** | Implemented in isolated `discovery.py`; live API filters not yet validated |
| Scanner modes | TOP_PERC_GAIN, TOP_PERC_LOSE, HOT_BY_VOLUME, MOST_ACTIVE | Implemented but no live IBKR test |
| Indicators | **Continuous EMA9** on completed 5M bars across premarket and dates; use **VWAP together with EMA9**, RTH-reset VWAP and volume/structure | Isolated `ema9.py` committed; exact VWAP calculation and IBKR WAP callback extension **not yet implemented** |
| Strategies | 5M RudraScanner five setup types, LONG + SHORT; 1H Rudra-Reversal retains locked BB rules; NQ stays on its existing Yahoo route | Scanner setup detectors and Reversal's new common 1H import **not connected** |
| Delivery | Existing five-minute Chakra job, Discord every cycle, AI hourly and read-only on-demand SSH; one Git pull/push cycle | Architecture approved, **not deployed** |
| Alerts | Preserve live Wicks and Rudra-Reversal alerts; never automate trading orders | Existing production code left unchanged |
| AI candidates | Friday 9 Oct source-linked web research, 10 candidate names + permanent INTC monitor, expiration Mon 12 Oct 12:00 UTC | `ASJR_Analyst/config/ai_scanner_list.csv` committed; **not automatically refreshed hourly** |
| SSH test | Inspect AI CSV, dated fixed list, optional already-saved IBKR scanner CSV, exclusions and 10/10/10 selection | `RudraScanner/ssh_smoke_test.py` committed; **not run on VPS yet** |

### Files changed during this implementation session

- New `RudraScanner/__init__.py`, `discovery.py`, `universe.py`,
  `storage.py`, `ema9.py`, `print_saved.py`, `ssh_smoke_test.py`.
- New offline tests in `RudraScanner/tests/`:
  `test_discovery.py`, `test_universe.py`, `test_selection_caps.py`,
  `test_ema9.py`.
- Updated `ASJR_Analyst/config/ai_scanner_list.csv`, this README,
  and `ASJR_Analyst/OPERATIONAL_HANDOFF.md`.
- The source snapshot covers **INTC, SPCX, PLTR, LITE, AMT, HUM,
  AMZN, TMUS, AAPL, JPM, NVDA**. All research quality statuses are
  `UNVERIFIED`; `SPCX` sector/underlying stock suitability must be
  checked with the actual IBKR contract before treating it as an eligible
  tradable US corporate stock. Do not infer successful research from a
  historical article link alone.
- Legacy October 9 fixed CSV includes **ONDS**, which conflicts with the
  user's existing exclusion. The new universe reader reports and excludes it,
  without editing old DataLake records.

### Safe next VPS test

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/ssh_smoke_test.py --date 2026-10-09
```

**This is read-only as far as the SSH preview is concerned.**
The test suite uses temporary local fixtures; do not start or restart
Chakra to run it. Review `git status --short` first: if it reports
uncommitted changes, stop before pull and inspect rather than resetting
working files. Paste the full test and preview output for review.

**Verification boundary:** GitHub commits and file contents were
confirmed. No VPS Python test output, IBKR callback/WAP sample, 1H data
coverage, real five-pattern signals, hourly task or Discord alert has
been verified in this session. The live five-minute job still follows
its legacy discovery path and the locked Reversal stock universe has
not yet been replaced. "Implemented" above means committed development
code, not deployed/activated.

**Open questions before activation:** approve the provisional per-source
ranking tie-breakers; verify `SPCX` IBKR stock eligibility; resolve
actual IBKR WAP callback and volume units; verify 1H warm-up data for
the selected list; agree numerical thresholds for all five scanner
setups. Do not guess or silently change these settings.

## Status

The user approved the workflow below. This document is the first deliverable in the new `RudraScanner` folder. Implementation is being drafted and tested; do not treat it as deployed until a new VPS log and actual output verify it. No live restart or live IBKR validation has occurred in this development session. Record actual commits, tests, activation and remaining gaps here as work proceeds.

## User-confirmed requirements

- Use **completed 5-minute candles** for all five setup detectors, EMA9, volume checks and indicator-based exits.
- Evaluate **LONG and SHORT** for every eligible ticker.
- Main inputs: **VWAP, EMA9, volume and price structure**. VWAP resets at the regular US session open.
- **4% is NOT a fixed discovery or entry requirement.** Scanner membership and pattern detection are different stages.
- Candidate discovery has exactly two named CSV inputs: an **AI list CSV** and an **IBKR scanner CSV**.
- AI researches and updates its CSV hourly. IBKR uses multiple scanner codes and creates its own CSV.
- Merge and deduplicate the two inputs, then feed their tickers to the existing data-import module.
- Use **IBKR** for 5-minute OHLCV and premarket data. Use **yfinance** for daily candles.
- Use the **existing common DataLake** and existing **five-minute Chakra job**. No separate scanner DataLake and no second five-minute scheduler.
- Each job performs **Git pull -> read CSV inputs -> discover/import -> calculate -> save -> Git commit/push**. All new scanner data and results belong in the common DataLake.
- Send the scanner result to **Discord each five-minute job**. Send an **AI review hourly**.
- The user can ask AI for the latest result at any time, or execute one `.py` file from SSH to print it.
- Output is a plain list, grouped into five sections, with ticker, LONG/SHORT and UK time. No dashboard is requested.
- Terminal, Discord and AI use the same saved mechanical result. AI may add sourced context but must not invent, silently change or recompute different technical signals.
- Keep existing Wicks and locked Rudra-Reversal strategy logic separate. No automated orders.

## Architecture

| Stage | Owner | Input | Output |
|---|---|---|---|
| AI discovery | Hourly AI research | Current web sources, market/sector context and latest saved scanner information | `ASJR_Analyst/config/ai_scanner_list.csv` |
| IBKR discovery | Five-minute Chakra job | Multiple market scanner codes | Common day's `raw/ibkr_scanner_list.csv` |
| Candidate merge | Existing import pipeline | Both CSV inputs | Deduplicated ticker universe with source labels |
| Data collection | Existing import pipeline | Tickers plus benchmark/sector ETFs | IBKR 5-minute/premarket data; yfinance daily data |
| Detection | RudraScanner logic | Completed candles, volume, context | Five LONG/SHORT setup lists plus data-quality status |
| Publication | Same Chakra job | Current run outputs | Common DataLake files committed and pushed to Git |
| Five-minute notification | Existing Discord sender | Saved scanner result | Same plain-list result, split into messages if needed |
| Hourly / on-demand review | AI | Git snapshot and recent signal history | Same technical list plus clearly separated current research |
| SSH | Standalone print script | Saved snapshot | Plain-list terminal output; no second data fetch |

The initial AI CSV can contain INTC as the user-required permanent monitor. This is not a claim of fresh research or a confirmed setup. Preserve INTC in the research list; other names must come from current discovery. Exclude penny stocks, BEAT and ONDS under existing user instructions. Unverified company quality must be marked, not guessed.

## Common DataLake and file contracts

**One data root:** `ASJR_Analyst/DataLake/YYYY-MM-DD/`, where the folder is the US trading-session date. Display times in `Europe/London`, 24-hour format; store canonical timestamps in UTC. Existing raw files remain compatible.

| Path | Contents |
|---|---|
| `ASJR_Analyst/config/ai_scanner_list.csv` | Canonical hourly AI-managed input; versioned in Git |
| `raw/ai_scanner_list.csv` | Exact AI rows used by this run, with freshness status |
| `raw/ibkr_scanner_list.csv` | IBKR candidates, scanner code, rank and scan time |
| `raw/scanner_status.json` | Success, empty result, timeout or failure per source |
| `raw/ibkr_gapup.csv` | Legacy compatibility output; no longer means a fixed 4% gate |
| `raw/intraday_5m.csv` | IBKR OHLCV, including premarket and required context ETFs |
| `raw/daily_30d.csv` | yfinance daily history; completed daily bars for context |
| `processed/scalp_radar_features.csv` | EMA9, session VWAP, volume comparisons, premarket levels and per-ticker data status |
| `processed/scalp_radar_rvol_profile.csv` | Small time-matched volume baseline and actual session count |
| `processed/scalp_radar.json` | Authoritative latest result, timestamps, input status and signal details |
| `processed/scalp_radar_history.jsonl` | Per-run history so AI can report the last hour without losing intervening signals |
| `reports/scalp_radar.txt` | Human-readable result used by terminal and Discord |

Private delivery state and reconstructible rolling-history caches may be gitignored outside the dated folders; they are implementation caches, not a second DataLake. All user-facing data-quality information, RVOL baselines and results must be published under the common root. The existing five-day cleanup must not destroy the 20-session reference needed for RVOL.

### AI CSV schema

` ticker,sector_etf,bias,catalyst,source_url,published_at_utc,researched_at_utc,expires_at_utc,quality_status,priority,enabled,reason `

- Uppercase, unique tickers. `bias` is LONG/SHORT/BOTH/WATCH research context; it must not override measured pattern direction.
- Research timestamps and expiration are mandatory for fresh research. A row with expired research cannot claim current news.
- Source URLs must support the actual claim. No source or insufficient evidence means UNKNOWN/UNVERIFIED.
- Use an explicit sector ETF when verified; unknown mappings remain unknown.
- Review liquid, established companies. Do not infer strong fundamentals just from price or volume.
- AI writes only its canonical CSV, preserving concurrent Git changes with a current file SHA. Chakra writes the run's used-input copy, never overwrites the AI-owned file.

### IBKR CSV schema

`ticker,scan_code,rank,scanned_at_utc`

Start with `TOP_PERC_GAIN`, `TOP_PERC_LOSE`, `HOT_BY_VOLUME`, `MOST_ACTIVE`. Validate availability and filters against the actual connected IBKR environment. Retain supported successful sources if another scanner fails, but clearly mark incomplete discovery. Keep per-code provenance even when a ticker appears in multiple scans. Apply liquidity/price filters; do not add a fixed +/-4% filter.

## Five-minute job and Git synchronization

1. Acquire a single-run lock. If a previous cycle is active, log an overlap skip; do not run concurrent writers.
2. Pull current `main` before reading the AI CSV. No force-push, history rewrite or automatic destructive cleanup. If sync fails, report that failure rather than claiming fresh inputs.
3. Read and validate the AI CSV. Run multiple IBKR scans and write the IBKR CSV with source status.
4. Merge tickers and source metadata; include benchmark/sector ETF requests for context, not as stock signals.
5. Fetch current IBKR candles; reuse/calculate daily context from yfinance. Exclude unfinished bars from detection.
6. Build indicators, data-quality checks and volume baselines. Bootstrap missing history in bounded requests so one job does not block indefinitely.
7. Evaluate all five patterns and save the authoritative result and history. Print the same text used for Discord.
8. Deliver Discord chunks through the existing sender. Acknowledge only successful sends; preserve failures for retry. Do not resend the same snapshot after restart, and do not present an old backlog as current entries.
9. Stage only this job's intended DataLake changes; commit, rebase on concurrent remote updates if safe, and push. Do not accidentally include unrelated staged work. Never append to an already-pushed tracked run log after the commit.
10. Record actual Git outcome, source health, pipeline version and timings. A successful local calculation is not proof that Git publication or Discord delivery succeeded.

The existing bot owns scheduling. Git pull updates files on disk; changed Python imports require the user's normal bot restart. Never restart the VPS or bot automatically. The external caller lives outside this repository and must be checked separately for sender integration.

## Data quality comes first

- Compare selected tickers' OHLCV, EMA9, VWAP and candle times with IBKR charts before live acceptance.
- Historical logs showed delayed IBKR candles. Show each signal's candle-close time and data age; block stale signals from appearing current.
- Separate MISSING, STALE, INCOMPLETE, UNVERIFIED and NO_PATTERN. Missing data is not “no setup.”
- Check unique ascending timestamps, valid OHLC, nonnegative volume, gaps and session coverage.
- Use exchange calendars for holidays, early closes and daylight-saving differences.
- VWAP must start at the regular-session open; premarket is stored separately. If the callback supplies only OHLCV, HLC3-weighted VWAP is an approximation and must be labelled. Exact trade/bar WAP needs an upstream callback enhancement.
- EMA9 uses 5-minute regular-session closes with historical warm-up. Document whether sessions carry over; do not silently change settings.
- RVOL compares cumulative IBKR volume through the same 5-minute endpoint with 20 prior complete regular sessions. Until 20 valid sessions exist, show the actual count and RVOL unavailable. Do not label a recent-bar ratio as RVOL20.
- Verify IBKR volume units; do not mix raw IBKR volume with Yahoo volume in a ratio or silently multiply by 100.
- Daily yfinance data is context, never a substitute for missing live 5-minute candles.
- A candle-only technical match is not proof of executable spread, short borrow or reviewed fundamentals. Expose missing checks.

## Five setup sections

Public SMB descriptions guide the design; proprietary scanner internals are unavailable. Our 5-minute conversion and numerical thresholds require independent testing.

| Section | LONG concept | SHORT concept |
|---|---|---|
| Hitchhiker | Opening drive, tight hold near highs, continuation break | Opening selloff, tight hold near lows, continuation break |
| Back$ide | Stabilization, higher low/high, EMA9 hold, reversal toward VWAP | Lower high/low, EMA9 rejection, reversal toward VWAP |
| Rubberband | Extended selloff accelerates in range/volume, then strong snapback | Extended rally accelerates in range/volume, then sharp reversal |
| Second Chance | Break resistance, quieter retest holds, renewed demand | Break support, quieter retest fails, renewed selling |
| Fashionably Late | Rising EMA9 crosses above VWAP after recovery | Falling EMA9 crosses below VWAP after deterioration |

Confirm entries only on completed 5-minute candles. Distinguish a forming pattern from confirmation. Mirror LONG/SHORT conditions consistently. Require market -> sector -> ticker context; mixed context means WAIT. Keep the user's existing after-first-30-minutes entry restriction unless explicitly revised; early Hitchhikers can be watch-only.

Define and test causal pivots, structural levels, invalidation, entry/stop/objective references, duplicate suppression and re-arming. Do not label a ranking score as a win probability or reuse SMB performance claims for our adaptation. Locked Rudra-Reversal rules remain unchanged.

## Alert and on-demand contract

Example layout only; these are not live signals:

```text
RUDRA RADAR | 5M | YYYY-MM-DD HH:MM UK
Data status: FRESH / PARTIAL / DATA NOT READY

HITCHHIKER
TICKER | LONG | HH:MM | Price | VWAP | EMA9 | RVOL

BACKSIDE
...

RUBBERBAND
...

SECOND CHANCE
...

FASHIONABLY LATE
...
```

- Discord: scanner output each five-minute run; no repeated identical snapshot; overflow sent in the same run.
- AI hourly: read current Git snapshot plus the preceding hour's history, show the same technical facts, research catalysts and update the AI CSV for subsequent cycles. Clearly separate new research from the current snapshot's input vintage.
- AI on request: find the latest actual available snapshot, show its time/status, and report unavailable/stale data honestly. Do not substitute web quotes for mechanical scanner results.
- SSH: print the saved snapshot; label an old snapshot historical/stale. No independent scheduler, hidden data fetch or notification side effect.

## Implementation and acceptance plan

1. Audit actual sources and callback fields; compare sample data to IBKR charts.
2. Implement both CSV contracts, multi-scanner discovery and input union.
3. Extend the existing import/DataLake pipeline with EMA9, VWAP, premarket levels, live context and time-matched volume history.
4. Implement/test the five 5-minute LONG/SHORT detectors and shared plain-list result.
5. Test replay, missing/late data, incomplete candles, session boundaries, duplicates, retry and existing-strategy compatibility.
6. Publish code and instructions to Git. Configure a dedicated hourly AI research/report task without silently replacing unrelated Rudra-Research/Jaguar tasks.
7. User pulls/installs requirements and restarts via the normal Discord controls. Verify a new runtime-version log, published snapshot, AI CSV refresh and real Discord arrival before claiming activation.

## Sources and existing assets inspected

- Existing pipeline: `ASJR_Analyst/Tests/test_asjr_pipeline.py`
- IBKR adapter: `ASJR_Analyst/Utils/asjr_ibkr.py`
- Daily adapter: `ASJR_Analyst/Utils/asjr_yfinance.py`
- Existing delivery: `ASJR_Analyst/Utils/asjr_alerts.py`
- Git helper: `ASJR_Analyst/Utils/asjr_git.py`
- Latest inspected saved DataLake date: 2026-10-09. Saved 5-minute file contained 106 tickers; pipeline requested three days. Sample replay had only two complete prior sessions for RVOL and lacked required intraday benchmark/sector data. These are coverage findings, not performance results.
- SMB public guides: https://www.smbtraining.com/cheatsheets
- IBKR scanner API: https://www.interactivebrokers.com/docs/tws-api/doc/market-scanner/introduction
- yfinance download: https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html

## Change record

- 2026-10-10: User chose 5-minute candles, LONG/SHORT, VWAP/EMA9/volume, plain-list SSH output, AI hourly CSV discovery, multiple IBKR scanners without fixed 4%, common DataLake, Git pull/push each five-minute Chakra cycle, Discord every cycle, hourly AI review and on-demand access.


## Phase 1 implementation record — 2026-10-10

**Committed to main; development only, not active in Chakra.** This section
documents what was actually added, and must be extended after every later
RudraScanner discussion, change, test, or activation. GitHub remains the
canonical handoff. Never silently treat planned phases as deployed.

### New files

- `RudraScanner/__init__.py` — identifies the isolated scanner package.
- `RudraScanner/discovery.py` — strict AI CSV reader with expiration and
  evidence/freshness handling; four IBKR scans
  (`TOP_PERC_GAIN`, `TOP_PERC_LOSE`, `HOT_BY_VOLUME`, `MOST_ACTIVE`)
  with per-code SUCCESS/EMPTY/TIMEOUT/ERROR and provenance; deduplication
  without any fixed percent-move gate.
- `RudraScanner/storage.py` — opt-in `save_discovery(app, trade_date,
  repo_root=...)` saves input copy, IBKR CSV, statuses and candidate union
  under the existing day DataLake. This does **not** replace the live pipeline.
- `RudraScanner/print_saved.py` — SSH read-only display of a saved report,
  or DATA NOT READY when the detector has not published a report.
- `RudraScanner/tests/test_discovery.py` — offline tests covering AI input
  validation, stale/duplicate/excluded tickers, IBKR scan status/filters,
  candidate union and DataLake paths; `tests/__init__.py` for discovery.
- `ASJR_Analyst/config/ai_scanner_list.csv` — initial INTC permanent
  WATCH row, explicitly UNVERIFIED, no fabricated catalyst or research dates.

### Operational and verification status

- **Not connected to** `run_asjr_manual_pipeline`, the five-minute Chakra
  caller, Git pull/push orchestration, Discord, or any automated AI task.
- **No live IBKR, VPS or Discord checks performed.** Tests committed as source,
  **not yet executed in a verified Python runtime**. Do not claim green tests.
- Inherited IBKR starting filters from existing ASJR:
  minimum USD price 5, average volume 1,000,000, market cap 500 million,
  `STK.US.MAJOR`, `CORP`, maximum 50 rows per scan. These are
  **provisional existing settings**, not newly user-approved thresholds.
- Original pipeline still uses the old +/−4% mover adapter and performs Git
  pull in `submit_datalake` after collection. Neither path was changed.
- The authoritative five-pattern detectors, 20-session RVOL,
  minute freshness, benchmark/sector feeds, safe five-minute integration,
  per-event delivery acknowledgements, hourly AI task, and live deployment
  remain **unimplemented**.

### Test command (for a developer, not the live scheduler)

```bash
cd /root/trading/ASJR
/root/trading/venv_new/bin/python -m unittest RudraScanner.tests.test_discovery -v
```

### Open decisions: ask the user, do not assume

1. Confirm or revise the inherited IBKR price/volume/market-cap filters and
   acceptable candidate cap before activating multi-scan in Chakra.
2. For EMA9, confirm whether regular-session 5-minute values carry across
   prior trading sessions or restart at each 09:30 ET open.
3. Confirm how to develop/lock numerical thresholds for all five setups
   (research-only candidates vs active alert thresholds); definitions are
   conceptual and have not been backtested or approved.
4. Verify source-specific callback fields, sector ETF mapping, VWAP source,
   delayed bars and real runtime volume units before enabling alerts.

### Next safe steps

Execute offline tests and fix any failures; audit connected IBKR callbacks;
then add indicators / RVOL and replay tests. Do not hook into production
or restart the bot until the unresolved settings are confirmed and outputs
are verified. Keep this README and `ASJR_Analyst/OPERATIONAL_HANDOFF.md`
consistent after every material change.

## Confirmed setting — 2026-10-10 (user decision)

User explicitly approved retaining the inherited IBKR scanner discovery filters:

- Stock price above USD 5 (`usdPriceAbove=5`).
- Average volume above 1,000,000 (`avgVolumeAbove=1000000`).
- Market capitalization above USD 500 million (`marketCapAbove1e6=500`).
- 50 results per scanner code (`numberOfRows=50`).
- Existing `STK.US.MAJOR` / corporate-stock-only scope stays as implemented.

These are **discovery filters**, not a percentage-move threshold or entry rules.
Do not re-ask this decision unless the user requests a change or real IBKR
validation reveals a technical incompatibility. Production activation and
live IBKR validation remain pending.

## Confirmed EMA9 continuity — 2026-10-10 (user decision)

The user confirmed **continuous 5-minute EMA9 across days** with premarket
bars included. **Do not reset EMA9 at 09:30 ET or at calendar/session
boundaries.** Carry the previous observed EMA through each subsequent
completed 5-minute bar, including extended-hours data the IBKR import
actually provides. Use all real available bars sorted chronologically
per symbol; do not manufacture missing 5-minute overnight or market-closed
candles. Include postmarket/overnight bars if the upstream feed contains them.

The indicator computes EMA9 from the oldest available preceding 5-minute
bar (with explicit history/warm-up status) and updates it only on completed
bars. Any missing or late bars must be surfaced rather than silently
asserting the stream was gap-free. Input integrity and freshness still
govern tradability.

**VWAP is separate:** retain the previously agreed regular-session
VWAP reset at the US RTH open. Continuous EMA9 does **not** imply
continuous VWAP. VWAP's price/volume source remains to be confirmed
against the actual IBKR callback before live activation.

The continuous EMA9 implementation belongs in the isolated scanner,
not in legacy Wicks or the locked Rudra-Reversal modules.

## Continuous EMA9 — implementation record (2026-10-10)

- Added `RudraScanner/ema9.py` with `build_continuous_ema9(raw, now=...)`.
  Accepts existing raw `Ticker,Date,Open,High,Low,Close,Volume` DataLake
  frames or normalized equivalents. Converts timezone-aware US exchange bar
  starts to UTC; exposes `Europe/London` time and session labels.
- For each ticker: sort real available 5-minute candles, discard incomplete
  or invalid bars, remove timestamp duplicates with a diagnostic count;
  apply `ewm(span=9, adjust=False)` across **all** real observed
  completed bars, including premarket, RTH, postmarket or overnight when
  returned by IBKR. No new-session reset and **no synthetic gap fill**.
- A valid EMA9 value requires at least nine observed completed bars for
  `ema9_ready` to become true. Do not fire live signals on unready EMA9.
  The existing 3-calendar-day IBKR historical request may supply fewer
  prior bars following holidays/connection gaps; this must be checked in
  live coverage tests. `prior_gap_minutes` exposes gaps in the actual feed.
- Added `RudraScanner/tests/test_ema9.py` for prior-Friday to Monday
  premarket/RTH carry, multi-ticker independence, real gap preservation,
  duplicate/invalid/unfinished diagnostics and rejecting timezone-naive bars.
- These are **committed source and test cases, not executed results**.
  No connected IBKR/Gateway access or live Python/test runtime was used.
  Nothing in the live ASJR pipeline or its EMA20/Wicks/Reversal logic changed.
- VWAP remains RTH-reset and still requires independent source/volume
  verification. This EMA module is not yet part of Chakra's execution.
- Offline test command:
  `/root/trading/venv_new/bin/python -m unittest RudraScanner.tests.test_ema9 -v`

The former open decision about EMA9 session reset is **resolved** by the
user: continuous, across days, including premarket. Do not re-ask.

## Indicator clarification — 2026-10-10

User reiterated: **RudraScanner uses EMA9 AND VWAP together** for pattern
analysis; this is not a choice between indicators. The previously confirmed
continuous five-minute EMA9 (including available premarket/extended-hours
bars, no daily reset) remains unchanged. The previously confirmed
**regular-session VWAP reset at 09:30 ET** remains unchanged.

**Still unresolved**: for VWAP, whether to extend the IBKR callback to
capture each historical bar's actual WAP (preferred when available), or use
an explicitly labelled HLC3×volume approximation from existing OHLCV.
Do not silently select one or claim actual WAP without checking the upstream
callback. No live bot changes made from this clarification.

## Shared DataLake ownership — 2026-10-10 (explicit user decision)

**The ASJR DataLake is common to all modules, including Rudra-Reversal and
RudraScanner.** It is not RudraScanner's private store, and no second DataLake
folder or competing five-minute collector may be introduced.

**Canonical shared day root:** `ASJR_Analyst/DataLake/YYYY-MM-DD/`
(one US trading-session date per folder). Keep existing common
`config/`, `raw/`, `processed/`, `reports/` subfolders.

- Shared collected inputs: `raw/intraday_5m.csv`, daily OHLCV,
  benchmark/sector context, and additional timeframes when available
  (including 1H for Rudra-Reversal), with common consistent ticker/time
  semantics. Collect a given feed once and let relevant modules read it.
- RudraScanner owns its namespaced derivative outputs
  (`processed/scalp_radar_*.csv`, `processed/scalp_radar*.json*`,
  `reports/scalp_radar.txt`) but they live *inside the shared day root*.
- Rudra-Reversal remains a separate strategy and can own separate
  reversal-specific derivative outputs *inside that same root* when
  integrated. Do not overwrite the shared raw feeds, other modules'
  outputs, or Reversal's locked strategy signals.
- Git pull/read/fetch/process/commit/push remains one existing Chakra job.
  Writes need module-scoped, non-colliding filenames and accurate freshness,
  source provenance and timeframe. No second scheduler or Git writer.
- Scanner 5M and Reversal 1H cannot assume one data interval substitutes for
  the other; publish a status if a required source/timeframe is missing.
- RVOL history/rolling data and historical 1H warmup must survive the
  five-day DataLake cleanup (reference store or published eligible history
  inside the common system; do not silently delete needed baselines).

**Audited current Reversal code:** `ASJR_Analyst/Strategies/RudraReversal1H/
rudra_reversal.py` already searches the requested day's shared
`DataLake/YYYY-MM-DD/raw/` for 1H input first (including
`intraday_1h.csv`, `hourly_1h.csv`), then falls back to
`Backtesting/BacktestData/IBKR/MarketData/1h/`; NQ currently uses a separate
Yahoo Finance 1H file. This is its *current source fallback*, not a newly
verified common 1H ingestion pipeline. Before claiming full shared-DataLake
operation, implement/verify a proper common 1H input, while preserving
the existing NQ/Yahoo source requirement and Reversal's locked calculations.

The user also accepted using actual IBKR historical-bar **WAP** for
RudraScanner VWAP (rather than an unlabeled HLC3 approximation). Retain
actual WAP with the shared 5M feed when upstream callbacks are enhanced,
so all consumers can access the same raw measurements. Existing saved
5M OHLCV without WAP must be labelled **WAP_MISSING** for exact VWAP,
not silently treated as exact WAP. EMA9 remains continuous across available
completed bars; VWAP resets at US RTH open.

**Status:** shared architecture agreed; Reversal source fallbacks confirmed by
code inspection; common 1H collection, actual WAP callback integration,
runtime tests and production deployment are not yet verified. Do not restart
or change live Wicks / Reversal while implementing these stages.

## Shared ticker-universe clarification and Phase 1 extension — 2026-10-10

**User-confirmed:** both RudraScanner and Rudra-Reversal should consume the
current ticker discovery idea **and the existing fixed watchlist**. Their
signals/indicators/timeframes must remain separate. This clarifies the earlier
"two CSV inputs" design: there are **two dynamic discovery feeds** (AI CSV +
IBKR scanner CSV), plus the **already-existing day-specific fixed list**.
Do not create another independently researched third ticker CSV.

The common ticker inputs for both US-stock strategies are:

1. Existing `DataLake/YYYY-MM-DD/config/fixed_watchlist.csv`
   (prepared/copied by the existing ASJR day-bootstrap, including manual edits).
2. AI-managed `ASJR_Analyst/config/ai_scanner_list.csv`.
3. IBKR multi-code `raw/ibkr_scanner_list.csv`.

Deduplicate by ticker, preserve FIXED/AI/IBKR source labels and each IBKR
scan code, and publish the single list at
`DataLake/YYYY-MM-DD/processed/scalp_radar_candidates.csv`. Both strategies
should eventually use this *same eligible stock list* and shared historical
imports. The 5M Radar detector does **not** replace the locked 1H
Rudra-Reversal BB detector. NQ uses its existing independent Yahoo Finance
1H route as a non-stock Reversal extension; do not silently drop it.

**Added code (committed to main):**
- `RudraScanner/universe.py`: read/validate enabled daily fixed rows,
  merge with AI+IBKR candidate provenance, and output
  `common_tickers(rows)`. Missing fixed files are explicitly MISSING;
  they are never silently replaced with a guessed list.
- `RudraScanner/storage.py` updated: saves the shared three-origin
  candidate CSV and includes fixed list health/exclusions in
  `raw/scanner_status.json`.
- `RudraScanner/tests/test_universe.py`: tests fixed-only names, overlap,
  disabled names, explicit exclusions, duplicates, missing fixed source,
  source provenance and saved artifacts.

**Known conflict found in the actual October 9 fixed CSV:** `ONDS` is
enabled there, but the user previously explicitly excluded `ONDS` (also
`BEAT`). The development shared-universe reader excludes and **reports**
such conflicts, preserving the existing historical fixed CSV unchanged.
If those exclusions are reversed, ask the user explicitly; do not infer
from an old enabled fixed row. Other enabled fixed-list tickers remain
candidates even if absent from both dynamic discoveries.

**Important activation boundary:** the *shared candidate-generation code*
now exists, but the production Reversal source still has its original
`STRATEGY_TICKERS` and uses 1H sources with fallback caches. We have
**not** changed that hardcoded live strategy ticker list, configured 1H
imports, Chakra schedule or Wicks alerts. First validate 1H availability
for the combined eligible list (150+ completed 1H bars per ticker),
performance and existing Reversal compatibility. Then integrate the one
shared universe as a controlled deployment, retaining existing NQ Yahoo
feed and locked BB rules. The complete tests for this extension have been
committed but **not verified as executed on VPS**. Attempted isolated
external checkout could not reach GitHub, so do not claim test success.

## Locked shared-universe size — 2026-10-10 (user decision)

**Maximum 30 DISTINCT US-stock tickers total** for the common
RudraScanner + Rudra-Reversal workflow:

| Source bucket | Maximum chosen unique tickers |
|---|---:|
| Existing daily FIXED list | 10 |
| AI hourly research CSV | 10 |
| IBKR multi-code scanners | 10 |
| **Total** | **30** |

- The cap is applied **before 5-minute and 1-hour IBKR historical imports**.
  Discovery can return more source rows; do **not** import them all.
- Source priority for avoiding duplicates is FIXED → AI → IBKR. If a
  ticker appears in multiple sources, it is counted only once against
  the earliest source bucket. Look farther down the *same* source for
  the next distinct eligible name.
- A source with fewer than 10 eligible nonduplicate names contributes
  fewer: never borrow unused quota from another source.
- Both strategies receive the exact same selected US-stock symbols.
  Rudra-Reversal's existing separately fetched Yahoo `NQ` is a distinct
  non-stock research instrument and remains outside this 30-stock cap.
- Wicks/other legacy modules are not silently changed by the new cap
  until integration is reviewed. This is the *new shared-scanner/reversal*
  selection policy, not a claim that live legacy imports are already limited.
- INTC's existing user-mandated permanent monitor is ranked first
  within the fixed bucket when present. The existing fixed-list
  OPEN POSITION notes are considered before general fixed names,
  and remaining fixed candidates follow the user-supplied CSV order.
- Initial deterministic **development ranking pending user confirmation**:
  AI rows: smallest numerical `priority` (then research freshness);
  IBKR: number of distinct scan codes (then best in-code rank).
  These are observable selection orderings, not calculated success
  probabilities or guarantees of fundamentals. They do not constitute
  an independently validated 'most eligible' ranking.
- The selected shared CSV exposes `selection_source` and full
  `sources` provenance separately. `raw/scanner_status.json` now
  records `selected_total`, per-source counts and unused quotas.
- `RudraScanner/universe.py` now enforces the cap in
  `merge_shared_universe()` and `load_shared_universe()`; it
  refuses configurations greater than 10 per source.
- `RudraScanner/storage.py` updated for the selection status and
  selection source. New offline test file:
  `RudraScanner/tests/test_selection_caps.py` tests 30-ticker cap,
  duplicate slot handling, unused quota, mandatory fixed monitors,
  and exclusions.

**Current state:** new code committed on `main`, but offline
tests have **not been executed in a verified runtime**. The live
Reversal `STRATEGY_TICKERS`, 1H data importer and Chakra caller have
**not been rewired**. Do not claim the live bot is limited to 30.

**Open ranking decision:** user said 'most eligible' and 'do not
assume'. Before activating, confirm whether these transparent
source-order / AI-priority / IBKR-consensus tie-breakers are preferred,
or whether a different eligibility/ranking rule should be used.
Do not invent missing liquidity, fundamentals, spread or catalyst data.

The 1H Reversal strategy needs >=150 completed 1H bars per included stock.
Tickers with insufficient history must be labelled DATA NOT READY,
not quietly dropped with a false no-signal claim.

## First sourced AI CSV refresh + SSH input smoke test — 2026-10-10

**User request:** update the AI-managed CSV from current web research so
the user can test from SSH. Work was completed and committed to `main`;
it is not a claim that automatic hourly refresh, live IBKR scanning or
production alerts are running.

### AI CSV research snapshot

Updated `ASJR_Analyst/config/ai_scanner_list.csv` with exactly
**10 distinct Friday 2026-10-09 news candidates**, plus the permanent
INTC monitor already carried in the fixed watchlist. Eleven CSV rows
does **not** mean 11 AI-selected slots: selection quotas skip overlap,
so INTC will count against the FIXED bucket and the 10 other eligible
names fill the AI bucket when the October 9 fixed list is used.

- `INTC`: permanent WATCH, explicitly unverified, no false research time.
- `SPCX`: SpaceX telecom spectrum expansion; sector ETF classification
  unverified; LONG research context only.
- `PLTR`: positive analyst coverage (Goldman and Barclays).
- `LITE`: CEO discussed exceptional demand for AI optical products.
- `AMT`: telecom tower infrastructure repricing after SpaceX news.
- `HUM`: Medicare Advantage quality star rating recovery.
- `AMZN`: AWS/AI and large-cap consumer rebound research.
- `TMUS`: incumbent mobile carrier weakness amid spectrum competition.
- `AAPL`: supplier-order report suggesting soft iPhone Pro demand.
- `JPM`: upcoming October 13 bank earnings (event risk, not a trade).
- `NVDA`: volatile AI infrastructure sentiment after competing reports.

Each news row contains a direct article link, `researched_at_utc =
2026-10-10T09:23:11Z`, and `expires_at_utc =
2026-10-12T12:00:00Z` (before Monday's regular open). Where a publisher
exposed an **exact** article time, `published_at_utc` is recorded.
Where only its calendar date was established, `published_at_utc`
is deliberately blank, never fabricated; read_ai_csv reports this as a
PARTIAL provenance warning. All rows have `quality_status =
UNVERIFIED` because comprehensive fundamental eligibility has not been
independently established. These rows are **research watch candidates,
not mechanical LONG/SHORT signals**. Candidates may be extended; wait
for price/volume/EMA9/VWAP/structure confirmation.

The source URLs are embedded in the CSV. Research was performed on
Saturday after the October 9 US close; no market-current 5M data
or executable entries are claimed. There is **no active automatic
hourly research task created by this update**. A future premarket
AI refresh must replace/expire old research rather than promoting it
as fresh.

### Read-only SSH test (new file)

Added `RudraScanner/ssh_smoke_test.py`. Reads the existing AI CSV,
October 9 fixed watchlist, and *optional previously saved* IBKR scanner
CSV. Reports validation/freshness, excluded fixed names, and FIXED/AI/
IBKR selected-count summary, with the hard 30-stock cap. It **does not**
connect to IBKR, call the live bot, alter the DataLake, send messages,
commit or push. It labels a missing IBKR CSV `NOT_YET_SAVED`.

Execute on the user's VPS:

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/ssh_smoke_test.py --date 2026-10-09
```

**Expected selection model, not a verified runtime result:**
up to 10 FIXED, 10 AI, and 0 IBKR until a multi-code scanner CSV
is actually saved; never mislabel zero IBKR rows as a successful scanner
run. The October 9 fixed file has 19 rows, one excluded ONDS, and
the first ten selections include INTC and the two existing "OPEN
POSITION" labels. Missing timestamp provenance warnings are expected.

**Status update after user testing:** commits and GitHub file existence verified; SSH input smoke test now observed on VPS and passed (20/30). The separate full unittest command and live IBKR/Discord delivery have *not been observed or verified*. If Git reports a conflict or dirty state,
do not force-reset or restart the bot. Show the output for diagnosis.
Continue to avoid editing locked Reversal/Wicks logic.

## Next task queued — Chakra bot-method integration (2026-10-10)

**User's stated sequence:** they will run the prepared SSH tests first; **after
reviewing the results, the next implementation task is integration into the
existing Chakra five-minute bot method.** This is a requested next stage,
NOT authorization to deploy or restart the bot before test verification.

Integration checklist for that next task:

1. Review actual SSH unittest and `ssh_smoke_test.py` output; fix failures,
   stale AI inputs or eligibility issues before live wiring.
2. Audit the production entry point `run_asjr_manual_pipeline(app, ...)`
   and its external VPS caller at
   `/root/trading/utils/trading_sudarsan_chakra.py`. Preserve existing
   Wicks and locked 1H Rudra-Reversal delivery.
3. Within the **same existing five-minute cycle** use one Git pull before
   input reads, the confirmed FIXED 10 + AI 10 + IBKR 10 shared stock
   selection, and bounded common DataLake imports (IBKR 5M and needed
   1H, Yahoo daily, NQ Yahoo 1H). No new scheduler or competing importer.
4. Validate completed candles, continuous premarket-inclusive EMA9,
   RTH-reset VWAP from actual IBKR bar WAP, source volume units,
   session/sector context, data freshness, and required Reversal 1H warmup.
5. Only after the five LONG/SHORT setup definitions, thresholds, and replay
   tests have been reviewed: publish authoritative scanner results to the
   common day DataLake, feed the same saved text to Discord, hourly AI
   review and SSH reader, and safely Git commit/push in the single job.
6. Implement idempotent Discord delivery with acknowledgement/retry
   and separate strategy state. Make all new scanner behavior opt-in or
   feature-gated until observed live checks pass.
7. Run dry-run/replay and integration tests before user-controlled pull/
   bot restart. Verify loaded version, current Git snapshot and delivered
   Discord payload rather than assuming successful activation.

**Latest status: USER VPS INPUT SMOKE TEST VERIFIED (20/30); full unit tests PENDING; BOT INTEGRATION NOT STARTED.**
Do not mistake the isolated package or the new task entry for deployed
production code. Keep this status current after the user's test.
