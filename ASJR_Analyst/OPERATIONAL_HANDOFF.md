# ASJR Analyst operational handoff

Updated 2026-10-10 (UK). This records the implementation and observed state for Rudrakchhya and future ASJR sessions. Check the current Git branch, VPS logs and today's DataLake files before treating a run as live-verified.

## LATEST ASJR / RUDRASCANNER STATE — 2026-10-10, after 13:38 UTC

**READ FIRST NEXT SESSION:**
[`RudraScanner/CURRENT_STATE.md`](../RudraScanner/CURRENT_STATE.md)
(specific implementation/test/deployment checklist).
This entry supersedes outdated statuses elsewhere in this
long historical handoff.

**Important correction from the user's direct confirmation:**
The **existing IBKR Gateway connection, baseline scanner operations,
and OHLC imports ARE ALREADY WORKING correctly for other
ASJR/Chakra tasks**. They are *user-confirmed existing operational
infrastructure*, not a missing capability. **Do not
propose a new IBKR login, Gateway, client ID, port, scheduler,
or second bot**. The new RudraScanner must share the
connected EWrapper/EClient app and original 5-minute pipeline.
Do NOT infer that the new RudraScanner's four scanner-code
requests or genuine live 5M WAP callback have already run:
they are **still pending feature-specific live verification**.

**Latest real VPS logs (Oct 10):**
`git pull --ff-only origin main` through `2d1ee811`;
complete scanner suite **83/83 PASS**:
`Ran 83 tests in 0.887s; OK`.
Monday read-only preflight returned
`scheduled_mode=shadow`, `research_enabled=true`,
`ready_to_shadow=true`, both scanner-Discord flags
false. It made **0 IBKR requests, 0 orders, 0 Discord sends**.
Fixed list: 19 configured rows, **18 eligible** in
RudraScanner, because ONDS excluded; existing
Wicks fixed membership untouched, permanent INTC
and AKAM/WTTR notes preserved. The new Scanner
selection caps fixed source to 10.
AI ticker research valid at Monday open: **1**
(permanent unverified INTC, overlaps fixed);
**10 expired** at 12 Oct 12:00 UTC / 13:00 UK.
There is **no working hourly AI-to-GitHub CSV automation**;
the previously attempted schedule was blocked by the
account active-task limit. Do not silently roll dates
forward or claim 30/30 candidates.

**New code already committed and pulled in VPS checkout:**
Monday 12-Oct SHADOW runtime config, four IBKR scanner
codes (TOP_PERC_GAIN / TOP_PERC_LOSE /
HOT_BY_VOLUME / MOST_ACTIVE); separate 30-name source
selection, additional missing stock and SPY/QQQ/sector-ETF
5M fetch through the SAME app; actual IBKR WAP
VWAP, continuous EMA9, 20 completed prior RTH
sessions RVOL20, 5 provisional long/short patterns,
top-down as-of-5M confirmation, independent 1H
research cache, same common DataLake and Git reports.
Old Wicks and locked 1H Rudra-Reversal detectors,
NQ Yahoo feed and their Discord state remain
separate. No new orders, scanner Discord OFF.

**Unverified:** whether the running VPS Chakra Python
process has reloaded new imports since the pull; new
4-code IBKR callback results, WAP/sector/benchmark
freshness and pacing, new 5M/1H/report CSV outputs,
and experimental scanner Discord bridge in the
actual running process. Saturday's
`RudraScanner/live_status.py --date 2026-10-12`
output `NOT SAVED YET` is EXPECTED and means no
Monday data files exist yet; it is a **read-only
saved-report viewer, not a command that starts
broker scans**. A Monday live session must be
observed before declaring new scanner LIVE.

**Next verification:** with the user's existing
bot-control workflow, confirm version
`ASJR Analyst Version: 2026.10.10.12` after
a controlled process reload, then check fresh
Monday 12 Oct 5-minute Chakra run:

```bash
cd /root/trading/ASJR
/root/trading/venv_new/bin/python RudraScanner/live_status.py --date 2026-10-12
/root/trading/venv_new/bin/python RudraScanner/print_saved.py --date 2026-10-12
```

Validate real per-code scanner status, selected
source counts, real WAP, sector context, current
bar stamps, RVOL20 readiness, one-hour coverage
and that Wicks/Reversal alerts still function.
No second IBKR connection needed. First 15
full RTH 5M bars (75 min) may be required
for a pattern in addition to the 30-minute
execution gate. Keep scanner Discord disabled
until explicit approval and evidence.

---

## SSH scan_now.py IMPLEMENTED AFTER 13:47 UTC, 2026-10-10 — TEST/RELOAD PENDING

The user ran a hypothetical CLI and got
`No such file or directory`. At the user's request,
created actual `RudraScanner/scan_now.py` and
`RudraScanner/manual_request.py` plus
`RudraScanner/tests/test_manual_ssh.py`
(10 new isolated unit tests), ignored runtime IPC
request JSON/lock/temp and integrated into existing
Chakra
`ASJR_Analyst/Tests/test_asjr_pipeline.py`
version **2026.10.10.13**.

Architecture: user runs
`/root/trading/venv_new/bin/python RudraScanner/scan_now.py`
during an open scheduled US/ET Chakra session.
This writes an atomic local
`ASJR_Analyst/rudra_scanner_manual_request.json`
request and **waits for the next normal 5-minute
Chakra scanner cycle** to acknowledge the result;
`--no-wait` queues immediately, `--status`
inspects without enqueue, and `--saved` reads
the last saved common DataLake report. Requests
are .gitignored; research reports still saved
via normal DataLake and Git pipeline.
**NOT an independently instantaneous broker API
scan; NO new IBKR connection/client/Gateway,
new scheduler, order function or scanner Discord.
Original Wicks and locked Reversal still have
priority.** It refuses weekend live requests;
on Saturday, use `--help`, `--status` or
`--saved --date`, not unqualified live mode.
Full instructions: `RudraScanner/SCAN_NOW.md`.
Other canonical next-session state:
`RudraScanner/CURRENT_STATE.md`.

**Verified status distinction:** user-confirmed
original VPS 83/83 offline tests PASSED
at 13:30 UTC *before this change*. The expanded
**93 tests are committed, NOT YET run on the VPS**.
No running Chakra process reload was observed.
A new Git pull, 93-test check and controlled bot
restart are required before live SSH request
operation can be called verified.

## Maintenance rule

- This file is the canonical AI/analyst handoff and must be updated after every material ASJR/Chakra/Rudrakchhya/Jaguar code, alert, schedule, DataLake, operational, audit, or deployment change so future sessions start from the latest verified state.

Update this handoff whenever ASJR Analyst/Chakra code, schedules, Git/DataLake behavior, Discord alerts, or live verification status changes. Record the date, affected methods, operational impact, and what was actually tested. Keep unverified assumptions marked as such, and update the README link if this document moves.

## 2026-09-30 UK alert display

- Code commit `cbe5a02`: `Utils/asjr_alerts.py::prepare_alert` now shows UK candle dates/times for both EMA20 and lower-wick alerts, with header `ASJR 5M ALERTS | candle times UK` and automatic BST/GMT suffix using `Europe/London`.
- Example: `2026-09-29 19:35 ET` displays as `2026-09-30 00:35 BST`. Conversion handles date rollover and US/UK daylight-saving mismatch weeks.
- Display-only change: event generation, US session labels/date logic, original `bar_time_et` data, and deduplication keys remain unchanged.
- Local checks passed for EMA20/wick formatting, midnight rollover, summer/winter time, March/October DST mismatch weeks, and repeat suppression.
- Pull the updated code and restart the Python BOT to load it. VPS activation and a live Discord message have not been verified from this session.

## 2026-09-30 UK logs and reports

- Version `2026.09.30.1`: `asjr_logger.UKFormatter` uses explicit `Europe/London` timestamps in file and console log records, independent of the VPS system timezone. Log filenames now include UK calendar date, time, and BST/GMT.
- `asjr_snapshot.build_ticker_summary` converts report `datetime` to timezone-aware UK time and adds a readable `datetime_uk` column. Snapshots include `report_timezone` and `generated_at_uk`.
- US trading-session dates and DataLake session folders retain their trading-day meaning; raw candle instants and live monitoring logic are unchanged. Existing historical logs are not rewritten.
- Local tests passed for BST/GMT, midnight rollover, log output and filename suffixes, report candle-instant preservation, missing intraday data, and unchanged session date.
- Pull/restart required to activate; VPS deployment remains unverified. Scope is ASJR Analyst logs in this repository, not the external VPS bot's own logger.

## 2026-09-30 retention and live UK verification

- GitHub-uploaded `reports/asjr_pipeline_20260930_073328_BST.log` verified version `2026.09.30.1`, UK timestamps, and data completion at 07:33:39 BST (20 tickers, 10,983 intraday rows).
- User authorized daily removal of DataLake folders older than five calendar days. Use Europe/London today minus five days, deleting only date folders strictly before that cutoff; retain cutoff day and all newer folders.
- Cleanup commit `33a09f0` removed `ASJR_Analyst/DataLake/2026-09-24`; verified main retains September 25, 26, 28, 29 and 30.
- ChatGPT task `ASJR DataLake cleanup` is enabled daily around 08:00 UK from October 1. It commits qualifying deletions to main without rewriting history. VPS working-file deletion follows the bot's next successful pull; local VPS removal has not been independently verified.
- This removes tracked working files, not Git history or untracked files. No Python bot restart is needed for these data deletions.

## Ownership and schedule

- ASJR/Rudrakchhya is the manual intraday analyst. Jaguar is the separate swing/long-term analyst; do not mix their strategy logic.
- Keep the two alert layers distinct: Rudrakchhya's existing hourly ChatGPT jobs review hot sectors, fixed/open-position lists and catalysts across overnight, premarket and regular trading; Chakra's five-minute BOT uses IBKR chart data for the mechanical EMA20 event and Discord. Do not present a Chakra cross as the analyst's confirmed entry setup. The analyst's preferred sequence is strong sector -> leading ticker -> controlled pullback/flag near rising EMA20 -> hold/reclaim -> renewed volume and right-side confirmation.
- The existing BOT owns the five-minute schedule; do not add another scheduler or loop inside ASJR Analyst.
- The VPS repository root is `/root/trading/ASJR` on `nostalgic-mirzakhani`. The VPS Chakra caller is outside this repository at `/root/trading/utils/trading_sudarsan_chakra.py`.
- The caller invokes `tp.run_asjr_manual_pipeline(app=app, trade_date=None, gapup_df=None, fetch_gapup_from_app=True, include_sector=True, git_submit=True)`. The intended alert integration then invokes `tp.prepare_alert(result)` and, if nonempty, `SN.send_to_discord(message)`. The exact currently running VPS caller was not inspected from here; verify that it contains these two alert lines before assuming Discord alerts are live.
- GitHub repo: `raghunathbhandari/ASJR`, production branch `main`. `run_asjr_manual_pipeline` and `prepare_alert` are in `ASJR_Analyst/Tests/test_asjr_pipeline.py`. PR #1 was merged 2026-09-27. The last confirmed code commit was `4a3075d`; later DataLake pushes may advance `main`.

## 2026-09-29 percent-mover discovery change

- The IBKR discovery scanner was changed from an RTH opening-gap scan to a market-wide percentage-mover scan. `get_api_tickers(scan_code="AUTO")` now runs both `TOP_PERC_GAIN + changePercAbove=4` and `TOP_PERC_LOSE + changePercBelow=-4` in every active session, using the existing liquidity filters (price >= $5, avg volume >= 1M, market cap >= $500M) and `stockTypeFilter="CORP"`.
- The legacy `get_gapup_tickers()` function name and `ibkr_gapup.csv` filename are intentionally retained for caller/file compatibility, but they now represent +/-4% percentage movers rather than opening-gap-only names.
- Reason for the change: BE/Bloom Energy was not present in the 2026-09-29 DataLake because it was an intraday momentum mover rather than a >=4% opening-gap result. The new scanner is intended to surface BE/FICO-style moves earlier so they can be added to the DataLake and then evaluated with 5-minute/15-minute structure.
- Discovery rule: +4% with continuing higher-high structure is an EARLY BUY WATCH; -4% with continuing lower-low structure is an EARLY SELL WATCH. This is discovery, not an entry signal. Market -> Sector -> Leader context and EMA20/structure confirmation still govern actual entries.
- Code commits on `main`: `cd23eb3` (scanner logic) and `0dc5b9a` (pipeline logging labels). Live IBKR behavior is not yet verified on the VPS after pull/restart.

## Pipeline and date rollover

- `run_asjr_manual_pipeline` builds the fixed + hot-sector + scanner ticker universe; fetches yfinance 30-day daily data and IBKR 5-minute data using `duration="3 D"`, `wait_time=20`, `batch_size=5`; computes features; writes raw CSV, ticker summary and snapshot; then calls the **existing** `asjr_git.submit_datalake` with `git_submit=True`.
- New `Utils/asjr_day.py` resolves session dates in `America/New_York`. Scheduled runs skip the closed weekend before Sunday 20:00 ET. From Sunday 20:00 ET, the session date is Monday. From 20:00 ET on Mon–Thu, it is the next session date.
- For an active session, the pipeline creates that date's DataLake folders on the VPS before reading the watchlist. A manually prepared `config/fixed_watchlist.csv` takes priority; if absent, the latest **earlier** date's watchlist is copied into the new folder. Future watchlists are never used to backfill a past date. Monday 2026-09-28 already has a prepared list including AKAM and WTTR.
- The existing Git helper stages the entire active day's DataLake folder (including copied config), commits, pulls with rebase against `main`, and pushes `main` when there are changes. It was deliberately left unchanged. Pipeline success is now printed to the console rather than appended to its tracked log after Git submit, avoiding a dirty prior-day log at rollover.
- `git pull` changes files on disk; a running Python BOT does not automatically reload imported code. Restart the BOT after code updates. Daily date rollover alone needs no restart.

## Five-minute Discord event

