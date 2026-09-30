# ASJR Analyst operational handoff

Updated 2026-09-30 (UK). This records the implementation and observed state for Rudrakchhya and future ASJR sessions. Check the current Git branch, VPS logs and today's DataLake files before treating a run as live-verified.

## Maintenance rule

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
