# RudraScanner — Current State / Start Here Next Session

**SSH manual scan implementation added later on Saturday 10 October.**
**NOW EXISTS:** [`scan_now.py`](scan_now.py) and
[`SCAN_NOW.md`](SCAN_NOW.md). Unlike
`print_saved.py` and `live_status.py`, the new CLI
writes a local **request for the next existing 5-minute Chakra
cycle** and can wait to print its actual saved 5M report.
It does NOT create a separate IBKR connection and does
NOT trigger an independent instant broker scan.
The existing pipeline version advanced to
`2026.10.10.13`, with atomic request ACK after its
original scanner/5M/1H sidecar completes. Local
requests are excluded from Git; normal DataLake
reports still follow the existing Git workflow.
The extra **10 offline regression tests have been
committed but NOT YET VERIFIED ON VPS**. Previously
confirmed 83/83 PASS; **93/93 expected after pull,
not yet observed**. User must pull, retest, and
reload existing Chakra before the SSH request can
be consumed. On Saturday `scan_now.py` intentionally
returns `MARKET SESSION CLOSED` (no broker work).
Monday scanner Discord remains OFF; AI research
expiry is unresolved.

**As of Saturday 10 October 2026, after 13:38 UTC.**
This is the **current checkpoint**, superseding older progress
blocks lower in the README and handoff documents.

## Verified and user-confirmed

- **Existing IBKR infrastructure is already working.**
  The user explicitly confirmed the existing **IBKR Gateway
  connection, scanner/data discovery and OHLC data imports
  are importing correctly in OTHER ASJR/Chakra tasks**.
  **Do not propose another Gateway, separate login,
  new connection, port change, client ID, replacement bot
  or reimplementation of basic market-data callbacks.**
  The new scanner must reuse the **same connected IBKR app**
  and existing 5-minute Chakra pipeline.
  These are user-confirmed operational facts about the
  EXISTING tasks, **not evidence that RudraScanner's four
  newly added codes have each completed live**.
- **User VPS confirmed full 83/83 offline tests PASS**
  (10 Oct 2026 13:30 UTC; `Ran 83 tests in 0.887s; OK`)
  after pulling GitHub main through `2d1ee811`.
  Previously failed test mock cases were fixed; the
  actual safety gate was preserved.
- **Monday Oct 12 2026 read-only preflight** returned
  `ready_to_shadow=true`, `scheduled_mode=shadow`,
  `research_enabled=true`, `alerts_enabled=false`,
  `thresholds_approved=false`. It checked source
  configuration and legacy hooks only, performing
  **zero broker requests, zero orders, zero Discord sends**.
- Monday fixed CSV exists:
  `ASJR_Analyst/DataLake/2026-10-12/config/fixed_watchlist.csv`;
  byte-for-byte Friday copy, **19 configured names**.
  New RudraScanner fixed-source filter finds
  **18 eligible / PARTIAL**, because `ONDS` is excluded.
  Shared scanner selection is **up to 10 fixed names**;
  the separate legacy Wicks watchlist is not overwritten.
  Permanent `INTC` included. Existing `AKAM` and
  `WTTR` open-position watch notes preserved,
  but do not infer that those positions are still held.
- Friday Oct 9 historical IBKR WAP research was performed:
  40 instruments, 22,290 genuine historical 5-minute WAP
  bars; 11 provisional pattern labels but **10 distinct
  entries**, 4 positive / 6 negative, average 30-minute
  hypothetical markout **+0.0147% before costs**.
  Retrospective, hindsight-selected: **not a live edge**.

## Implemented in GitHub and VPS checkout; pending live run

- Monday `2026-10-12` runtime config in
  `ASJR_Analyst/config/rudra_scanner_runtime.json`
  schedules **SHADOW** research.
- Same Chakra pipeline imports old Wicks and locked
  Rudra-Reversal first, then four extra IBKR scanner
  queries: `TOP_PERC_GAIN`, `TOP_PERC_LOSE`,
  `HOT_BY_VOLUME`, `MOST_ACTIVE`.
- Source caps: **10 FIXED + 10 AI + 10 IBKR = 30
  unique stocks maximum**, not a guarantee all 30
  will be populated. No universal 4% threshold.