- `result["alert_data"]` is a list of fresh ticker events from the existing in-memory `result["intraday"]` DataFrame. There is no second IBKR fetch or CSV read for the detector.
- `Utils/asjr_alerts.py` examines up to the last two **completed** 5-minute candles per ticker, and emits only a cross above or below EMA20 from the relevant session within the freshness window. It displays the timestamp in UK time (BST/GMT), session label RTH/EXTENDED, close, EMA20 and distance, candle volume compared with the prior 12-bar median (only if at least five positive prior bars), EMA slope, and a prior-12-bar high break where present. Overnight Sunday evening bars map to Monday's session date.
- `tp.prepare_alert(result)` makes one Discord code block with ticker sections, stays below Discord's 2,000-character limit, and suppresses repeat event IDs using local `ASJR_Analyst/alert_state.json` (gitignored). It returns an empty string if there is no new event. This is chart context, **not** an entry signal; actual entries remain regular-session-only after 09:30 ET and need the user's separate confirmation rules.
- Example:

  ```text
  ASJR 5M ALERTS | candle times UK

  INTC [RTH] 2026-09-28 15:15 BST
  EMA20: CROSSED ABOVE | Close $25.10 | EMA $25.00 (+0.40%)
  Vol: 250,000 (1.8x prior 12-bar median) | EMA: rising | 12-bar high break

  AMD [RTH] 2026-09-28 15:15 BST
  EMA20: CROSSED BELOW | Close $168.20 | EMA $168.50 (-0.18%)
  Vol: 410,000 (1.3x prior 12-bar median) | EMA: flat/falling
  ```

## Tested and still to verify

- Synthetic checks passed for a fresh cross, stale-bar rejection, volume comparison, message size, repeat suppression, date rollover, prior watchlist copying, prepared-list priority and Sunday overnight session assignment. The Sunday 2026-09-27 morning notebook run returned `SKIPPED_CLOSED_SESSION` without an alert, as intended.
- The user showed that VPS `main` successfully rebased, pushed local DataLake commits, and fast-forwarded to code commit `4a3075d`; subsequent `git pull` said up to date and `git push` said everything up to date. A BOT restart **after** that last code commit was advised but not explicitly confirmed in the conversation. Verify the running process loaded the new module and that its caller actually sends `tp.prepare_alert(result)`.
- Live IBKR overnight 5-minute historical bars for the chosen SMART contract/scanner request have **not** been verified. IBKR's eligible overnight market begins Sunday 20:00 ET (Monday 01:00 UK BST on 2026-09-28); regular US trading opens 09:30 ET (14:30 UK BST). A fresh alert is not guaranteed at either open. Check actual bar timestamps, `result["git"]`, the GitHub DataLake snapshot and the BOT error/Discord path after the first active run.
- `prepare_alert` currently records deduplication before `SN.send_to_discord` is called. If sending fails after formatting, that event is not retried automatically; this is a known delivery limitation, not a tested exactly-once guarantee.

## 2026-09-30 wick-only Discord policy

- User stopped EMA20-cross notifications. Commit `0e14376` removes cross event generation from `build_ema20_alerts` (legacy callable name retained) and filters legacy/cached cross events out of `prepare_alert`.
- Lower-wick detection, thresholds, UK timestamps, deduplication and existing data collection are retained. Catalyst automation is separate.
- Verified main contains the change; Python syntax compilation passed. Live VPS/Discord behavior is not yet verified. Bot must pull and restart to load changed Python code.


## 2026-10-01 clean wick-only Chakra alerts

- Root cause found from live DataLake history: IBKR 5-minute historical data can trail real time by roughly 15-20 minutes. The previous detector only accepted bars within an 11-minute freshness window, so valid wick candles could arrive after the detector had already declared them stale.
- `Utils/asjr_alerts.py` now exposes `build_wick_alerts` as the active detector. The pipeline calls this directly; no EMA20-cross event generation is used for Discord alerts.
- Wick detection now covers both `LOWER_WICK` and `UPPER_WICK` using the existing materiality thresholds (minimum candle range, price-relative wick size, candle-share, body multiple, and recent-range comparison).
- Completed bars from the last 60 minutes are scanned so delayed IBKR bars are still eligible. `prepare_alert` deduplicates event IDs using `alert_state.json`.
- Alert rule is simple: if at least one new qualifying wick survives deduplication, `prepare_alert(result)` returns a non-empty Discord code block; if none exists, it returns `""` and the caller sends nothing.
- Discord wick messages no longer show EMA20/cross information. They show OHLC, wick size/share, prior 12-bar high/low sweep context, volume context, next-candle confirmation, and UK candle time.
- Pipeline version advanced to `2026.10.01.1`.
- Commits: `31d9cc4` (wick-only detector, upper+lower, delayed-bar tolerance) and `8794765` (pipeline calls `build_wick_alerts` directly).
- VPS must `git pull` and restart the Python BOT because imported Python modules are not hot-reloaded.


## 2026-10-01 stateful no-miss wick processing

- Chakra wick processing now uses a persistent per-ticker `last_processed` candle marker in local `ASJR_Analyst/wick_alert_state.json`.
- On each run, IBKR data is imported first. `build_wick_alerts` then evaluates every completed current-session 5-minute candle after each ticker's saved marker. The marker advances only after those candles are evaluated for wick/no-wick.
- If the BOT was stopped or IBKR delivered bars late, the next run catches up from the last processed candle instead of using a freshness cutoff. This changes the guarantee from "fresh only" to "may be late, but do not intentionally skip a completed bar that is present in the fetched history."
- On the first run with no state file, all completed candles in the current trading session are processed and every qualifying upper/lower wick is added to the pending queue.
- Qualifying wick events are persisted in `state["pending"]`. `prepare_alert(result)` formats the oldest pending events that fit under Discord's message-size limit, but does not remove them.
- After `SN.send_to_discord(discord_message)` succeeds, the caller must run `tp.mark_alert_sent()`. Only then are the event IDs from that prepared batch removed from pending. If send fails or the process stops before acknowledgement, the same batch remains pending for retry.
- Large backlogs can require multiple Discord messages. The existing one-message caller will deliver one batch per scheduled run; remaining pending alerts stay queued for later runs, so they may arrive late but are retained.
- Local state/batch files are gitignored: `wick_alert_state.json`, `wick_alert_batch.json`, and temp variants.
- Pipeline version is `2026.10.01.2`. Relevant commits: `a65f8d7` (persistent processing marker/pending queue), `e5e6657` (delivery acknowledgement wrapper), `3dcabe1` (gitignore state files).
- Required VPS caller sequence:
  ```python
  discord_message = tp.prepare_alert(result)
  if discord_message:
      SN.send_to_discord(discord_message)
      tp.mark_alert_sent()
  ```
- Pull + BOT restart required to load this version.


## 2026-10-01 live wick audit findings and next-audit guide

This section is the canonical audit record for the 2026-10-01 Chakra wick-alert investigation. Future Rudrakchhya/Chakra audits should read this before changing alert logic.

### What was observed live

- The external Chakra caller was confirmed to use the intended sequence:
  - `result = tp.run_asjr_manual_pipeline(...)`
  - `discord_message = tp.prepare_alert(result)`
  - `if discord_message: SN.send_to_discord(discord_message)`
- The caller already prints both `result` and `discord_message`, so the tmux console is the best place to inspect the final alert payload path.
- A live tmux capture showed `result["alert_data"] == []`. Therefore the missing Discord wick alert was upstream of `prepare_alert` and `send_to_discord`; Discord was not the first failure point.
- The Git/DataLake logs around 14:44-14:45 BST showed the pipeline running normally and fetching 5-minute data successfully.
- Historical inspection of the exact DataLake commit from that run showed AMAT, CRDO, LRCX and WDC data only through 09:25 ET, even though the live clock was around 09:45 ET. This demonstrated an IBKR historical-data lag of roughly 15-20 minutes for those names on that run.
- Later DataLake versions contained the 09:35 ET candles and those candles met the configured wick thresholds. Therefore the missing alerts were not because qualifying wicks never existed; they arrived in the fetched history later than the old alert freshness rule allowed.
- The previous detector had an 11-minute freshness rejection. With IBKR history lagging by about 15-20 minutes, valid wick bars could be rejected as stale as soon as they finally became visible to the bot.
- The prior implementation only detected lower wicks. The clean wick implementation now handles both upper and lower wicks.
- The previous `prepare_alert` flow marked events as sent before the caller actually completed Discord delivery. That created a possible loss window if Discord sending failed after formatting.

### Architecture after the audit

- Data collection remains owned by `run_asjr_manual_pipeline()`. It imports the latest scanner universe, daily data, 3-day IBKR 5-minute history, features, sector context, snapshot and DataLake files.
- Wick processing is a separate logical stage. The pipeline calls `alerts.build_wick_alerts(intraday, trade_date=trade_date)` after the latest IBKR import is complete.
- `build_wick_alerts` uses a persistent per-ticker `last_processed` 5-minute candle marker instead of a freshness cutoff.
- For each ticker, every completed session candle after `last_processed` is evaluated exactly once for wick/no-wick. After evaluation, the read/process marker advances to the latest completed candle available in the fetched history.
- If the bot is stopped, delayed, restarted, or IBKR data arrives late, the next run resumes from the saved marker and processes the missing candles present in the newly imported history.
- First run with no state file processes all completed candles from the current trading session. This intentionally allows the first stateful run to discover older qualifying wicks from the day.
- Qualifying upper/lower wick events are persisted in a local pending queue. They remain pending until delivery is acknowledged.
- `prepare_alert(result)` formats the oldest pending events into one Discord-safe message and records only the prepared batch IDs. It does not acknowledge delivery.
- After a successful Discord send, the caller must execute `tp.mark_alert_sent()`. Only that prepared batch is then removed from the pending queue.
- If Discord sending fails, the process stops, or acknowledgement is not reached, the events remain pending and are retried later.
- If the backlog exceeds Discord's message-size limit, one batch is sent per scheduled run and the rest remain pending for subsequent runs. The design therefore favors delayed delivery over silently dropping an alert.
- Local state files are intentionally gitignored:
  - `ASJR_Analyst/wick_alert_state.json`
  - `ASJR_Analyst/wick_alert_batch.json`
  - matching temporary files.
- Pipeline version after this redesign: `2026.10.01.2`.

### Required caller contract

The external VPS caller must use this order:

```python
result = tp.run_asjr_manual_pipeline(
    app=app,
    trade_date=None,
    gapup_df=None,
    fetch_gapup_from_app=True,
    include_sector=True,
    git_submit=True,
)

print(result)

discord_message = tp.prepare_alert(result)
print(discord_message)

if discord_message:
    SN.send_to_discord(discord_message)
    tp.mark_alert_sent()
```

Do not call `tp.mark_alert_sent()` before Discord sending.

### Important remaining delivery caveat

- The current external `send_to_discord(message)` helper catches exceptions internally and does not return a success flag or re-raise the failure. Therefore the caller cannot currently distinguish a confirmed send from a swallowed Discord exception.
- For a strict no-loss delivery guarantee, change `send_to_discord` later to return `True` on successful `webhook.send(message)` and `False` on failure, then call `tp.mark_alert_sent()` only when the return value is `True`.
- Until that caller helper is improved, the stateful scan prevents candle-processing loss, but Discord acknowledgement is only as reliable as the current helper's success behavior.

### Next audit checklist

1. Check `ASJR_Analyst/OPERATIONAL_HANDOFF.md` first.
2. Verify current `main` commit and pipeline version.
3. Check the running tmux process was restarted after Python changes.
4. Compare the latest fetched 5-minute candle timestamp with the actual clock to measure IBKR lag.
5. Inspect `result["alert_data"]` in tmux output before investigating Discord.
6. Inspect `wick_alert_state.json` for per-ticker `last_processed` and pending events.
7. Inspect `wick_alert_batch.json` if a Discord message was prepared but not yet acknowledged.
8. Verify `prepare_alert` returns non-empty text when pending events exist.
9. Verify Discord send outcome.
10. Verify `tp.mark_alert_sent()` removes only the successfully delivered prepared batch.
11. Never reintroduce a short freshness cutoff that can discard delayed IBKR bars.
12. Keep EMA-cross alert generation separate from this wick-only Chakra delivery path; current Discord policy is wick-only.


## Mandatory version and log policy

- Every material ASJR Analyst / Chakra Python code change must increment `ASJR_ANALYST_VERSION` before deployment.
- Documentation-only edits do not require a runtime version bump unless they accompany a code change.
- Every pipeline run must log the running version at startup using `RUN | VERSION | <version>`. This is the authoritative runtime evidence for which code generation the VPS process actually loaded.
- The same version must be recorded in this `OPERATIONAL_HANDOFF.md` together with the date, affected methods/files, behavior change, deployment requirement, and verification status.
- After a version-changing Python update: push to `main`, VPS `git pull`, then restart the running Python BOT. A successful pull without restart does not prove the new runtime version is active.
- During every audit, check the newest DataLake report log first and compare its `RUN | VERSION` line with the current version documented here. If they differ, treat the running BOT as stale until restarted and re-verified.
- Do not infer the runtime version only from Git HEAD. The run log version is the proof of what the Python process actually executed.


## CRITICAL PRE-CODE-CHANGE CHECKLIST

Before making any ASJR Analyst / Chakra / Rudrakchhya / Jaguar code change, always do these checks first:

1. Read this canonical file: `ASJR_Analyst/OPERATIONAL_HANDOFF.md`.
2. Check the current `main` Git version/commit and inspect the exact files/methods that will be changed.
3. Check the newest DataLake run log and read its `RUN | VERSION | <version>` line.
4. Compare the runtime log version with the current `ASJR_ANALYST_VERSION` documented in this handoff and present in the code.
5. If Git/code version and runtime log version differ, treat the running BOT as stale. Do not assume current Git code is live until the BOT is restarted and a new log confirms the new version.
6. Review the latest relevant audit findings in this handoff before altering behavior, especially alert state, DataLake, Discord delivery, scheduler, date/session, or IBKR timing logic.

For every material code change:

1. Increment `ASJR_ANALYST_VERSION`.
2. Make the code change.
3. Update this `OPERATIONAL_HANDOFF.md` in the same change cycle with:
   - new version,
   - date,
   - files/methods changed,
   - reason/root cause,
   - behavior before/after,
   - deployment steps,
   - verification status,
   - any remaining caveats.
