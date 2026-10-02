# ASJR Analyst operational handoff

Updated 2026-10-01 (UK). This records the implementation and observed state for Rudrakchhya and future ASJR sessions. Check the current Git branch, VPS logs and today's DataLake files before treating a run as live-verified.

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

