# RudraScanner — canonical instructions and implementation plan

Updated: 10 October 2026, Europe/London.

**Read this document first in every future session.** Repository: `raghunathbhandari/ASJR`, production branch `main`. Operational history: `ASJR_Analyst/OPERATIONAL_HANDOFF.md`.

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