4. Commit/push to `main`.
5. On VPS: `git pull`.
6. Restart the Python BOT when Python/imported code changed.
7. Verify the next DataLake log contains the new `RUN | VERSION | <version>` line.
8. Only after that log appears should the new version be treated as live.

The runtime log version is the primary proof of the code actually running on the VPS. Git HEAD alone is not sufficient.


## 2026-10-01 locked liquidity-sweep wick filter

- Runtime version: `2026.10.01.3`.
- Files changed:
  - `ASJR_Analyst/Utils/asjr_alerts.py`
  - `ASJR_Analyst/Tests/test_asjr_pipeline.py`
- Reason: the earlier detector produced too many ordinary wick events. User validated LRCX 09:00 BST and CNXC 14:35 BST as the type of real liquidity-sweep/rejection wick desired.
- Locked immediate wick rule:
  - upper or lower wick itself must be at least **2.0% of price**;
  - real candle body must be at most **1.0% of price**;
  - prior full-range, wick-share, body-multiple, and prior-median-range threshold gates were removed from qualification.
- Alert formatting now includes both wick percent and body percent.
- Old pending wick backlog is intentionally discarded on this detector schema change. `STATE_SCHEMA_VERSION = 3` causes the first run after deployment to seed each ticker's `last_processed` marker at the newest completed candle already present and emit no historical backlog. Subsequent runs evaluate only newly completed candles while retaining the stateful no-miss behavior for future delayed data/restarts.
- Normal trading-day rollover does not use this deployment reset; a new session can still be processed from its first available completed candle.
- The previously discussed optional “one biggest wick per hour” fallback is **not implemented in this version**. Version 2026.10.01.3 locks only the validated 2% wick / 1% body immediate filter so live behavior can be observed cleanly before adding another alert class.
- Pre-change audit completed before edit:
  - canonical handoff reviewed;
  - Git code showed `ASJR_ANALYST_VERSION = "2026.10.01.2"`;
  - newest inspected DataLake log `asjr_pipeline_20261001_172101_BST.log` confirmed `RUN | VERSION | 2026.10.01.2`.
- Deployment required: VPS `git pull`, then restart the Python bot.
- Live verification required after restart: newest DataLake report log must show `RUN | VERSION | 2026.10.01.3`. Until that appears, treat this change as pushed but not live-verified.


## 2026-10-01 dynamic wick setup configuration

- Runtime version: `2026.10.01.4`.
- `ASJR_Analyst/Utils/asjr_alerts.py` now reloads `ASJR_Analyst/config/wick_setups.json` on every pipeline run.
- This requires one VPS pull + bot restart to load the JSON-aware code. After that, edits to `wick_setups.json` are picked up on the next scheduled pipeline run without a Python restart.
- Current review setup definitions are:
  1. `LOWER LIQUIDITY SWEEP`: lower wick >= 2.0% of price, current low breaks the prior 12-bar low, and close reclaims back above that prior low. No body-size cap.
  2. `UPPER LIQUIDITY SWEEP`: upper wick >= 2.0% of price, current high breaks the prior 12-bar high, and close reclaims back below that prior high. No body-size cap.
  3. `REJECTION WICK`: upper or lower wick >= 2.0% of price and candle body <= 1.0% of price; no sweep/reclaim requirement.
- JSON order is priority order. One candle-side emits at most one setup label even if it matches more than one definition.
- User validation examples:
  - LRCX 2026-10-01 09:00 BST is a clean rejection wick.
  - CNXC 2026-10-01 14:35 BST is a clean upper rejection/sweep candidate.
  - LQDA 2026-10-01 13:15 BST and 14:30 BST are lower liquidity sweep/reclaim examples that must be supported despite bodies > 1%.
- The latest pre-change runtime log checked was `asjr_pipeline_20261001_180959_BST.log`, which confirmed `RUN | VERSION | 2026.10.01.3`.
- Deployment required now: VPS `git pull`, restart bot once, then verify a new DataLake log shows `RUN | VERSION | 2026.10.01.4`.
- After that verification, future wick setup tuning can be performed by editing only `config/wick_setups.json`; no restart should be needed for JSON-only rule changes.


## 2026-10-01 wick review training examples

- `ASJR_Analyst/config/wick_setups.json` now also stores eye-validated review examples so future wick-rule tuning is grounded in candles the user actually accepted or rejected.
- Accepted examples currently recorded:
  - LRCX 09:00 BST upper rejection wick.
  - CNXC 14:35 BST upper sweep/rejection.
  - AMAT 14:35 BST lower structure/rejection candidate.
  - CNXC 14:40 BST upper structure/rejection candidate.
  - LQDA 13:15 BST lower liquidity sweep/reclaim.
  - LQDA 14:30 BST lower liquidity sweep/reclaim.
- Rejected examples currently recorded:
  - WOLF 14:30 BST upper candidate — rejected by eye because body/candle structure was not the desired wick.
  - INOD 17:55 BST lower candidate — rejected by eye.
- LQDA note: for 2026-10-01, 13:15 BST and 14:30 BST are the validated LQDA examples; other reviewed LQDA wick candidates can be ignored for now.
- These review examples are reference/training data only; they do not create a new active detector rule by themselves.
- JSON commit containing the review examples: `6111f653067c37404c3f5a3c54ad283fdce02f34`.

## 2026-10-02 4% Mean Reversal strategy

- Runtime version: `2026.10.02.2`.
- New isolated strategy folder:
  - `ASJR_Analyst/Strategies/MeanReversal4Pct/mean_reversal.py`
  - `ASJR_Analyst/Strategies/MeanReversal4Pct/README.md`
- Core strategy tickers: **MU, CAT, TSLA, AMAT, INTC, LRCX**.
- Signal reference remains the **previous completed daily close** from the existing 30-day daily dataset.
- Chakra evaluates newly completed 5-minute candles and triggers immediately on the **first completed 5-minute close that crosses to -4.00% or lower versus the previous daily close**.
- One trigger per ticker per trading day. Local persistent state prevents repeated alerts on every five-minute run.
- Alert levels are calculated from the detected 5-minute close: **SL = -1%**, **TP = +4%**.
- Discord format:
  ```text
  4% Mean Reversal:
  Ticker: MU
  Detected Candle: YYYY-MM-DD HH:MM BST/GMT
  SL: xx.xx
  TP: xx.xx
  ```
- `ASJR_Analyst/Tests/test_asjr_pipeline.py::run_mean_reversal_strategy(daily, intraday, trade_date)` is the dedicated method entry point. The main pipeline calls this helper; mean-reversal detection is not embedded inside wick logic.
- Existing wick detection remains separate and unchanged. `Utils/asjr_alerts.py::prepare_alert` gives pending mean-reversal messages priority over wick messages, and the existing caller continues to use the same `tp.prepare_alert(result)` / `tp.mark_alert_sent()` contract.
- Today’s fixed watchlist was updated so MU, CAT, TSLA and INTC are added; AMAT and LRCX were already present.
- New runtime state files are gitignored: `mean_reversal_alert_state.json` and `mean_reversal_alert_batch.json` plus temp variants.
- Pre-change runtime verification: newest inspected DataLake log `asjr_pipeline_20261002_121438_BST.log` showed `RUN | VERSION | 2026.10.01.4`. Therefore the new version is **not live yet**.
- Deployment required: VPS `git pull`, restart the Python BOT, then verify a new DataLake log shows `RUN | VERSION | 2026.10.02.2` before treating the strategy as live.


## 2026-10-02 ratio-based wick detector

- Target runtime version: `2026.10.02.3`.
- Files changed:
  - `ASJR_Analyst/Utils/asjr_alerts.py`
  - `ASJR_Analyst/config/wick_setups.json`
  - `ASJR_Analyst/Tests/test_asjr_pipeline.py`
- Reason: fixed wick percentage of stock price was too strict for high-priced stocks such as MSFT. User visually validated MSFT 14:40 BST and 14:45 BST as wicks that must alert.
- Wick qualification is now ratio/structure based rather than requiring a fixed percent of stock price.
- New JSON-supported metrics:
  - `min_wick_share_pct`: wick / full candle range.
  - `min_wick_body_ratio`: wick / real body.
  - `min_wick_opposite_ratio`: primary wick / opposite wick.
  - `min_range_vs_median`: candle range / median prior range.
  - `min_volume_vs_median`: candle volume / median prior volume.
  - `relative_context_optional`: permits strong shape-only rejection when relative context is unavailable, useful for the first extended-hours candle.
- Current ratio setups:
  1. LOWER LIQUIDITY SWEEP: lower wick >= 40% of candle, wick/body >= 1.2x, wick/opposite >= 1.2x, breaks prior 12-bar low and closes back above it.
  2. UPPER LIQUIDITY SWEEP: upper wick >= 40% of candle, wick/body >= 1.2x, wick/opposite >= 1.2x, breaks prior 12-bar high and closes back below it.
  3. STRONG REJECTION WICK: wick >= 60% of candle, wick/body >= 2.0x, wick/opposite >= 1.5x, range >= 1.25x prior median where context is available.
  4. EXPANSION REJECTION WICK: wick >= 40% of candle, wick/body >= 1.2x, wick/opposite >= 1.5x, range >= 2.0x prior median, volume >= 2.0x prior median.
- MSFT validation from 2026-10-02:
  - 14:40 BST lower wick: ~72.5% of candle, ~5.5x body, range ~2.06x median, volume ~27.5x -> must alert.
  - 14:45 BST lower wick: ~41.7% of candle, ~1.3x body, range ~3.14x median, volume ~34x -> must alert.
- WOLF 2026-10-01 14:30 BST remains a rejected visual example. The primary/opposite-wick dominance gate helps reject two-sided candles that do not look like the desired one-sided wick.
- Discord wick text now emphasizes shape: absolute wick, percent of candle, and wick/body ratio rather than stock-price percentage.
- Pre-change runtime verification: newest inspected DataLake log `asjr_pipeline_20261002_172337_BST.log` showed `RUN | VERSION | 2026.10.01.4`; therefore `2026.10.02.3` is pushed but not live-verified.
- Separate known issue remains: multiple 2026-10-02 runs returned `IBKR | 5m fetch completed | rows=0` and overwrote the current intraday CSV. This is not fixed by the ratio-wick change and should be addressed separately.
- Deployment required: VPS `git pull`, restart bot, then verify the next DataLake log shows `RUN | VERSION | 2026.10.02.3`.

## 2026-10-02 isolated Mean Reversal Bollinger backtest

- Added an isolated research-only backtesting package under `Backtesting/MeanReversal/`.
- Main module: `Backtesting/MeanReversal/mean_reversal_bb_backtest.py`.
- This does **not** modify the live Chakra/Rudrakchhya pipeline or runtime version.
- Stable notebook entry point: `run_backtest(...)`; strategy internals can be changed later without repeatedly editing the VS Code notebook cell.
- Data source: Yahoo Finance.
  - Daily bars are used for the close-to-close shock calculation.
  - Yahoo has no native 4H interval, so the module downloads 60m bars and aggregates regular US session bars into 4H-style candles.
- Default research rule:
  1. daily return <= -4%;
  2. shock day has at least one 4H close at/below Bollinger lower band (20, 2);
  3. after the shock-day close, BUY on the first 4H close back above the lower band after the prior 4H close was at/below the lower band;
  4. SL = 1%;
  5. TP = 3.5%;
  6. when SL and TP are both touched inside the same 4H candle, assume SL first (conservative).
- Supports explicit start/end dates, one-year Yahoo tests, candlestick + Bollinger chart, BUY/SELL markers, per-trade table, win/loss count, win rate, average/median/best/worst return, compounded return, profit factor, trade-equity max drawdown, and average 4H bars held.
- Batch helper `run_batch(...)` is included for comparing MU, AMAT, LRCX, INTC or other ticker sets.
- Production deployment/restart is not required for this isolated research module.

### Correction: BB Mean Reversion is separate from -4% Shock

- The Bollinger Band mean-reversion research strategy is now fully separate from the ASJR -4% shock strategy.
- Pure BB module: `Backtesting/MeanReversal/bb_mean_reversal_backtest.py`.
- Current pure BB default:
  1. 4H close <= lower Bollinger Band (20,2);
  2. BUY on first later 4H close back above lower band;
  3. SL 1%;
  4. TP 3.5%.
- No daily -4% shock condition is used in this BB strategy.
- `Backtesting/MeanReversal/__init__.py` now points to the pure BB module.
- This remains isolated research code; no live bot restart/runtime version change is required.

### 2026-10-02 BB Mean Reversion rule correction

- Pure BB research strategy corrected to match the referenced TradingView-style logic.
- Entry: BUY when a completed 4H candle **closes below** the Lower Bollinger Band. A wick below the band is not sufficient.
- Exit: close the long when a later completed 4H candle **closes above** the Upper Bollinger Band.
- Removed the lower-band re-entry requirement from the BB strategy.
- Removed fixed 1% SL / 3.5% TP from the default BB strategy logic.
- The notebook call remains backward-compatible: old stop/target arguments are accepted but ignored, so the user does not need to rewrite the notebook cell immediately.
- Pure BB strategy remains separate from the -4% shock strategy.

### 2026-10-02 second BB Mean Reversion method: ADX-filtered

- Plain BB strategy remains unchanged in `Backtesting/MeanReversal/bb_mean_reversal_backtest.py`.
- Added separate method `Backtesting/MeanReversal/bb_mean_reversal_adx_backtest.py`.
- ADX method:
  1. 4H Close < Lower BB(20,2);
  2. ADX(14) < 25 at entry;
  3. BUY on that completed 4H close;
  4. EXIT when a later completed 4H Close > Upper BB.
- No -4% shock logic and no fixed SL/TP in the ADX version.
- Added default 14-ticker comparison universe:
  MU, AMAT, LRCX, INTC, PLTR, CRWD, TSLA, NKE, JPM, COIN, CAT, UBER, FSLR, XOM.
- Added `compare_plain_vs_adx(...)` to run both methods on the same date range and print side-by-side trades, win rate, compounded return, drawdown, profit factor and average return.
- `Backtesting/MeanReversal/__init__.py` now exposes both plain and ADX methods without changing the existing `run_backtest` plain entry point.



