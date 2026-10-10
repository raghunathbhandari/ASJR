# RudraScanner — canonical instructions and implementation plan

Updated: 10 October 2026, Europe/London.

**Read this document first in every future session.** Repository: `raghunathbhandari/ASJR`, production branch `main`. Operational history: `ASJR_Analyst/OPERATIONAL_HANDOFF.md`.

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

**Status:** commits and GitHub file existence verified. SSH commands,
unittest results, and live IBKR/Discord delivery have *not yet been run
or observed by the assistant*. If Git reports a conflict or dirty state,
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

**Current status: PENDING SSH TEST OUTPUT; BOT INTEGRATION NOT STARTED.**
Do not mistake the isolated package or the new task entry for deployed
production code. Keep this status current after the user's test.