- Same connected IBKR app; new sidecar reuses
  existing 5-minute OHLCV/WAP where available and
  requests only missing selected stocks plus
  SPY, QQQ and evidenced sector ETF benchmarks.
  Exact WAP-based RTH VWAP, continuous EMA9,
  historical 20-full-prior-RTH-session RVOL20,
  five experimental patterns and index-to-sector
  as-of-candle gate are implemented in code.
  New stock 1-hour data uses same app and a
  throttled separate DataLake cache. Locked 1-hour
  Rudra-Reversal symbols, NQ Yahoo source and
  Wicks/alert state remain unchanged in SHADOW.
- Data/report files use the one common daily
  `ASJR_Analyst/DataLake/YYYY-MM-DD/` plus Git.
  SSH status: `/root/trading/venv_new/bin/python
  RudraScanner/live_status.py --date 2026-10-12`.
  The script **reads saved files ONLY**, does not
  contact IBKR/start a scan. Repeated Saturday checks
  correctly returned `NOT SAVED YET`.
- Experimental Scanner Discord is **OFF** while
  `alerts_enabled=false` and
  `thresholds_approved=false`. There are **no
  new orders**. Scanner alert queue/deduplication
  state is separate from Wicks and Reversal.

## Outstanding / do not assume completed

1. The existing **IBKR system works**, per user,
   but the **new four scanner-code results, WAP
   capture in Monday's running process, benchmark
   timing, selected extra 5M/1H historical imports,
   Git-written scanner report, Discord bridge
   behaviour and actual per-cycle pacing** still
   need **RudraScanner-specific live evidence**.
2. Git pull/test success does **not** verify that
   the **running long-lived Chakra Python process
   has reloaded version `2026.10.10.12`**.
   User controls bot restart via the existing
   Discord `!mbdstop` / `!mbdstart` workflow.
   Do not start a second Gateway or scheduler.
3. AI CSV: **10 research rows expire on Monday
   12 Oct at 12:00 UTC / 13:00 UK BST**.
   Monday-open preflight found **only one valid
   AI candidate (`INTC`, permanent unverified WATCH)
   which overlaps the fixed list**. Thus fresh
   independent AI names may be **zero** and a full
   30/30 is **not** supported. No automatic
   hourly AI-to-GitHub CSV writer was successfully
   scheduled: task creation hit the five-active-task
   account limit. Existing Rudra-list reporting
   is **not equivalent** to updating this CSV.
   Research and commit current evidence rather than
   extending expiry or reusing stale Friday catalysts.
4. Setup detector minimum warm-up is 15 complete
   RTH 5-minute bars (75 minutes) in the Friday
   evaluation, in addition to the initial 30-minute
   guard. Do not expect a valid early pattern
   from the first 30 minutes just because
   other legacy data feeds already work.
5. External VPS launcher
   `/root/trading/utils/trading_sudarsan_chakra.py`
   is not in this GitHub repo; review real
   process log/callback compatibility rather than
   claim it was audited.

## How to resume — minimum verification

**No new IBKR connection.** First inspect whether
Chakra is running current version and has reloaded
after pull. In a genuine Monday US market run,
check the saved report only after the existing
5-minute job runs:

```bash
cd /root/trading/ASJR
/root/trading/venv_new/bin/python RudraScanner/live_status.py --date 2026-10-12
/root/trading/venv_new/bin/python RudraScanner/print_saved.py --date 2026-10-12
```

Expect actual dated `raw/scanner_status.json` with
four per-code states, `raw/ibkr_scanner_list.csv`,
`processed/scalp_radar_candidates.csv`,
`reports/scalp_radar.txt`,
`reports/rudra_scanner_live_status.json` and
`raw/rudra_scanner_hourly_status.json`.
Inspect genuine IBKR data timestamps, selected source
counts, WAP and ETF completeness, RVOL20 availability,
pattern WAIT/LONG/SHORT diagnostics, Git sync and
unchanged Wicks/locked Reversal alerts. Mark individual
missing data sources `NOT READY` rather than
manufacture successful scans.

**Monday US regular session 09:30–16:00 EDT
= 14:30–21:00 BST** on 12 October 2026.
For a practical first assessment, inspect after
enough RTH candles have closed, not just at open.

**Acceptance:** code and offline tests passed;
live RudraScanner **SHADOW run remains unverified**;
Scanner Discord pattern alerts remain OFF until
specific approval after live evaluation.

Related canonical references:
- `RudraScanner/README.md`
- `RudraScanner/MONDAY_LIVE.md`
- `ASJR_Analyst/OPERATIONAL_HANDOFF.md`