## 2026-10-04 selective relative wick filter

- Target runtime version: `2026.10.04.1`; wick config version 4; state schema 4.
- User rejected the fixed 2% stock-price wick rule and requested relative detection with less noise.
- Files: `Utils/asjr_alerts.py`, `config/wick_setups.json`, `Tests/test_asjr_pipeline.py`, new `Tests/test_relative_wicks.py`, this handoff.
- Ordinary and liquidity-sweep wicks require >=50% candle share, >=2x real body, >=1.5x opposite wick, >=1.5x median prior range. At least five prior bars are mandatory; no shape-only fallback when recent context is unavailable. Baselines use up to 12 earlier completed candles, excluding the candidate.
- Ordinary rejection additionally needs >=1.5x prior median volume OR a high/low sweep and close reclaim. Sweep setups require actual sweep/reclaim.
- Preserved the previously accepted MSFT 14:45 expansion exception: >=40% candle share, >=1.2x body, >=1.5x opposite wick, >=2x median range AND >=2x median volume. This exception intentionally has a lower body ratio than ordinary wicks.
- No active setup requires a percentage of stock price. Relative range rejects tiny candles even with high relative volume. Invalid OHLC/nonfinite/zero-volume candles are ignored.
- Only one candidate side per ticker/candle is queued; prefer sweep/reclaim, then dominant wick. Existing pending retry and successful-send acknowledgement remain intact.
- Alert text now includes side and relative range; zero-body candles display `doji body` instead of an infinite ratio. Missing legacy body ratios display unavailable rather than `0.0x`.
- Schema migration intentionally clears the permissive detector's pending backlog and seeds at the newest completed candle on the first updated run. New-session catch-up remains intact. No time-based cooldown was added, preserving separately validated consecutive expansion candles.
- Pre-change audit: main tree `c11b13af5912c87abe9fd9cc17dffadf34b3328f`; pipeline code `2026.10.02.3`; latest report `asjr_pipeline_20261002_205648_BST.log` confirms `RUN | VERSION | 2026.10.02.3` and 49,980 fetched rows. Current main intraday CSV is empty, so a complete historical replay could not be performed.
- Verification: Python compilation and eight synthetic regression tests passed: price-scale invariance, tiny-range rejection, missing context, volume-or-sweep, accepted expansion shape, supplied noise shapes, one-side queue/retry/ack, and schema migration. These checks verify mechanics, not trading performance.
- Deployment: commit to main, VPS git pull, then user-controlled bot restart. Confirm next DataLake `RUN | VERSION | 2026.10.04.1` before treating as live. VPS activation/Discord delivery remains unverified.


## 2026-10-04 minimum H-L range and 2.5x body ratio

- Target runtime version `2026.10.04.2`, config version 5, state schema 5. Supersedes the earlier expansion exception's 1.2x body gate.
- User preferred the MSFT 2.5x wick/body replay (four candles) but rejected the remaining premarket candles as too small. Requested a minimum high-low gate.
- All four setups now require wick/body >=2.5x and `(high-low)/close*100 >=0.25`. Existing relative range, dominance and volume/sweep filters remain active. The 0.25% floor is an initial implementation choice, not an optimized trading threshold; it is not a 2.5% wick-size rule.
- Friday MSFT sample: 10:00 H-L 0.0968%, 13:25 0.1935%, 13:35 0.1755% are rejected. 14:40 H-L 0.3229%, wick/body 5.5x remains. 14:45 is intentionally removed by the stricter body ratio despite its 0.5483% range. Prior visual acceptance records are historical references, not overrides.
- Files changed: wick config, alert detector, pipeline version, regression tests and this handoff.
- Schema migration clears old pending candidates and seeds at the newest completed bar to avoid old permissive alerts after deployment.
- Pre-change audit: main `a0de02b687367764ecaa1cf956f832a0962003ea` has code version 2026.10.04.1. Latest available Friday log still confirms 2026.10.02.3; no evidence of VPS activation of Sunday's edits.
- Validation passed: nine regression checks, syntax compilation, and Friday MSFT replay (one retained candle, 14:40 BST). Live activation remains unverified.
- Deployment: VPS git pull and user-controlled bot restart; verify RUN | VERSION | 2026.10.04.2 in a new log. No automatic restart.

## 2026-10-04 INTC user-reviewed wick correction

- Target runtime version `2026.10.04.3`; config/state schema 6.
- User rejected INTC 13:35 BST as an ordinary candle inside an advancing move. User requested alerts for INTC 14:25 (upper wick) and 14:30 (large two-sided wick); 14:35 desirable but not required in this change.
- Sweep setup relative range threshold adjusted from 1.5x to 1.4x, allowing the genuine upper sweep at 14:25 (1.47x median). Wick/body >=2.5x and H-L >=0.25% remain mandatory.
- Ordinary strong rejection now requires a matching-side sweep/reclaim; volume alone no longer allows the rejected INTC 13:35 lower wick. Strong expansion exception retains mandatory >=2x range AND >=2x volume with all existing shape/body gates.
- Added TWO-SIDED EXPANSION WICK: each wick >=40% of range, selected-side wick/body >=2.5x, H-L >=0.25%, relative range >=2x and volume >=2x, at least five prior bars. One event per candle remains mandatory. Alert label BOTH and explicit direction unconfirmed avoid presenting a two-sided candle as a directional rejection. Internal event type remains upper/lower for delivery compatibility; both wick sizes are recorded.
- Friday replay: INTC retains 14:25 upper liquidity sweep and 14:30 two-sided expansion; excludes 13:35. MSFT remains one event at 14:40 lower sweep. INTC 14:35 remains excluded because wick/body 2.03x is below the retained 2.5x gate.
- Files changed: wick detector/config, pipeline version, regression tests, this handoff.
- Validation passed: eleven regression tests including recorded 12-bar Friday windows for three INTC examples and MSFT 14:40; neutral two-sided alert formatting; syntax compilation. These are recognition tests, not trading-performance evidence.
- Pre-change audit: main 4015399169831dc223eae57a661b8023be8b5cbd has code 2026.10.04.2; latest available Friday log remains 2026.10.02.3. No Sunday live activation evidence. Prior handoff and changed methods reviewed.
- Schema upgrade clears old pending candidates and seeds newest completed bar. VPS git pull + user-controlled bot restart required. Verify RUN | VERSION | 2026.10.04.3 before treating live.

## 2026-10-04 isolated Friday Discord replay

- Added `Tests/replay_friday_wicks.py`; no live pipeline changes or runtime version bump.
- Reads the verified nonempty Friday CSV from Git commit eea41cd8c9b83477b2dd2bdcce68877910137c1d using git show. Uses current wick config with explicit trade_date 2026-10-02 and temporary initialized schema state, bypassing live deployment seeding and weekend scheduling.
- Leaves live logs, wick pending state, delivery batch state and mean-reversal state untouched. Default preview prints counts/times; --send explicitly sends historical-labelled Discord batches.
- Sender resolution reads the actual top-level SN import from /root/trading/utils/trading_sudarsan_chakra.py and imports only that notification module, not the trading bot. If unavailable/unsupported, stops without sending and asks for import inspection. Existing helper may return None/swallow exceptions; script does not claim confirmed delivery or modify live acknowledgements. False return/raised errors stop sending.
- Offline verification: current filter produced 130 candidate signals in 20 messages; largest labelled message 1945 characters. INTC 14:25 and 14:30 retained; MSFT only 14:40. Script compilation passed. VPS caller import and actual Discord delivery remain unverified.
- Existing pending alerts can be retried by the normal alert formatter/sender; text log deletion does not reset last_processed or repopulate acknowledged candidates. Removing live state invokes seed_latest, not full historical replay. Normal Sunday scheduling skips the closed session until overnight opens.


## 2026-10-04 explicit SMART + OVERNIGHT research import

- User requested full-day IBKR candles after MU's refreshed SMART/all-hours CSV still lacked Oct 2 08:00 and 08:45 BST (gap 01:00-08:55 UK).
- Reviewed primary docs: https://www.interactivebrokers.com/campus/ibkr-quant-news/api-overnight-trading/ documents OVERNIGHT routing with primary listing exchange, separate from SMART. Historical request doc confirms useRTH=False and request fields: https://www.interactivebrokers.com/docs/tws-api/doc/market-data-historical/historical-bars/requesting-historical-bars. Market-data routing is documented; one-year overnight historical availability is not guaranteed and remains a live test.
- Added optional `IBKR_import.py --24h`; new isolated `Backtesting/DataLoader/ibkr_24h_loader.py`, usage document and offline regression tests. Existing `--all-hours` behavior and generic loader unchanged.
- Qualifies SMART to obtain conId/primaryExchange, clones for OVERNIGHT, then makes explicit historical requests with useRTH=False. OVERNIGHT is requested first. Raises on API errors/empty or repeated windows and validates overnight-session rows before claiming import success.
- Merges real SMART 04:00-20:00 ET and OVERNIGHT 20:00-04:00 ET bars with UTC indexes. No invented candles or double-counted volume. Writes isolated MarketData24h/<interval> cache, source CSVs and coverage JSON with session counts and last-date UK 08:00/08:45 checks. Original MarketData caches remain intact; research callers must explicitly select the validated new root.
- First VPS test: MU, 5m, start/end 2026-10-02, client 71, concurrency 1. Only after overnight availability is verified should --years 1 be used.
- Eight offline routing/merge/failure/CLI tests and Python compilation passed. No Gateway access in development workspace: live request, year coverage and TradingView equivalence remain unverified.
- Pre-change audit: main 2ecb6317321a9385c0d2fb928df72ce8fc8c44d6; canonical handoff/current importer/current loader reviewed. Latest DataLake log still 2026.10.02.3; Sunday user supplied console confirmed restart and closed-session skip, without runtime version line.
- Isolated research importer only: live ASJR version remains 2026.10.04.3. Pull updated repository and run standalone SSH command; no bot restart needed for this research import. No automated CSV Git push added.

## 2026-10-05 immediate compact wick delivery

- Runtime version `2026.10.05.1`. Wick recognition config and state schema remain unchanged (schema 6); retain existing last_processed and undelivered events.
- User request: wick found -> notify on the current five-minute run, no next-candle confirmation. One simple alert with every detected event; when Discord's size limit requires overflow, send the next message immediately in the same run.
- Audit correction: prior detector did NOT gate wick generation on next_confirmed. It computed next-bar commentary for historical bars. Delivery formatted only one verbose <=1900-character batch per call, with mean reversal first; that could postpone wicks across schedules. The supplied 85-minute delay is not conclusively diagnosed without the actual external caller and runtime logs.
- Removed all next-bar inspection/confirmation fields from the wick detector. Compact line: `TICKER | LOWER/UPPER SWEEP/WICK | HH:MM`, with the date once in the `WICKS | YYYY-MM-DD` header; ASJR/UK/BST/GMT words omitted at user request, London conversion retained (mixed-date catch-up includes line dates); two-sided candles say `TWO-SIDED WICK`.
- Added `send_alerts(result, sender)`: send all wick lines, immediately drain size overflow, then send independent mean-reversal notifications. Acknowledge only completed sends. False return or raised exception stops delivery and retains unsent events. Internal delivery manifest files remain for failure recovery, not confirmation waiting.
- Compatibility formatter now prioritizes wicks over mean reversal. A stale mean-reversal delivery manifest cannot acknowledge a newly prepared wick message.
- Added optional `alert_sender` parameter to `run_asjr_manual_pipeline`. When supplied, send immediately after wick/mean detection, before sector fetch, reports and Git submission. Returned alert collections contain only unsent events; `alerts_dispatched` prevents the old post-pipeline formatter sending duplicates.
- The external caller `/root/trading/utils/trading_sudarsan_chakra.py` is NOT tracked in this repository. Enable the callback once on the VPS with:

```bash
cd /root/trading/ASJR
git pull
/root/trading/venv_new/bin/python ASJR_Analyst/Tools/enable_immediate_wicks.py
```

- Installer validates exactly one existing `tp.run_asjr_manual_pipeline` call, adds `alert_sender=SN.send_to_discord`, keeps other caller code, saves a backup, and never restarts the bot. It stops without editing if the expected structure is absent. Re-running with the parameter present is a no-op.
- After installation, use the existing Discord stop/start commands yourself. Check the next log for `RUN | VERSION | 2026.10.05.1` and `ALERTS | Immediate dispatch`. Without the caller callback, the legacy formatter still only prepares one size-limited message per run; pull/restart alone does not enable overflow draining or early delivery.
- Existing sender caveat: a helper returning None and swallowing exceptions cannot prove delivery. For reliable acknowledgement it must raise on failure or return False, and return True on success. No notification helper source was available to change in this repository.
- Timing remains limited by scheduler execution and actual IBKR data availability; this change does not guarantee a wall-clock five-minute SLA when the caller is stopped or fetching is delayed. Catch-up events keep their original UK candle times.
- Validation: 17 wick regressions passed, including first completed candle without a following bar, all 80 events delivered once in one call with size overflow, failed overflow/retry, wick priority over mean reversal, stale acknowledgement isolation, caller patch idempotence, and the existing user-reviewed shape tests. Python compilation passed. VPS activation and Discord arrival are not verified from this workspace.


## 2026-10-06 one-time EURUSD research import hook

- Added `Backtesting/DataLoader/forex_historical_downloader.py` for IBKR spot FX MIDPOINT history. Default research scope is EURUSD, one year, native 1d/4h/1h bars, UTC timestamps, output under `Backtesting/BacktestData/IBKR/Forex/EURUSD/`.
- Added `Backtesting/DataLoader/run_forex_download_tmux.sh` and `forex_download_hook.py`. The launcher starts detached tmux session `forex_download`, uses IBKR client ID 41, writes `Backtesting/BacktestData/IBKR/Forex/logs/EURUSD_1y_download.log`, creates a local .done marker after successful completion, and pushes the generated CSVs + tracked download log to main.
- `ASJR_Analyst/Tests/test_asjr_pipeline.py::run_asjr_manual_pipeline` version `2026.10.06.1` now calls the one-time Forex hook near the start of every scheduled DataLake run. The launcher is idempotent: later cycles exit immediately if the tmux job is already running or the local completion marker exists.
- The Forex hook is isolated with try/except. Failure to launch the research import is logged but must not interrupt the normal Chakra/DataLake pipeline.
- Git operational chatter for the Forex push is kept in the local untracked state log `Backtesting/BacktestData/IBKR/Forex/.state/git_push.log`; the tracked research log is finalized before staging to avoid leaving the repository dirty after push.
- External VPS caller `/root/trading/utils/trading_sudarsan_chakra.py` remains unchanged.

## 2026-10-10 RudraScanner instructions first

- New canonical project instructions: `RudraScanner/README.md`. Read it before modifying this scanner.
- User approved two candidate sources: hourly AI CSV and multiple IBKR scanner CSVs, deduplicated into the existing import pipeline; no fixed 4% discovery requirement. IBKR supplies 5-minute/premarket OHLCV; yfinance supplies daily context.
- One common `ASJR_Analyst/DataLake/YYYY-MM-DD/`; each existing five-minute Chakra job pulls Git inputs, collects/calculates, saves and pushes results. No second scanner DataLake or scheduler.
- Required access: plain-list SSH script, same five-minute Discord result, hourly AI CSV refresh/review and on-demand AI reads. Five sections, LONG/SHORT, completed 5-minute candles, session VWAP, EMA9 and volume.
- This instructions-first commit does not deploy runtime changes. Implementation drafts remain local/uncommitted at this checkpoint. No VPS restart, IBKR chart comparison, live notification verification or automation mutation has occurred.


## 2026-10-10 RudraScanner phase 1 (development only)

- Canonical scanner design and change log:
  `RudraScanner/README.md`. User requested every subsequent discussion
  and implementation change be recorded there.
- Added an isolated discovery package with 4 IBKR scanner codes, AI CSV
  schema/expiration handling, provenance-aware union, common DataLake
  discovery output, offline tests and read-only SSH report viewer.
  Seeded `ASJR_Analyst/config/ai_scanner_list.csv` with INTC as an
  unverified user-required watch, not an AI news signal.
- **No change to the live Chakra caller, Wicks, Rudra-Reversal or scheduling.**
  The old 4% scanner remains active in the old pipeline until explicitly
  replaced following tests and user confirmation. No live IBKR/Discord
  verification or bot restart. The new tests have been committed but not run
  in a verified environment.
- Next: execute offline tests; validate actual callback/provenance and volume,
  settle unconfirmed EMA9/threshold settings, implement pattern replay,
  then add gated integration with safe Git sync and verified delivery.

## 2026-10-10 RudraScanner discovery filters confirmed

The user explicitly approved retaining the currently inherited IBKR scanner
filters: price above USD 5; average daily volume above 1 million; market
capitalization above USD 500 million; up to 50 rows per scanner code.
This decision is recorded in `RudraScanner/README.md`. It does not
reactivate the old fixed +/-4% discovery rule. The scanner remains isolated,
not live-activated, and new tests remain unverified on VPS.

## 2026-10-10 RudraScanner continuous EMA9 confirmed and coded

- User decision: 5-minute EMA9 must be continuous across day boundaries,
  including premarket/extended-hours bars returned by IBKR. No daily/RTH
  EMA9 restart. Do not invent bars for missing overnight intervals.
- Code: `RudraScanner/ema9.py` adds completed-candle EMA9 calculation
  with timezone validation, warm-up flag, gap minutes and data-quality
  diagnostics. Tests: `RudraScanner/tests/test_ema9.py`.
- Canonical design/history: `RudraScanner/README.md`.
- **Development only**: new files committed, tests not yet executed
  on verified runtime, no live scanner or bot integration/activation.
  RTH-reset VWAP remains a separate agreed setting.

## 2026-10-10 RudraScanner indicator clarification

User reiterated that the scanner uses **both EMA9 and VWAP together**.
EMA9 is continuous across available 5-minute bars and days including
premarket; VWAP is a separate RTH-reset indicator. The historical-bar WAP
versus HLC3×volume VWAP source is still awaiting explicit confirmation.
See `RudraScanner/README.md`. No live activation.

## 2026-10-10 shared DataLake — Rudra-Reversal + RudraScanner

User explicitly confirmed one common ASJR DataLake for both Rudra-Reversal
and RudraScanner (and existing modules): `ASJR_Analyst/DataLake/YYYY-MM-DD/`.
Reuse shared raw inputs and the existing five-minute Chakra collector;
keep each strategy's processed results/alerts separate inside the same daily
`processed/` and `reports/` subfolders. No second DataLake or scheduler.

Current Reversal source code searches the common day's `raw/` for 1H CSV
first, but can fall back to historical IBKR research cache; NQ 1H uses Yahoo
Finance. This does not prove that fresh shared 1H ingestion exists. Align
source publication over time without changing locked Reversal signal rules.
User approved actual bar WAP as the scanner VWAP price source; upstream IBKR
callback extension and runtime verification are still outstanding.
Canonical details: `RudraScanner/README.md`. No live deployment yet.

## 2026-10-10 common candidates: fixed + AI + IBKR for both strategies

User clarified: **fixed watchlist tickers are mandatory candidate inputs
alongside AI hourly tickers and IBKR scanner tickers**, and this ticker idea
is for BOTH RudraScanner (5M) and Rudra-Reversal (1H). Use the existing
`DataLake/YYYY-MM-DD/config/fixed_watchlist.csv`; no separate new
source directory. Merge/dedupe, retain source provenance and share
collected stock data. The two strategies retain isolated locked rules.

New isolated code: `RudraScanner/universe.py`, updated
`RudraScanner/storage.py`, test `RudraScanner/tests/test_universe.py`.
The file `processed/scalp_radar_candidates.csv` is the proposed common
candidate artifact, with FIXED/AI/IBKR provenance. Explicit ONDS/BEAT
exclusion wins even if a historic fixed row is enabled (2026-10-09 fixed
file contains an enabled ONDS, so record that as a conflict). NQ stays
on Reversal's dedicated Yahoo Finance route.

**Not live**: existing Reversal `STRATEGY_TICKERS` was not changed,
combined 1H data import is not wired, and no VPS validation or restart
has happened. Tests committed, not runtime-verified. See canonical
`RudraScanner/README.md` for complete history.

## 2026-10-10 confirmed max 30 stock tickers (10/10/10)

User approved **max 30 distinct US-stock candidates total** for the
shared RudraScanner/Rudra-Reversal source universe, selected up to
10 FIXED, 10 AI hourly, 10 IBKR scanner. Cross-source duplicates
take one slot; fill from the same source's next eligible candidate,
never overflow a source or transfer unused slots. Apply cap before
IBKR 5M/1H market data import to avoid loading every discovery name.
NQ Yahoo instrument remains separate from 30 US-stock names.

Development code: `RudraScanner/universe.py::merge_shared_universe`
enforces hard quotas and provides selection-source provenance and
`selection_summary`; `RudraScanner/storage.py` now saves status
and selected origin to common DataLake. Added offline cap tests in
`RudraScanner/tests/test_selection_caps.py`.

Rank tie-breakers are **provisional pending user confirmation**;
no fixed 4% gate. **No bot restart or live activation**. Locked
Reversal `STRATEGY_TICKERS`, Wicks and live ASJR imports are unchanged.
Canonical details: `RudraScanner/README.md`.

## 2026-10-10 news research CSV and SSH dry-run entry point

- User asked to populate AI ticker CSV from current web research for
  subsequent SSH testing. Updated `ASJR_Analyst/config/ai_scanner_list.csv`
  with ten non-fixed news ideas from October 9 plus permanent INTC.
  Rows are sourced and expiry-stamped (October 12 12:00 UTC).
  Unknown exact publisher times are left blank; fundamental quality
  is UNVERIFIED; these are research contexts not validated trade signals.
  Current list: INTC, SPCX, PLTR, LITE, AMT, HUM, AMZN,
  TMUS, AAPL, JPM, NVDA.
- `RudraScanner/ssh_smoke_test.py`: read-only validation and selected
  ticker preview for a dated common DataLake folder. Use
  `/root/trading/venv_new/bin/python RudraScanner/ssh_smoke_test.py
  --date 2026-10-09` after `git pull --ff-only origin main`.
  Also run offline `python -m unittest discover` for scanner tests.
- No live IBKR request or VPS test ran in this development session.
  No new automatic hourly update task or production scanner integration
  is active. The existing Chakra/Reversal/Wicks modules remain unchanged.
  Full instructions in `RudraScanner/README.md`.

## 2026-10-10 RudraScanner full-session documentation checkpoint

User requested all current implementation activities and decisions be recorded
in the Markdown handoff. `RudraScanner/README.md` now has a **Current
implementation checkpoint** near its beginning, with a concise status matrix,
all created/updated files, confirmed DataLake and 10+10+10 selection contracts,
confirmed scanner filters, EMA9+VWAP/WAP design, AI research snapshot, the
read-only SSH verification commands and outstanding activation blockers.

The AI CSV has 11 lines of candidates (10 source-linked research names plus
INTC permanent monitor) and expires October 12 at 12:00 UTC. The read-only
SSH preview is `RudraScanner/ssh_smoke_test.py`; offline tests are in
`RudraScanner/tests/`. **Only committed source was verified, not successful
VPS tests or live IBKR, Discord, WAP, 1H import, 5-pattern detectors or
hourly AI scheduling.** No live Chakra restart or locked strategy change.

**Future sessions:** read `RudraScanner/README.md` first; continue to update
its checkpoint + chronological change records and this operational handoff
for each material change. Revalidate actual runtime behavior before claiming
deployment. Latest user's next action is to run the existing offline tests
and SSH preview and provide the result for review.

## 2026-10-10 RudraScanner next phase queued

User will run the existing SSH validation tests. **Next task after results
are reviewed:** integrate RudraScanner within the existing Chakra bot
five-minute method, not a new scheduler. The integration must use the
shared DataLake and 10 FIXED + 10 AI + 10 IBKR universe, preserve
existing Wicks and locked Rudra-Reversal, add the necessary verified
IBKR WAP/5M/1H data flow, publish one authoritative result and use
safe Git/Discord delivery. **No integration, deployment or restart
is authorised as already complete**; the pending steps and acceptance
gates are documented in `RudraScanner/README.md`.

## 2026-10-10 final user handoff: Resume from RudraScanner README

The user requested that **all progress and the exact next-session resume
point** be saved in Markdown. `RudraScanner/README.md` now contains
**START HERE NEXT SESSION — latest checkpoint (2026-10-10 UK)** near the top.
Read this FIRST; its detailed checklist supersedes earlier provisional
status blurbs, without changing their historical record.

**Current verified status:** GitHub development code committed. Offline
unittest/VPS SSH output has **not yet been supplied or verified**. The user
will run the tests later. The US market is closed Saturday, Oct 10, but
read-only saved-file validation can run against **2026-10-09**. Expected
(not observed) selected universe is **10 FIXED + 10 AI + 0 IBKR = 20**
unique names while there is no saved new multi-scan IBKR CSV.
This is input selection, **not 20 trading signals**. A real trading-day
five-pattern output previously illustrated in chat is only an EXAMPLE:
the real five detectors, actual WAP VWAP processing, Discord scanner
delivery and hourly AI task are NOT deployed.

**Next stage after seeing and fixing real SSH test results:** integrate the
new scanner into the EXISTING five-minute Chakra bot method, using the
same DataLake for Radar/Reversal, capped 10+10+10 source universe, one Git
pull/import/save/push flow, continuous EMA9, RTH-reset actual-WAP VWAP,
tested five LONG+SHORT setups, independent Reversal 1H logic and preserved
Wicks delivery/ack. External VPS caller still needs a live-code audit,
and user controls any bot restart. No automatic trade execution.

**Exact VPS commands, pending user execution:**

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
    /root/trading/venv_new/bin/python RudraScanner/ssh_smoke_test.py --date 2026-10-09

The AI research expires **Monday Oct 12 at 12:00 UTC / 13:00 UK**
and must be refreshed before the US open; it contains source-backed
watch candidates but unverified fundamental suitability. The
priority ranking and detector thresholds need review rather than
unsupported assumptions.

**Maintenance rule for future work:** update the near-top START HERE
checkpoint in RudraScanner README and this ASJR handoff with each
substantial code change, test result, activation and any remaining
blockers; retain clear distinctions between planned, committed,
offline-tested, VPS-verified and live-alert-verified stages.

## 2026-10-10 USER VPS SSH RESULT VERIFIED — RudraScanner phase 1

The user supplied actual console output for:

    /root/trading/venv_new/bin/python RudraScanner/ssh_smoke_test.py --date 2026-10-09

**Input smoke test PASSED on the VPS.** The result showed:

- AI list PARTIAL, 11 eligible rows, 0 expired;
  source published_at time unavailable for LITE/HUM/NVDA.
- Fixed list PARTIAL, 18 enabled after the old enabled
  ONDS row was excluded under the user's existing rule.
- New IBKR scanner CSV NOT_YET_SAVED, zero IBKR discovery rows;
  this is expected because the read-only smoke test makes
  **no live IBKR request**.
- Exactly **20 / 30 selected** = **10 FIXED + 10 AI + 0 IBKR**.
  Cross-source INTC counted once. Source bucket lists:
  FIXED: AKAM, AMAT, CRDO, INTC, MSFT, ORCL, QCOM, SMCI,
  WDC, WTTR; AI: AAPL, AMT, AMZN, HUM, JPM, LITE,
  NVDA, PLTR, SPCX, TMUS. No IBKR source names yet.
- Same deduplicated ticker universe displayed for the intended
  Scanner/Reversal stock selection; NQ remains Yahoo 1H outside 30.

**Verification must be interpreted narrowly:** the Python full offline
unittest command result has not been submitted; live multi-code IBKR,
1H import, historical WAP/RTH VWAP, five actual 5M detectors,
Chakra-method integration, Git delivery, Discord and automatic hourly
AI research are still **NOT verified or integrated**. The earlier
sample signal messages were hypothetical examples, not real scans.

**Remaining check before modifying production pipeline:**

    cd /root/trading/ASJR
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v

**Next engineering phase, already requested by user:** safely integrate
the scanner within the existing five-minute Chakra bot METHOD, reusing
the 30-stock shared candidate list/DataLake, preserving Wicks and
locked Rudra-Reversal 1H logic. Do not auto-restart, add a second
scheduler, or claim live notifications. The canonical latest
per-session checkpoint and actual evidence are in
`RudraScanner/README.md`, at START HERE NEXT SESSION.

## 2026-10-10 VPS 18/18 tests passed; Chakra hook wired; Friday offline replay

**Observed from user's actual VPS terminal:**
`python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v`
completed **18 tests in 0.181 seconds, OK**, zero failures.
This confirms the original discovery/EMA9/shared-universe/offline
tests on the user's runtime. Previously observed read-only SSH
ticker-preview test also passed: 10 FIXED + 10 AI + 0 IBKR = 20/30.

**User then requested immediate bot-call implementation, with
IBKR candidates copied/reused from the Friday 2026-10-09 DataLake
while the market is closed.**

Source changes committed to GitHub main:

- `ASJR_Analyst/Tests/test_asjr_pipeline.py` version
  `2026.10.10.1` now invokes
  `RudraScanner.bot_hook.run_bot_shadow()` inside the existing
  five-minute `run_asjr_manual_pipeline` method, before the legacy
  universe is fetched. Hook errors are isolated from
  Wicks/Rudra-Reversal. Shadow result included in returned dict.
- `RudraScanner/bot_hook.py` mode environment
  `RUDRA_SCANNER_MODE`: defaults to `off`; `shadow` enables
  new four-code IBKR discovery and shared DataLake candidate
  recording without changing legacy imports or alert delivery.
  No extra scheduler or IBKR connection. Production refuses
  replay unless caller passes `allow_replay=True` explicitly.
- `RudraScanner/replay.py` +
  `RudraScanner/bot_test.py` now enable a direct, read-only
  Friday historical replay via the SAME bot hook, no live API.
  IBKR source `2026-10-09/raw/ibkr_gapup.csv` (old 4%-era
  mover list, not live four-scanner output) cross-checked
  against `daily_30d.csv` for >=20 saved valid sessions,
  last close >$5 and mean 20-day volume >1 million, ranked by
  observed mean 20-day dollar volume, then de-duplicated into
  the historical **10 IBKR slots**.
- Friday stored `ibkr_gapup.csv` contains 87 rows; 84 passed
  historical 20-day price/volume screening in a GitHub data
  inspection. **No current market cap/fundamentals/tradability
  verified**, and no new four-scanner result claimed.
- `RudraScanner/tests/test_bot_hook.py` adds six offline tests;
  this **new code is NOT yet VPS-tested**. Original 18/18 result
  does not include these six. Existing Wicks/Reversal untouched.

**Next direct SSH validation, safe during Saturday market closure:**

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main
    /root/trading/venv_new/bin/python RudraScanner/bot_test.py --date 2026-10-09 --ibkr-source-date 2026-10-09
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v

Optional `--save` only after preview produces
`raw/ibkr_scanner_replay_list.csv`,
`processed/rudra_scanner_replay_candidates.csv`,
`reports/rudra_scanner_replay_report.txt` and
`reports/rudra_scanner_replay_status.json` under the
SAME common dated DataLake. It never overwrites live scanner
files, Git pushes, or sends Discord. User has not supplied
this new replay/test output yet.

**Integration level:** live bot **METHOD CALL WIRED, DEFAULT
OFF**, no production activation/restart or live 5-pattern
detectors yet. Must not claim new scanner 30-stock import,
1H feed for Reversal, actual WAP/VWAP, technical signals,
or Discord scanner alerts implemented. The user will
directly run the offline replay first and supply its output.
For chronological and priority checkpoints read
`RudraScanner/README.md` section "LATEST UPDATE".

## 2026-10-10 USER VPS CONFIRMATION — Friday replay 30/30; ALL 24 tests OK

**This is the latest RudraScanner verification checkpoint, superseding
prior “six new tests pending” notes.** User supplied actual SSH outputs
from the same VPS, after `git push` = Everything up-to-date and
`git pull` = Already up to date.

1. `/root/trading/venv_new/bin/python RudraScanner/bot_test.py
   --date 2026-10-09 --ibkr-source-date 2026-10-09`:
   **HISTORICAL_NOT_LIVE**, source `LEGACY_GAPUP_REPLAY_NOT_LIVE`,
   84 archival names passed limited price/volume checks,
   exact **30 / 30 selected: 10 FIXED + 10 AI + 10 historical IBKR**,
   no real Gateway requests, no save, and **0 real trade alerts**.
   FIXED: AKAM, AMAT, CRDO, INTC, MSFT, ORCL, QCOM, SMCI,
   WDC, WTTR; AI: AAPL, AMT, AMZN, HUM, JPM, LITE, NVDA, PLTR,
   SPCX, TMUS; legacy IBKR: ASTS, AXTI, DDOG, DE, MRNA,
   SNOW, SWKS, T, VZ, ZS.
2. `/root/trading/venv_new/bin/python -m unittest discover
   -s RudraScanner/tests -p 'test_*.py' -v`:
   **Ran 24 tests in 0.170s; OK**, zero failures/errors,
   including the six new shadow/replay bot-hook tests.

**Verified:** the shared stock candidate cap, provenance, offline
historical source fallback, and bot hook's isolated OFF/replay mechanics
run correctly on the user's Python environment.

**Not verified, not active:** connected four-code IBKR scanning,
production `RUDRA_SCANNER_MODE=shadow` connected run,
replacing the live import universe, 5M real WAP/VWAP,
the five actual LONG/SHORT setup detectors, shared Reversal
1H historical imports, scanner Discord alerts and hourly AI
refresh. The bot integration method is *wired but defaults OFF*;
existing Wicks and locked Rudra-Reversal logic unchanged.
Historical source is ONLY a testing substitute; no current
fundamentals/market cap inferred.

**Next step:** controlled live-session **shadow discovery verification**
using the existing IBKR app (only when user approves activation);
check callback statuses and DataLake outputs before changing any
live universes. Later implement real WAP capture, RTH VWAP,
signals and alert delivery with tests and separate state.
Do not invent signal thresholds or claim Sunday/weekend market data
is live. AI news CSV expires Monday Oct 12 12:00 UTC
(13:00 BST). Complete resumption checkpoint in
`RudraScanner/README.md` section “VERIFIED VPS CHECKPOINT”.

## 2026-10-10 Phase 2 implementation committed — 50 new/old test inventory

**User instruction:** implement the full RudraScanner system so they can
run an end-to-end VPS test even during the Saturday US-market closure.
The new code is on GitHub main, BUT **no new VPS run has been supplied
since the previous 24/24 verified tests**. Follow the latest
`RudraScanner/README.md` Phase 2 checkpoint and
`RudraScanner/FULL_TEST.md` first; do not equate code commits
with live verification.

### Existing five-minute Chakra pipeline integration

`ASJR_Analyst/Tests/test_asjr_pipeline.py` now at
`ASJR_ANALYST_VERSION = 2026.10.10.5`, referencing:

- `RudraScanner/bot_hook.py` —
  `RUDRA_SCANNER_MODE=off` default, `shadow` isolated
  discovery and diagnostic outputs, opt-in `active`
  common up-to-30 US-stock selected import set.
- `RudraScanner/wap_capture.py` and additive change in
  `ASJR_Analyst/Utils/asjr_ibkr.py` —
  actual IBKR bar WAP aligned to timestamp and attached to
  the existing six-field historical parse only when captured.
  RTH VWAP is not approximated silently from OHLC.
- `RudraScanner/features.py` —
  continuous cross-day/pre-market completed-bar EMA9,
  regular-session reset exact WAP VWAP, volume ratios,
  explicit missing quality diagnostics.
- `RudraScanner/volume_history.py` —
  preserve true cumulative RVOL20 from 20 prior **full**
  RTH sessions by carrying last 21 full sessions
  via `DataLake/YYYY-MM-DD/processed/rudra_scanner_rvol20_baseline.csv`.
  This stays within the one common DataLake and survives
  five-day old daily raw folder cleanup.
- `RudraScanner/patterns.py` and `topdown.py` —
  five symmetric experimental 5M LONG/SHORT research setups
  only when SPY/QQQ and sector ETF direction are aligned;
  unavailable or mixed => WAIT. Thresholds are provisional,
  still require user review and proper historical performance tests.
- `RudraScanner/engine.py`, `datalake_test.py` —
  common-day research feature CSV, status JSON and plain text
  outputs, read-only historical replay test.
- `RudraScanner/hourly.py` —
  with explicit ACTIVE mode, up to 30 1H stock historical
  IBKR requests on the same app, refreshed at most hourly;
  writes `raw/intraday_1h.csv` and status under common DataLake.
  Locked Rudra-Reversal evaluates those names plus existing
  Yahoo NQ without its BB math changing.
- `RudraScanner/reversal_bridge.py` —
  safely seed first-use stock symbols at latest completed 1H
  candle after >=150 bars; avoid alert floods from old history.
- `RudraScanner/delivery.py` —
  separate idempotent scanner Discord ack state; both
  `RUDRA_SCANNER_ALERTS=1` and
  `RUDRA_SCANNER_THRESHOLDS_APPROVED=1` required and
  **neither enabled/approved**. Research-only flag
  `RUDRA_SCANNER_RESEARCH=1` also OFF.
  Wicks and Reversal alert detector code unchanged.

**Production scope caution:** ACTIVE opts to replace imported
ticker set with the shared <=30 names and therefore *also changes
the names seen by existing Wicks* (not its wick rules).
User confirmation before enabling ACTIVE is required.
SHADOW mode preserves legacy monitored ticker list.
The actual VPS external EWrapper script has NOT been inspected
or verified against WAP tap. Live scanner, pacing, 1H coverage,
VWAP and Discord outcomes remain unknown. Production defaults OFF.

### Full offline test instruction on the user's VPS

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main
    /root/trading/venv_new/bin/python -m compileall -q RudraScanner ASJR_Analyst/Tests/test_asjr_pipeline.py ASJR_Analyst/Utils/asjr_ibkr.py
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
    /root/trading/venv_new/bin/python RudraScanner/bot_test.py --date 2026-10-09 --ibkr-source-date 2026-10-09
    /root/trading/venv_new/bin/python RudraScanner/datalake_test.py --date 2026-10-09

The source now contains **50 unittest methods** (original
24 VPS-verified plus 26 NEW and unverified test methods).
Expected 50/50 and successful read-only Friday input/feature
reports; **do not report PASS until actual VPS output arrives**.
Friday lacks actual WAP and 20 complete RTH sessions, so
exact VWAP/RVOL20 should report DATA NOT READY, never
fabricated live trade alerts. Weekend replay should remain
30/30 historical candidate lists, not live IBKR scanning.

**Next step:** inspect the user's 50-test output and fix any actual
failures; only after that consider controlled one-session
SHADOW mode with the user's approval and user-controlled bot
configuration/restart. Do not initiate live ACTIVE, Discord, or
automated trading without source/pacing/threshold validation.

## 2026-10-10 Phase 2 FINAL SOURCE TEST INVENTORY — 55 cases awaiting VPS

Following the prior Phase 2 implementation handoff, the user requested
complete setup detection and testing. Added
`RudraScanner/tests/test_patterns.py` with 5 synthetic
LONG+SHORT symmetric tests covering Hitchhiker, Back$ide,
Rubberband, Second Chance and Fashionably Late.
Improved optional IBKR historical WAP capture to scope sidecar
storage to registered 5M request IDs only, avoiding retention
of unrelated historic callbacks. Added an extra WAP timestamp
ordering test. `RudraScanner/tests/test_features.py` now
includes 9 feature/WAP tests. Current **source code count:
55 unittest methods total**, comprising 24 previously VPS
confirmed cases and **31 new, NOT YET VPS VERIFIED**.

Source docs and exact safe SSH procedures updated at:

- `RudraScanner/README.md` — newest Phase 2 checkpoint at top.
- `RudraScanner/FULL_TEST.md` — full 55-test
  runner and Friday read-only raw DataLake replay commands.

Latest exact full test sequence:

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main
    /root/trading/venv_new/bin/python -m compileall -q RudraScanner ASJR_Analyst/Tests/test_asjr_pipeline.py ASJR_Analyst/Utils/asjr_ibkr.py
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
    /root/trading/venv_new/bin/python RudraScanner/bot_test.py --date 2026-10-09 --ibkr-source-date 2026-10-09
    /root/trading/venv_new/bin/python RudraScanner/datalake_test.py --date 2026-10-09

**No restart or broker connection required for these weekend tests.**
`RUDRA_SCANNER_MODE` remains OFF by default; live SHADOW/ACTIVE
and scanner Discord are NOT user-activated or verified.
The user should send the 55-test output so failures can
be fixed before any live test. Exact WAP VWAP and RVOL20
correctly remain DATA NOT READY until real sources/history exist.

## 2026-10-10 USER VERIFIED 55/55 PHASE 2 TESTS — latest observed checkpoint

User supplied exact VPS results for the new complete offline test
sequence from `/root/trading/ASJR`.

- `python -m compileall -q RudraScanner
  ASJR_Analyst/Tests/test_asjr_pipeline.py
  ASJR_Analyst/Utils/asjr_ibkr.py` completed silently
  (no syntax errors).
- `python -m unittest discover -s RudraScanner/tests -p
  'test_*.py' -v` returned **Ran 55 tests in 0.531s; OK**
  with **0 test failures or errors**.
- `RudraScanner/bot_test.py --date 2026-10-09
  --ibkr-source-date 2026-10-09` returned an offline
  **30/30 source universe**, 10 fixed + 10 AI + 10
  historical legacy-mover IBKR substitutes, 84 candidates
  qualifying its incomplete archival price/volume screen.
  **No broker calls, no technical signals, no file save.**
- `RudraScanner/datalake_test.py --date 2026-10-09`
  returned **56,027 completed 5M bars / 106 historical
  tickers**, continuous EMA9 OK,
  **WAP_MISSING_OR_INCOMPLETE_RTH (0 exact VWAP rows)**,
  **INSUFFICIENT_20_FULL_RTH_SESSIONS (0 RVOL20 rows)**,
  `INDICATORS_ONLY`, detectors DISABLED, Discord DISABLED,
  no verified 5M pattern entry/exit signals.
  `TOP-DOWN context gate: 0` is NOT proof index/sector
  confirmation was executed, because pattern detector is OFF.

**Nonfatal issue:** pandas `FutureWarning` on concat of
empty rolling-volume DataFrame at
`RudraScanner/volume_history.py:89`. Follow-up **fix
committed** to avoid concatenating empty inputs, plus
`test_empty_prior_source_does_not_emit_futurewarning`
regression test in `tests/test_volume_history.py`.
**New total = 56 test methods, NOT yet VPS run for the fix**.
Expected result is zero warnings and same market-data
quality conclusions; never report follow-up PASS before
new actual user output.

**Remaining live acceptance tasks:**
audit actual VPS EWrapper scanner and historical callbacks,
test four new scanner codes on next regular US trading
session in isolated `RUDRA_SCANNER_MODE=shadow`,
verify actual WAP/5M and data alignment, 20 real complete
RTH sessions for RVOL20, per-symbol >=150 complete 1H
Reversal bars and stable pacing, establish source-verified
sector direction and final detector numerical settings.
Discord send gates still OFF; Wicks and original Reversal
detector logic unchanged. ACTIVE would change Wicks'
ticker universe and must not be enabled without approval.

**Next resumption path:** `RudraScanner/README.md`
section **VERIFIED VPS TEST — Saturday 2026-10-10,
55/55 PASSED** and `RudraScanner/FULL_TEST.md`.
Do not auto-restart the live Chakra bot.

## 2026-10-10 FINAL VPS REGRESSION CHECKPOINT — 56/56 PASS

**Latest user terminal evidence:** successful `git pull --ff-only
origin main` updated the VPS from `e3250e40` to `42c45aae`.
The full `RudraScanner/tests/` suite then completed:

    Ran 56 tests in 0.497s
    OK

**All 56 tests passed with no errors, failures or pandas FutureWarning.**
This includes `test_empty_prior_source_does_not_emit_futurewarning`,
proving that the previously noisy `volume_history.py` empty
baseline concat fix works on the user's real Python environment.
This supersedes the earlier "56th test pending" notes.

**Verified test scope:** offline 5M EMA9 and synthetic exact-WAP
VWAP guards, 20-session RVOL tests, five bidirectional synthetic
detector scenarios, source-cap logic, fake-IBKR 1H requests,
safe first-use Reversal state, safe Discord dedup/ack unit tests,
historical offline 30/30 candidate replay.
Prior actual 2026-10-09 historical raw DataLake smoke test
returned 56,027 completed 5M candles across 106 tickers and
correctly reported unavailable actual WAP VWAP / RVOL20.
No actual live 4-code IBKR scanner run or live alert was
performed. Existing Chakra is still feature-gated OFF.

**Next permitted controlled milestone:** audit the external
deployed `/root/trading/utils/trading_sudarsan_chakra.py`
and real `EWrapper` scanner/historical callbacks, then
enable only SHADOW during a regular US market session
with user-controlled process configuration and restart.
Verify real candidate/source counts, valid current stock
contracts, actual WAP and timestamps, data freshness,
1H warm-up and pacing before ACTIVE or Discord.
ACTIVE would change ticker coverage of the existing Wicks
detector despite unchanged rules: explicit approval needed.
AI research CSV expires Monday Oct 12 at 12:00 UTC
(13:00 UK) and must be refreshed before US open.

Canonical current checkpoint:
`RudraScanner/README.md` section "CURRENT VERIFIED STATE —
2026-10-10: 56 / 56 VPS tests passed" and
`RudraScanner/FULL_TEST.md`.

## 2026-10-10 Friday Oct 9 one-round retrospective scanner replay COMMITTED

User requested running the **full RudraScanner five-pattern code
for Friday 2026-10-09** without restarting the closed-market
Chakra bot. New source committed on main:

- `RudraScanner/friday_round.py`: direct standalone
  one-session command. Uses existing `features.py` and
  `patterns.py`; frozen previously verified Friday
  30 candidate names (10 FIXED + 10 Saturday AI +
  10 historic Friday mover-list). Friday session is evaluated
  **bar by bar**, no later OHLC, index or sector ETF close
  can be used in an earlier signal.
- Requires exact real IBKR historical TRADES WAP and
  previous RTH close + timestamp-matched SPY/QQQ and sector
  ETFs for a research setup. No HLC3 VWAP substitution.
  Archived `raw/intraday_5m.csv` has no WAP and is
  expected to print **NO EVALUABLE SIGNALS** and
  explicit blocker counts; this is **not** a backtest with
  zero wins or zero profits.
- Optional `--download-ibkr` uses a NEW isolated,
  read-only `ib_async.IB` connection (clientId 91
  by default) to the user's **already running** Gateway;
  historical TRADES `BarData.average` supplies actual
  bar WAP. Requests up to 30 stocks + SPY/QQQ/sector
  ETFs; no orders, no Chakra process changes, no Discord
  or automated Git push. The Gateway may be unavailable
  on the weekend; code reports errors honestly.
- Namespaced test-only input and result paths in
  `ASJR_Analyst/DataLake/2026-10-09/`:
  `raw/rudra_friday_ibkr_wap.csv`,
  `reports/rudra_friday_ibkr_backfill_status.json`,
  `reports/rudra_friday_round_status.json`,
  `reports/rudra_friday_round_markouts.csv` (results
  only saved via `--save`).
- Research exit sample: signal confirmed on completed
  5M candle, hypothetical next bar open, exit at close
  6 bars after signal (30-minute horizon); no fees,
  spread/slippage, risk exits or position cap. Requiring
  strictly consecutive bars avoids inventing a 30-min
  markout when history has gaps.
- Frozen Friday 30-selection list was produced
  **after Friday market close** from Saturday research
  and archived mover screens: severe **lookahead / hindsight
  universe bias**. This tool tests retrospective technical
  pattern feasibility only; NOT as-of-open SMB discovery
  or validated trading P&L. No historical profits claimed.
- New `RudraScanner/tests/test_friday_round.py`
  includes **8 new unit tests** for missing actual WAP,
  missing/stale benchmark, future-free index/sector
  context, markout entry/exit alignment and date checks.
  **Suite source total now 64**, up from the prior
  verified 56/56. The NEW tests have **not** been
  executed/verified on user VPS yet.

Read full instructions: `RudraScanner/FRIDAY_REPLAY.md`;
latest resumption note at top of
`RudraScanner/README.md`.

**Immediate read-only SSH commands:**

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
    /root/trading/venv_new/bin/python RudraScanner/friday_round.py --date 2026-10-09

**Optional connected Friday WAP backfill (requires an existing
running IBKR Gateway and the user's choice to run it):**

    /root/trading/venv_new/bin/python RudraScanner/friday_round.py --date 2026-10-09 --download-ibkr --host 127.0.0.1 --port 4002 --client-id 91 --save

Do not claim these tests have passed or quote a Friday
win rate without actual user VPS results. Production
`RUDRA_SCANNER_MODE=off`; locked Wicks/Reversal untouched.

## 2026-10-10 verified Friday IBKR 40-instrument WAP replay — first real pattern research result

The user ran:
`/root/trading/venv_new/bin/python RudraScanner/friday_round.py
--date 2026-10-09 --download-ibkr --host 127.0.0.1
--port 4002 --client-id 91 --save`.
An initial "No such file" was due only to not yet pulling the
committed file; a subsequent `git pull` fast-forwarded to
`940f949d` and the run succeeded.

**ACTUAL VPS evidence:**
- 40/40 historical IBKR instrument requests completed,
  `failures = {}`; 30 retrospective stocks + SPY/QQQ +
  eight sector ETFs, **22,290 actual 5M OHLCV/WAP bars**,
  **9,360** valid RTH WAP-weighted VWAP bars.
- **2,160** RTH stock bars after the opening execution
  gate; **1,853** missing/mixed index-sector directional
  context; 36 insufficient pattern lookback; 8 pattern
  hits with insufficient complete 30-minute forward
  bars; missing WAP 0.
- Raw detector labels: **11 LONG pattern hits**,
  **5 positive, 6 negative** for a provisional next-open
  to six-bars-later close markout, **45.45%** positive,
  mean **+0.0311% per pattern hit before costs**.
- By pattern: HITCHHIKER 6, 2 positive, mean −0.0364%;
  BACK$IDE 4, 2 positive, mean +0.0914%;
  SECOND CHANCE 1, 1 positive, +0.1947%;
  RUBBERBAND 0; FASHIONABLY LATE 0.
- AMZN 2026-10-09 20:25 BST generated both
  HITCHHIKER and SECOND CHANCE with the SAME
  entry at 20:30 UK and SAME +0.1947% 30m
  markout. These cannot be counted as separate
  portfolio entries. **10 distinct entry opportunities,
  4 positive, 6 negative, 40% positive,
  +0.0147% mean before costs** (simple same-ticker/
  side/entry-time deduplication). Other entries can
  overlap within a ticker.
- Best recorded markout HUM +0.6329% (BACK$IDE);
  worst AMT −0.5489% (HITCHHIKER).
- `real_live_signals: 0`, `discord_sent: 0`,
  `orders_sent: 0`; saved the historical WAP CSV
  and research report only under
  `ASJR_Analyst/DataLake/2026-10-09/`.
  The historical API backfill does NOT verify the
  upcoming real-time four-code scanner.

**Cautions:** this universe includes Saturday AI research
and Friday after-close movers, creating hindsight selection
bias. One day cannot establish an edge. Pattern thresholds
remain provisional, and the exit is a temporary 30-minute
markout, not a user-approved exit/SL. Returns exclude spread,
fees, slippage, execution and short borrows. Counting
+0.0311% as tradeable expected net profit would be misleading.

**Follow-up GitHub code committed AFTER that observed test:**
`RudraScanner/friday_round.py` now additionally produces
`distinct_entry_opportunities`,
`overlapping_pattern_labels`,
`distinct_entry_win_rate_pct`,
`distinct_entry_average_markout_pct` and
per-pattern win/mean statistics. The prior raw pattern ledger
is retained for research. A ninth Friday unit test checks
duplicate-pattern handling; the existing markout
unit test was corrected to respect the 15-bar
detector warm-up. **Suite now 65 source tests**:
56 previously VPS PASSED + 9 NEW Friday replay tests
NOT YET CONFIRMED on the VPS. Do not claim 65/65 PASS
until user supplies new output.

**Next run does NOT require new IBKR requests**; Friday
`raw/rudra_friday_ibkr_wap.csv` is already cached:

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
    /root/trading/venv_new/bin/python RudraScanner/friday_round.py --date 2026-10-09 --save

Complete explanation and actual Friday summary:
`RudraScanner/FRIDAY_REPLAY.md`, and newest
`RudraScanner/README.md` resume checkpoint.
No bot restart or scanner Discord approval occurred.

## 2026-10-10 12:41 UTC Friday retest: 64/65 tests, mock warm-up issue fixed

The user shared their second Friday full-suite command and
saved report from VPS after pulling `940f949d..9fc0dbf6`
on main. The unit suite returned:

    Ran 65 tests in 0.746s
    FAILED (failures=1)

**Exact failure:** `test_friday_round.FridayReplayTests.
test_markout_entry_next_bar_and_exit_after_six`.
The test monkeypatched `detect_five_patterns()` with
an unconditional fake signal, allowing index 6
(30-minute RTH gate). However, the assertion
correctly expected actual pattern minimum 15
completed bars (index >=14). This was a **test
mock bug**, not a verified live strategy flaw.

**Code fix committed to main:** only
`RudraScanner/tests/test_friday_round.py`
was changed: `fake_signal()` now blocks signals
when `len(bars) < 15` (reports
`blocked_data=1`), mirroring the production
detector's warm-up. All real scanner detection,
data import, alert sending and exit analysis code
remains unchanged. **The corrected 65-test suite
is pending VPS re-execution**, not yet 65/65 PASS.

**User's Friday WAP research results remain valid
as generated:** 22,290 historical IBKR WAP
5M bars across 40 instruments; 9,360 RTH VWAP
ready. 11 labelled signals = 10 unique
entry opportunities after one duplicate AMZN
pattern label. 4 positive and 6 negative unique
hypothetical next-bar-entry / 30-minute markouts;
40.0% positive, +0.0147% mean before fees,
spread or slippage. No orders/Discord,
hindsight universe and experimental setups.

Next safe SSH command after pull:

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v

No IBKR backfill required; already cached.
Canonical resumption notes in
`RudraScanner/README.md` and
`RudraScanner/FRIDAY_REPLAY.md`.

## 2026-10-10 12:46:59 UTC — final Friday replay unit test suite VERIFIED 65/65

User performed successful fast-forward pull from `9fc0dbf6` to
`368cf6d3` in VPS `/root/trading/ASJR`, then ran:

    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v

**Real SSH output: `Ran 65 tests in 0.784s; OK`. All 65 passed, zero
errors/failures.** This includes the corrected mocked early-entry
test `test_markout_entry_next_bar_and_exit_after_six`:
the fake pattern now respects the real detector's 15 complete RTH
bar lookback. Previous 64/65 failure is resolved and VERIFIED.
No real detector rule, Wicks, Reversal or Chakra production logic
changed in that specific unit-test fix.

**Friday historical research evidence from prior actual VPS run:**
40 IBKR stocks/ETFs, 22,290 genuine historical 5M WAP
bars, 9,360 valid RTH VWAP-ready bars, 11 experimental LONG
pattern labels but only 10 unique entry opportunities
(4 positive, 6 negative, 40% positive; mean +0.0147%
hypothetical six-bar / 30-minute markout BEFORE trading costs).
Candidate selection used after-close/Saturday information;
consequently this is hindsight-biased research, not an
as-of-market-open stock-scanner backtest, nor proof of a
profitable strategy. The user's Friday IBKR data is cached
in common `ASJR_Analyst/DataLake/2026-10-09/raw/rudra_friday_ibkr_wap.csv`
on VPS; no need to redownload for further Friday replay.

**Current stage:** all 65 source unit tests offline-VPS verified.
LIVE four IBKR scanner discovery codes, actual live WAP/5M
callbacks, 1H shared stock-history readiness, live Discord
scanner alerts and performance remain unverified. Production
`RUDRA_SCANNER_MODE=off` by default; keep existing Wicks
and locked Reversal unchanged. Next after user approval:
controlled single US market session `shadow` test via
existing Chakra connection, preserving original live universe.
New status canonical at top of `RudraScanner/README.md`
and `RudraScanner/FRIDAY_REPLAY.md`.

## 2026-10-10 MONDAY 12 OCT LIVE CHAKRA SHADOW — CODE COMMITTED, VPS TEST PENDING

**User instruction:** Apply ALL RudraScanner code to the existing
live scanner for Monday 12 Oct, review integration and update docs.
This is the latest state and supersedes prior "Monday
SHADOW not implemented" checkpoints. Read
`RudraScanner/MONDAY_LIVE.md` FIRST for commands,
rollback and exact operational constraints.

**GitHub/main changes committed** (NOT yet reloaded into VPS process):

- New `ASJR_Analyst/config/rudra_scanner_runtime.json`:
  date-gated `enabled_from_et=2026-10-12`,
  `mode=shadow`, `research=true`,
  **scanner Discord alerts FALSE** and pattern-threshold
  approval FALSE. Production source watcher remains
  the existing `ibkr_trading_sudarsan_chakra(app)`;
  no new scheduler/broker connection/order function.
- Existing `ASJR_Analyst/Tests/test_asjr_pipeline.py`
  is version **2026.10.10.12** and installs passive
  IBKR WAP tap before the legacy 5M fetch (no added
  requests at this step), then delivers original
  **WICKS and locked 1H Reversal alerts BEFORE**
  four-code discovery or extra 5M/1H sidecar loads.
  `uni = universe.build_universe(...)` unchanged,
  `run_rudra_reversal_strategy(trade_date=...)`
  unchanged; new selected 30 names NEVER replace
  Wick/Reversal live name universe in SHADOW.
- `RudraScanner/bot_hook.py` hot-reads
  date-gated runtime configuration and runs
  TOP_PERC_GAIN, TOP_PERC_LOSE, HOT_BY_VOLUME and
  MOST_ACTIVE, capped 10 fixed + 10 valid AI +
  10 IBKR, no fixed 4% condition.
  SHADOW now returns selected candidates for 5M
  import, rather than just counts.
- New `RudraScanner/live_round.py` computes
  genuine completed 5M EMA9 and RTH reset VWAP
  from IBKR WAP, persistent RTH RVOL20 baseline,
  and all five bidirectional pattern detectors.
  Reuses already imported legacy WAP bars, loads
  only missing stocks+SPY/QQQ/evidenced sector
  ETF 5M bars from SAME app. Directional context
  uses timestamp-matched completed 5M ETF prices
  versus PRIOR RTH close (avoids future-close).
  Unknown ETF/missing WAP = WAIT.
  Saves `ASJR_Analyst/DataLake/2026-10-12/
  reports/scalp_radar.txt` and JSON/CSV.
  No additional top-level DataLake.
- Existing `RudraScanner/hourly.py`
  caches the selected 1H stock source once per
  hour. Under SHADOW it does NOT seed, rewrite
  or run locked Rudra Reversal on new names;
  Yahoo NQ and original 1H Reversal alerts remain
  unchanged.
- `RudraScanner/delivery.py` adds separate
  state/ACK and batch for scanner research
  Discord, integrated at LAST priority in
  `ASJR_Analyst/Utils/asjr_alerts.py`
  `prepare_alert()`, `mark_alert_sent()`
  and optional `send_alerts()`.
  This was designed around previously observed
  external Chakra pattern:
  `tp.run_asjr_manual_pipeline(...)`
  -> `tp.prepare_alert(result)` -> `SN.send_to_discord`.
  Actual `/root/trading/utils/trading_sudarsan_chakra.py`
  is **not available in GitHub** and cannot be
  definitively reviewed without user VPS output.
  Scanner messages are **OFF in config** pending
  user-approved numerical thresholds. No orders.
- New `RudraScanner/live_preflight.py`:
  direct SSH read-only readiness (0 IBKR
  requests, 0 orders, 0 Discord).
  New `tests/test_live_round.py` (7),
  `tests/test_live_preflight.py` (2),
  `tests/test_pipeline_bridge.py` (5),
  plus 2 new queue tests in `test_delivery.py`.
  Total **81 source tests = 65 previously VPS
  verified + 16 NEW UNVERIFIED**.
  Do not claim 81/81 passed without VPS output.

**Important blocker in separate AI hourly workflow:**
Attempt to create new 8–20 UK weekday
AI research + GitHub CSV updater AUTOMATION
FAILED because the user has reached their
5-active-task limit. The existing Saturday AI
CSV snapshot expires Monday 2026-10-12
12:00 UTC (13:00 UK), BEFORE Monday US RTH.
Unless refreshed, 10 AI source slots are
not assured. DO NOT imply the AI hourly
GitHub CSV updater is running. It must
be scheduled after user makes a task slot,
or researched/updated manually.

**Mandatory immediate read-only VPS verification:**

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main
    /root/trading/venv_new/bin/python -m compileall -q RudraScanner ASJR_Analyst/Tests/test_asjr_pipeline.py ASJR_Analyst/Utils/asjr_ibkr.py ASJR_Analyst/Utils/asjr_alerts.py
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
    /root/trading/venv_new/bin/python RudraScanner/live_preflight.py

Expected **81 tests**, OK; **NOT YET USER VPS VERIFIED**
for new code. If tests fail, fix GitHub before
any user-controlled restart. Git pull alone
does not reload an existing tmux Python process.
User controls restart via their established
Discord bot control commands; never start a
second process automatically.

**Monday acceptance:** After the user
restarts/reloads the existing bot AND
confirms 81/81 tests, verify version
2026.10.10.12 in Chakra logs, legacy
Wicks/Reversal immediate dispatch, scanner
4-code actual result/partial statuses, <=30
separate stocks, WAP/timing/ETF 5M context
and the shared DataLake report. FIRST
US RTH open is 14:30 UK BST, pattern
research after 15:00 UK. 20-day RVOL20
will remain unavailable until 20 complete
prior RTH days have been collected.
Inspect IBKR pacing and Git sync,
as shadow extra history increases demand.

**SAFE rollback:** set scanner runtime
`mode=off` or process env
`RUDRA_SCANNER_MODE=off`, Git pull/reload
normal process. Never modify Wicks/Reversal
rules, current open positions, historical
data or alerts to force scanner to work.

**No live claims beyond code:** 65/65
prior offline unit tests VERIFIED, Friday
40-history-contract WAP fetch worked,
but Monday real 4-code callbacks, streaming
WAP, 81 new-case suite, source freshness,
real Discord scanner delivery and timing
remain UNVERIFIED.


## 2026-10-10 13:24 UTC — user VPS MONDAY LIVE preflight 81/83; 2 test-only failures fixed

Actual user-supplied console, after fast-forward
`368cf6d3..1ce9a402` on GitHub main:
`Ran 83 tests in 0.972s; FAILED (failures=2)`.
The 2 failures were **only**:
`test_external_mark_sent_falls_through_to_scanner_ack`
(count 0 rather than 1) and
`test_scanner_batch_after_internal_wicks_reversal_dispatch`
(empty string rather than "QUEUED RESEARCH").
The tests had not mocked the current approved-scanner Discord
runtime gate. Production's `_scanner_queue_approved()`
CORRECTLY blocks scanner sends/ACKs when
`alerts_enabled=false` or
`thresholds_approved=false`. Fixed both **TESTS ONLY**
by mocking the approved state for the tested branch.
No live alert approval and no locked strategy code changed.
**Actual 83/83 re-run still PENDING user VPS output.**

Preflight reported `ready_to_shadow=true` (code
configuration checks only; DOES NOT verify connected
IBKR/live market scan), `scheduled_mode=shadow`,
`research_enabled=true`, but scanner Discord flags
both false, original Wicks/Reversal hooks present and
no broker/Discord actions in preflight. It also showed
`fixed_today=0`, `fixed_state=MISSING`,
`ai_valid_at_monday_open=1`,
`ai_expired_at_open=10`.

To fix the Monday fixed list **without changing legacy
strategy membership**, created
`ASJR_Analyst/DataLake/2026-10-12/config/fixed_watchlist.csv`
as an exact copy of Friday 2026-10-09 fixed CSV
(19 rows, includes INTC, AKAM and WTTR).
The RudraScanner selector will rank at most 10
FIXED stocks, and exclude ONDS from Scanner even though
original Wicks watchlist membership remains unmodified.
After VPS git pull, preflight should find the Monday file.
This new input has NOT YET been VPS verified.

The expiring AI research CSV is still a material
coverage blocker: ten rows expire Monday October 12
12:00 UTC / 13:00 BST, with only permanent
unverified INTC remaining, and it overlaps fixed.
Do NOT claim full AI 10-stock discovery or 30/30 total,
extend dates without sourced new research, or
silently use Friday news as fresh Monday catalysts.
No configured hourly AI-to-GitHub writer exists.
Monday SHADOW can still test four-code IBKR discovery
with a partial source universe.

**Next safe VPS step (do NOT restart bot first):**

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main
    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
    /root/trading/venv_new/bin/python RudraScanner/live_preflight.py

Expected: 83 tests OK (not yet verified); fixed no
longer MISSING. Continue only with user-controlled
restart after confirming actual test result and
external launcher/Discord callback compatibility.
Full up-to-date checklist:
`RudraScanner/MONDAY_LIVE.md`; primary overview:
`RudraScanner/README.md`.

## 2026-10-10 13:30 UTC — VERIFIED Monday SHADOW preflight 83/83 PASS

The user ran the complete test suite after
`git pull --ff-only origin main`, updating the VPS from
`1ce9a402` to `2d1ee811`. Actual console result:

    Ran 83 tests in 0.887s
    OK

**All 83 tests passed, zero errors/failures.** Both
previously failing Discord bridge tests
`test_external_mark_sent_falls_through_to_scanner_ack`
and `test_scanner_batch_after_internal_wicks_reversal_dispatch`
now pass after the test fixtures were corrected to simulate
explicitly approved alerts. The *real* Monday Scanner
Discord gating remains OFF / fail-closed.

**Actual read-only `RudraScanner/live_preflight.py`
output** for Monday Oct 12:
`scheduled_mode=shadow`; `research_enabled=true`;
`live_scanner_alerts_enabled=false`;
`approved_thresholds=false`;
`ready_to_shadow=true`;
`fixed_today=18` and `fixed_state=PARTIAL`
because Friday's 19-row copied fixed list contains
the expressly excluded ticker ONDS (excluded in
RudraScanner, without changing legacy Wicks).
`ai_valid_at_monday_open=1`,
`ai_expired_at_open=10` and
`ai_state_at_monday_open=PARTIAL`.
The one nominally still-valid AI row is permanent
INTC watch; it overlaps fixed names, so it is not
ten newly sourced AI candidates. Four scanner
code strings, existing Chakra, Wicks and locked
Reversal and Discord queue interfaces passed
static preflight existence checks. This command
made **0 broker requests, 0 orders and 0 Discord sends**.

**Unverified / next milestone:** GitHub code and
VPS checkout pass offline tests, but the long-running
Chakra Python process may still be using earlier
modules until a user-controlled restart. The actual
external EWrapper callbacks, connected four live
IBKR scanners, 5M WAP, ETF times, same-time
pattern state and scanner-only common DataLake
output are still not verified. Production scanner
Discord remains disabled during SHADOW. The
user's workflow is to verify external launcher
and process environment, optionally restart via
`!mbdstop` / `!mbdstart` after code/test
acceptance, then inspect:

    /root/trading/venv_new/bin/python RudraScanner/live_status.py --date 2026-10-12

Ensure live legacy Wicks and Reversal continue to
function. Automatic hourly AI-to-GitHub research
remains absent; do not silently keep expired ten
AI tickers. No 30/30 live selection is yet proved.
Further details:
`RudraScanner/MONDAY_LIVE.md` and
`RudraScanner/README.md`.

## 2026-10-10 15:19 UTC — existing Discord bot Git commands: ONE handler

The user showed their existing bot command pattern
`if text.startswith("!NEWS"): ... await message.channel.send(result)`
and explicitly requested **one reusable method** for
`!gitpull` and `!gitpush`, not an additional bot or
multiple methods.

Implemented:
`ASJR_Analyst/Utils/discord_git_commands.py`
exports the single callable `run_git_command(text, author_id)`.
It returns the full Discord-ready success/failure/exception message,
and recognizes EXACT `!GITPULL` and `!GITPUSH` (case-insensitive).
`!gitpull` = `git pull --ff-only origin main` and
`!gitpush` = `git push origin main`, from
`/root/trading/ASJR`. It does not stage/commit,
force-push, stash, reset or create a new bot.
It verifies branch and intended origin, blocks
concurrent Discord Git calls, and fails closed for
non-authorised user IDs via
`ASJR_DISCORD_GIT_ALLOWED_IDS` environment variable
or explicit `allowed_ids` function argument.
All command exit errors and exceptions return
a short message instead of raising into Discord.
Use `asyncio.to_thread` from Discord async handler
to avoid blocking messages while Git runs.

Paste at TOP of existing external Discord bot Python file:
```python
import asyncio
import sys
sys.path.insert(0, "/root/trading/ASJR/ASJR_Analyst")
from Utils.discord_git_commands import run_git_command
```

Paste in EXISTING bot on_message command chain:
```python
if text.strip().upper() in ("!GITPULL", "!GITPUSH"):
    result = await asyncio.to_thread(
        run_git_command, text, message.author.id,
        allowed_ids={YOUR_NUMERIC_DISCORD_USER_ID},
    )
    await message.channel.send(result)
    return
```
Replace `YOUR_NUMERIC_DISCORD_USER_ID` with the user's
actual Discord numeric ID; never invent this number.
Alternatively omit `allowed_ids` only after setting
`ASJR_DISCORD_GIT_ALLOWED_IDS` in the running bot environment.
No modification to external bot script was possible via
GitHub: that bot resides outside the repo on VPS.
After Git pull and bot restart, user must paste the
handler block and test both Discord commands.
