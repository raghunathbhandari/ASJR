# ASJR / Chakra / Rudra-Premarket — AI SESSION HANDOFF

## 2026-10-11 ~16:00 UK — Completed code stage for gated BUY WATCH, NOT DEPLOYED

User authorized full new Rudra-Premarket alert implementation and a safe Chakra restart once verified. GitHub commits now include:
- `RudraScanner/premarket_live.py`: evaluates the **latest completed and fresh 5-minute bar** using continuous EMA9, verified IBKR historical-bar WAP weighted into a strict contiguous-session cumulative VWAP for PRE/RTH/POST, and saved five-session same-segment cumulative RVOL; rejects 09:30–10:00 ET, no missing volume filled, no stale replay. `prepare` formats grouped UK-time BUY WATCH message; `acknowledge` persists sent keys only AFTER existing Chakra Discord success.
- `RudraScanner/premarket_alert_config.json`: **enabled=false, auto_backfill=false**. This is intentional. A Git pull or restart CANNOT cause new experimental BUY WATCH messages or background imports unless both respective gates are deliberately switched and VPS tested.
- `ASJR_Analyst/Tests/test_asjr_pipeline.py` version `2026.10.11.7`: canonical hook installs WAP callback before legacy same-app 5m fetch, calls live evaluator in SHADOW, reads durable RVOL5, adds selected AI/IBKR scanner extra WAP bars to final alert evaluation, retains existing Reversal/Wicks/snapshot/Git flow, exposes signal events/quality. `prepare_alert(result)` uses existing external `SN.send_to_discord` wrapper, joins premarket message when enabled, `mark_alert_sent()` acknowledges after successful send. The original canonical function is now `_run_asjr_manual_pipeline_unlocked`, called via locked public `run_asjr_manual_pipeline(...)`.
- `RudraScanner/premarket_live_backfill.py`: *gated* three-worker historical import for new selected tickers (one IBKR history request at a time, max three ticker requests per full cycle, atomic shared reference merge, no duplicate same-day attempt). Invoked after other scanner broker stages, with SAME app, and joins workers before pipeline finishes.
- `RudraScanner/run_now.py`: manual started-app path reuses current lock and passes controlled environment flag into pipeline. `--dry-run` explicitly never queues broker work.
- `RudraScanner/install_chakra_round_lock.py`: reversible **external VPS launcher patch**, required for a full lock covering both canonical pipeline and original Discord send/ACK. `--check` only validates safety, `--apply` creates timestamped backup before patching `/root/trading/utils/trading_sudarsan_chakra.py`; does not change its trading/data/Discord body. DO NOT apply/restart without first passing tests and reviewing output.
- New offline tests: `test_premarket_live.py`, `test_premarket_live_backfill.py`, `test_chakra_round_lock_install.py`, revised `test_run_now.py`; `check_chakra_launcher.sh` compiles new modules, executes targeted unit tests, performs read-only launcher patch preview and non-broker dry-run.

**CRITICAL DEPLOYMENT STATUS**: NO VPS test output has been received for these new post-version-2026.10.11.7 changes. Earlier 9/9 RVOL/backfill and 3/3 or 4/4 run_now tests are OLD and do NOT establish that new code works. No live BUY WATCH delivery was tested, none enabled. User asked "can I restart BOT now?": wait for green offline tests. After pull:
```bash
cd /root/trading/ASJR
git pull --ff-only origin main
bash RudraScanner/check_chakra_launcher.sh
```
This is NO BROKER / NO ALERT test. If PASS, next carefully inspect output and run reversible lock installer with `--apply` ONLY with bot stopped and user approval, then restart bot in SHADOW (both gates still off), and verify normal Chakra logs. The user may enable live messages only after a real market-cycle quality check and explicit gate commit.
**Unresolved specification discrepancy**: TV-style "1 Day Anchor" cumulative RVOL could cross PRE/RTH/POST, while this implementation computes cumulative RVOL separately within each segment; user confirmation needed before claiming indicator parity. Current complete-history data ready: 30 RTH, 30 POST, 26 PRE, stored 27,744 rows at durable state. Date-folder cleanup task was updated to preserve durable RVOL baseline.
**Possible alert delivery tradeoff**: message is appended to other active alert text through single existing external Chakra send. Combined message should be bounded to Discord's limit before enabling if scanner/reversal messages can be lengthy.
**No production claim** until operational logs prove signal timing, exact VWAP, selected AI names, dedup, Discord ACK, and cross-process lock.

---


## 2026-10-11 ~15:53 UK — New shadow signal hook; DO NOT RESTART FOR LIVE ALERTS YET

User authorized implementation of live Rudra-Premarket alerts. Partial, **not yet production-ready**, commits:
- `RudraScanner/premarket_live.py` evaluates completed EMA9, IBKR WAP VWAP and durable RVOL5, prepares formatting and persisted acknowledgement helpers.
- `RudraScanner/premarket_alert_config.json` deliberately `enabled: false`; no Discord BUY WATCH may be sent.
- `ASJR_Analyst/Tests/test_asjr_pipeline.py` version `2026.10.11.3` installs WAP callback capture before existing 5m fetch and executes a guarded SHADOW `evaluate_premarket` on renamed 5m raw bars. Fixed prior erroneous `update_premarket_history(intraday,...)` input: now uses `prem_raw` with lowercased ticker/datetime/volume. Need Python compilation + end-to-end tests, and robust init when raw feed absent.
- **Major blocker**: `RudraScanner/features.build_scanner_features` computes WAP-based VWAP for RTH only, NOT PRE/POST. Thus premarket and after-hours signal logic is not ready; VWAP user requirements cannot be claimed implemented. Live current-bar completeness, UK time, state/dedup ACK, external Chakra Discord integration and cross-process scheduler lock need test and additional wiring.
- `--premarket-test` still does not guarantee alerts are suppressed in full standalone mode; regular Chakra messages may be sent. Do NOT restart bot with these new commits on assumption they are tested. User needs clear warning.

---


## 2026-10-11 ~15:46 UK — RVOL5 RETENTION PROTECTION / CLEANUP CONTRACT

User requires automatic five-day DataLake cleanup to **never delete the last five usable RVOL5 historical sessions**. Implemented code changes:
- `RudraScanner.premarket_rvol.durable_reference_path(ROOT)` points to `ASJR_Analyst/state/rudra_premarket_rvol5.csv` (OUTSIDE `DataLake/YYYY-MM-DD`). `update_history` reads durable baseline first; whenever `save=True`, writes both daily `DataLake/YYYY-MM-DD/processed/rudra_premarket_rvol_history.csv` and durable state atomically.
- `RudraScanner/import_premarket_history.py` merges newly fetched profiles with existing durable/daily references, preserving other ticker histories across import batches, and writes both destinations. Never rerun an old unpatched importer after the initial reference is protected.
- `RudraScanner/protect_rvol5_history.py --for-day 2026-10-12` migrates existing 27,744-row daily reference (actual post-validation row count to be checked) to durable state without IBKR, shows rows/tickers/ready session groups, and fails closed on invalid source.
- **The actual VPS five-day deletion cron/script lives outside verified ASJR repo files or has not yet been identified; it has NOT been modified or audited.** Before running cleanup, confirm that it only targets date-stamped `ASJR_Analyst/DataLake/YYYY-MM-DD`, NEVER `ASJR_Analyst/state`, and does not delete the baseline before migration. Ideally add a guard to the real cleanup job to verify a readable durable file with five completed sessions per eligible ticker/segment, or preserve dated source until guard passes. Durable baseline is a compact rolling cache; long-term research raw files are subject to separate policy.
- Operational migration:
```bash
cd /root/trading/ASJR
git pull --ff-only origin main
/root/trading/venv_new/bin/python RudraScanner/protect_rvol5_history.py --for-day 2026-10-12
```
Do this BEFORE automatic cleanup deletes 2026-10-12 reference. Verify output. Future scheduled pipeline uses the durable state automatically after next code load/restart. No live Bot restart verified.

---


## 2026-10-11 ~15:44 UK — VERIFIED RVOL5 REFERENCE COVERAGE

User inspected `ASJR_Analyst/DataLake/2026-10-09/reports/rudra_premarket_backfill.json` on VPS. Actual output: `FETCHED: 30`; reference exists at `ASJR_Analyst/DataLake/2026-10-12/processed/rudra_premarket_rvol_history.csv`; `REFERENCE ROWS: 27744`. Per-segment complete historical sessions: **RTH >=5 for 30/30; POST >=5 for 30/30; PRE >=5 for 26/30**. Four PRE not ready: WTTR=1, OPRX=0 (absent PRE in report), AMT=2, HUM=1. NXPI PRE=9, TMUS PRE=8, FSLY PRE=9; other ready PRE generally 10. Many RTH and POST report 10 prior complete sessions, but the saved reference module `_clean_reference` retains only LAST FIVE per ticker/segment; do not confuse raw coverage counts with stored 5-session baseline.

**Important limitations:** This is VERIFIED historical reference coverage, not live RVOL computation or live alert tests. Do not interpret missing PRE as zero volume. Do not rerun another import that overwrites the Monday reference without implementing a reference MERGE. Newly imported data exists locally on VPS, not automatically Git-synced.

---


## 2026-10-11 ~15:42 UK — VERIFIED FIRST HISTORICAL FETCH RESULT (user VPS log)

The user ran `/root/trading/venv_new/bin/python RudraScanner/import_premarket_history.py --day 2026-10-09 --max-tickers 30`. Terminal printed `RUDRA IMPORT | FINISHED .../2026-10-09/reports/rudra_premarket_backfill.json` with **30 of 30 ticker requests successful**, no reported historical fetch errors. All used the existing Gateway helper and IBKR client ID 656; volume of data varied (common 1,920 bars, NXPI 1,884, WTTR 1,413, OPRX 1,267, AMT 1,533, HUM 1,444, TMUS 1,906, FSLY 1,912). Fixed list 19 rows, 18 included, ONDS excluded; AI 14 enabled; saved Friday IBKR mover source 87 symbols (not a Sunday live scan). Selected 30 in source order: MSFT CRDO SMCI QCOM AMAT ORCL WDC MRVL LRCX NXPI AKAM WTTR MCHP OPRX MU CAT TSLA INTC SPCX PLTR LITE AMT HUM AMZN TMUS AAPL JPM NVDA FSLY NVAX.

**DO NOT CLAIM RVOL5 READY.** The terminal output does not print `complete_prior_sessions`, reference row count or whether `2026-10-12/processed/rudra_premarket_rvol_history.csv` exists. Check these from JSON/read-only shell commands before claiming readiness. Historical data retrieval succeeded; no BUY WATCH signals, EMA9/VWAP, Discord or full open-market canonical pipeline were tested by this run. Imported raw CSVs are in VPS local DataLake and were not pushed to Git automatically.

---

**Last updated:** 2026-10-11, ~15:40 UK. **Canonical starting point for the next AI/Codex session.**
**Truthfulness:** statuses below are confirmed only to the extent supported by actual commit history or VPS output. Do not interpret a committed module as running in production.

## 1. Architecture — user-confirmed and non-negotiable
The **only canonical full ASJR pipeline entry point** is called by the real VPS Chakra launcher `/root/trading/utils/trading_sudarsan_chakra.py`:
```python
tp.run_asjr_manual_pipeline(
    app=app,
    trade_date=None,
    gapup_df=None,
    fetch_gapup_from_app=True,
    include_sector=True,
    git_submit=True,
)
```
Function lives in `ASJR_Analyst/Tests/test_asjr_pipeline.py` (despite misleading Tests path). Launcher wrapper `ibkr_trading_sudarsan_chakra(app)` calls that function, then `tp.prepare_alert(result)`, `SN.send_to_discord(discord_message)` when nonempty, and `tp.mark_alert_sent()` only after send. On error it logs and may send an error message.
**All ongoing scanner/alert/data features must hook INSIDE this canonical pipeline.** Use the **same already-connected IBKR `app` object** across all modules. Never start a new EClient or Gateway inside individual strategy modules; no second scheduled bot. For stopped-bot manual one-shot, initialize app through the EXISTING Chakra `connect_ib_gateway(None)` helper; it may reconnect/launch Gateway if required.
Schedule: existing `trading_bot` tmux Chakra job runs every ~5 minutes. Preserve Rudra-Reversal 1H, existing scanner, other non-wick alerts, DataLake/Git synchronization and the user's manual Discord controls.

## 2. Manual full-cycle runner / call flow
`RudraScanner/run_now.py` (commit `d2f57ca1`, subsequent version unchanged as of this handoff):
- AUTO with `tmux has-session -t trading_bot` present: delegates to `RudraScanner/scan_now.py`, which **queues a request for the next normal scheduled Chakra cycle** using `RudraScanner/manual_request.py`; not an immediate execution.
- AUTO with bot absent, or explicit `--mode standalone`: one-shot script locks `/root/trading/ASJR/.chakra_run_now.lock` using nonblocking `fcntl.flock`; rechecks tmux; adds `/root/trading` (required for `utils.*` imports) and its utils directory to sys.path; loads **real launcher module** via importlib; calls existing `connect_ib_gateway(None)` (typically port 4002); checks connected; calls **real** `ibkr_trading_sudarsan_chakra(app)`; disconnects only its locally initialized app on completion. No separate permanent bot.
- `--dry-run`: checks launcher presence, no tmux, lock obtainable, **never connects**. `--premarket-test`: queued scanner mode prints diagnostic on completion; **standalone still invokes normal alerts**, so it is NOT a no-Discord mode. `--status` and `--saved` delegate to scanner CLI.
- **Safety gap**: manual lock not yet acquired by the scheduled production launcher. tmux check avoids common conflict but is NOT race-free. Before activating true manual/live overlap, add the SAME cross-process lock to scheduler (or enforce scheduling exclusion). `pgrep`/tmux detection is not a substitute for a common lock.
Actual VPS verification on 2026-10-11:
```text
run_now.py --dry-run => DRY RUN PASS
run_now.py --premarket-test => Gateway started; clientId=656 had API disclaimer error 10141;
clientId=657 connected True; FULL CHAKRA PIPELINE START; Sunday US session closed -> SKIPPED_CLOSED_SESSION; FULL CHAKRA PIPELINE COMPLETE.
```
Thus manual launcher/bootstrap/skip worked; NO open-market 5m imports or signals validated. IBKR warning 2172: Gateway 1045.1 needs upgrade before 2026-12-15; paper-trading API disclaimer error 10141 encountered on one client ID. Address separately.

## 3. Rudra-Premarket V1 rules (user confirmed)
- **BUY WATCH alert only**; NOT an order.
- Completed 5-minute close **Price > EMA9 > VWAP** (strict).
- **5-day cumulative RVOL at same New York clock time <= 0.50x**, calculated against five PREVIOUS completed trading sessions; NO RVOL20 V1, NO 20-day import.
- Do not alert between **09:30 and 10:00 New York time**; other valid sessions eligible including premarket and after-hours subject to IBKR bars.
- Use actual IBKR WAP-based VWAP, never fabricated HLC3 replacement. Normal feed/feature transformer currently does NOT provide all fields to Rudra-Premarket, so SIGNAL AND DISCORD **NOT LIVE**.
- ET/UK conversion is DST-aware; alert user time in UK; dedup by ticker and bar/time; group only simultaneously qualifying tickers in one message, no batching delay across 5-min periods.
```text
RUDRA-PREMARKET
INTC | 17:35 | BUY WATCH | Price > EMA9 > VWAP | RV5 0.42x
AKAM | 17:35 | BUY WATCH | Price > EMA9 > VWAP | RV5 0.35x
```
Sample only, NOT live evidence.
- Wicks setups disabled in `ASJR_Analyst/config/wick_setups.json`; verify that old pending wick state can't still send. Preserve catalyst and Rudra-Reversal alerts.
- The research RVOL calculation presently uses **separate PRE/RTH/POST cumulative segments**, not TradingView's single `1 Day` anchor, and requires perfectly contiguous 5-minute bars from segment open. Extended-hours sparse prints may therefore fail readiness. Compare with user intended cumulative daily anchor before treating result as TradingView-equivalent.

## 4. Modules and hookup state
- `ASJR_Analyst/Tests/test_asjr_pipeline.py`: version `2026.10.11.2`. After `intraday_features.add_intraday_features(intraday_raw)`, calls `RudraScanner.premarket_rvol.update_history(..., save=True)` in a guarded try/except; then `RudraScanner.premarket_diagnostic.save_diagnostic(...)` in guarded try/except; legacy alert path continues. **This is history research, not BUY WATCH dispatch.**
- `RudraScanner/premarket_rvol.py`: ET normalized, strict complete-session profiles, previous five, readiness gate, candidate filter requiring `close, ema9, vwap, rvol5, rvol5_ready, minute, session`.
- `RudraScanner/premarket_diagnostic.py`: writes `ASJR_Analyst/DataLake/YYYY-MM-DD/reports/rudra_premarket_test.json`, explicitly reports `NOT_EVALUATED_MISSING_VERIFIED_EMA9_VWAP`.
- `RudraScanner/premarket_backfill.py`: opt-in queue `workers=3`, `ibkr_concurrency=1`. **Not wired to full pipeline, not started by scheduler.** Missing coordinated shared IBKR request gate, retry/TTL/persistence; do not claim active.
- `RudraScanner/scan_now.py`: request/await next scheduled full scanner cycle; `--premarket-test` prints saved diagnostic.
- `RudraScanner/run_now.py`: handles queued/stopped manual full Chakra call as above.
- `RudraScanner/import_premarket_history.py`: **one-off separate historical import only**, NOT a call to entire trading pipeline. Added 2026-10-11 (~15:39 UK). Uses same existing Chakra `connect_ib_gateway` helper/app, manual process lock, tmux safety check; per-symbol `ASJR_Analyst.Utils.asjr_ibkr.get_ibkr_5m_batch(app,[symbol],duration='10 D',batch_size=1,wait_time=25)`, 2-second spacing, raw CSVs, completeness stats, no scanner/new orders/Discord/Git. Source and audit below. Still **running on user's VPS when handoff requested; user has NOT yet supplied terminal output**. Do not assert import success, tickers completed, coverage, or saved baseline.
- `RudraScanner/check_chakra_launcher.sh`: offline Python compilation/test and launcher inspection, fail-fast.

## 5. Data sources, actual filenames and selection policy
**FIXED**: Latest earlier daily `ASJR_Analyst/DataLake/YYYY-MM-DD/config/fixed_watchlist.csv`; `ASJR_Analyst.Utils.asjr_day.ensure_fixed_watchlist` normally copies earlier file to a new day. Friday file `ASJR_Analyst/DataLake/2026-10-09/config/fixed_watchlist.csv` exists. Fixed includes MSFT, CRDO, SMCI, QCOM, AMAT, ORCL, WDC, MRVL, LRCX, NXPI, AKAM, WTTR, ONDS, MCHP, OPRX, MU, CAT, TSLA, INTC. Explicit exclusion ONDS in `RudraScanner.discovery.EXCLUDED` alongside BEAT; do not import these even if fixed enabled. INTC mandatory.
**AI**: `ASJR_Analyst/config/ai_scanner_list.csv`; validated by `RudraScanner.discovery.read_ai_csv` (enabled flag, expiry, warning). Updated 2026-10-11 to append MRVL, WDC, AKAM (labelled UNVERIFIED), preserving existing Friday researched names e.g. SPCX, PLTR, LITE, AMT, HUM, AMZN, TMUS, AAPL, JPM, NVDA, INTC. Freshness/quality are NOT magically verified by being in CSV. For discovery, AI is its own CSV; do not rewrite it from IBKR. Avoid claim of new live research for this backfill.
**IBKR FRIDAY SAVED**: `ASJR_Analyst/DataLake/2026-10-09/raw/ibkr_gapup.csv` (89 saved Friday mover symbols), NOT a fresh Sunday scan. Friday `raw/ibkr_scanner_list.csv` was not available from GitHub path; the importer uses actual Friday `ibkr_gapup.csv`. Some historical tickers may not pass fundamental/liquidity filters — apply `EXCLUDED`, validate quality separately.
**Live discover**: existing scanner uses TOP_PERC_GAIN, TOP_PERC_LOSE, HOT_BY_VOLUME and MOST_ACTIVE; live source CSV typically `raw/ibkr_scanner_list.csv`, kept distinct from saved Friday movers.
**One-off import source order**: FIXED -> AI -> IBKR_FRIDAY_SAVED_MOVERS, unique first occurrence, `EXCLUDED` omitted; default **max 30** symbols (not all 89). User requested fixed + AI + Friday list.
**One-off output paths**:
```text
ASJR_Analyst/DataLake/2026-10-09/raw/rudra_premarket_history/<TICKER>_5m.csv
ASJR_Analyst/DataLake/2026-10-09/reports/rudra_premarket_backfill.json
ASJR_Analyst/DataLake/2026-10-12/processed/rudra_premarket_rvol_history.csv
```
These are VPS data, not evidence of completed import unless files/logs verified. Do not git-add/push raw data automatically.
**Critical limitation**: importer currently tests *whole* PRE/RTH/POST segments for historic completeness; may report FETCHED while `complete_prior_sessions` is empty. It will only store validated data in the RVOL5 reference file; a FETCHED row does not imply enough five-day history. It uses `before_day='2026-10-12'` and writes Monday Oct 12 reference. The raw CSV fetch is usable for further diagnosis even when RVOL profile incomplete. If `--max-tickers 30`, only first 30 selected; verify count and provenance before expansion.

## 6. Commands — never mix live and offline
**Inspection/offline (safe):**
```bash
cd /root/trading/ASJR
git pull --ff-only origin main
bash RudraScanner/check_chakra_launcher.sh
/root/trading/venv_new/bin/python RudraScanner/run_now.py --dry-run
/root/trading/venv_new/bin/python RudraScanner/import_premarket_history.py --dry-run
```
**Historical import (actual IBKR, only if tmux `trading_bot` stopped and manual lock available):**
```bash
/root/trading/venv_new/bin/python RudraScanner/import_premarket_history.py --day 2026-10-09 --max-tickers 30
```
Check after completion:
```bash
/root/trading/venv_new/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('ASJR_Analyst/DataLake/2026-10-09/reports/rudra_premarket_backfill.json')
if p.exists():
 d=json.loads(p.read_text())
 print('entries',len(d.get('entries',[])),'reference',d.get('reference_path'),'rows',d.get('reference_rows'))
 for x in d.get('entries',[]): print(x['ticker'],x['state'],x['rows'],x['complete_prior_sessions'])
else: print('NO REPORT')
PY
```
**Full manual canonical Chakra pipeline (actual IBKR/normal Discord/Git operations):**
```bash
/root/trading/venv_new/bin/python RudraScanner/run_now.py --premarket-test
```
Bot-running => queues next cycle; stopped => standalone full run. On Sunday before ET 20:00 it **skips closed session**. `--premarket-test` is NOT a no-Discord switch in standalone.
**Discord SSH command convention**: `!runpy RudraScanner/run_now\.py --premarket-test` — quoting/backslash handling is specific to existing Discord parser; ensure no unintended flags. Never restart bot amid an active import.

## 7. Tests and verified results (chronological)
- 2026-10-11 VPS `git pull` reached `e65e3e5f`: Python compilation good; **9/9** offline RVOL5 + backfill tests passed, **3/3** older run_now tests passed. Then `run_now` implementation changed and `test_run_now.py` now has **4 tests**; no fresh recorded 4/4 result in attached logs. Do not misreport these as verified.
- 2026-10-11 initial live `run_now` failed importing `utils.IBKR_Historydata` because `/root/trading` absent from sys.path; fixed commit `d2f57ca1`.
- 2026-10-11 `run_now.py --dry-run`: PASS, scheduler absent, lock acquired.
- 2026-10-11 `run_now.py --premarket-test`: successfully initialized Gateway, connected with clientId 657 after error 10141 for clientId 656, invoked canonical full pipeline, got `SKIPPED_CLOSED_SESSION` (Sunday), returned FULL CHAKRA PIPELINE COMPLETE. This was **NOT** a historical market import, RVOL or signals success.
- 2026-10-11 AI CSV updated commit `3e20bd2`; history importer added commit `3c035b9`; user said **test is running** around 15:39 UK. Outcome is **PENDING USER LOGS**.

## 8. NEXT ACTIONS — preserve precise order
1. Wait for user terminal/history-import status. Read `rudra_premarket_backfill.json` and raw CSVs; count FETCHED vs ERROR vs no complete day and validate saved reference for Oct 12. Handle actual IBKR pacing/coverage issues; do not retry blindly while first import runs.
2. Fix discrepancies in raw historical data if `normalize_bars` expects timezone-aware bars; test complete segment counts for last five weekdays, distinguish no-trade sparse extended bars from missing broker feed. Decide whether use trading-day anchor vs separate PRE/RTH/POST with user approval, not silent change.
3. Preserve/merge reference history across multiple import rounds. One-off importer currently overwrites Monday reference with only the newly fetched batch; **danger if repeated imports**; fix before additional batches.
4. Wire the shared execution lock into real scheduled Chakra launcher (outside repo), or add a narrow wrapper **with explicit deployment procedure**. Do not edit external VPS file blindly; first audit launch wiring.
5. Implement actual EMA9 + IBKR WAP VWAP on completed same-time 5M bars, join RVOL5 readiness; exact UK time format/dedup; add unit and end-to-end integration tests; only then enable Discord alert after user approval.
6. Protect other alerts: Wicks setups disabled, Rudra Reversal 1H and catalysts unchanged. Validate no lingering wick pending-state dispatch.
7. Update version, `OPERATIONAL_HANDOFF.md`, `RUDRA_PREMARKET_SPEC.md`, `RudraScanner/CURRENT_STATE.md` as needed; do not claim production live before a trading-session test.
8. Watch IBKR compliance notices: paper disclaimer 10141, Gateway 1045.1 warning upgrade before Dec 15 2026.

## 9. Security, operations and user communication
No broker account numbers, passwords or Discord webhook tokens in reports/commits. Do not delete untracked research data or assume Git deletes on VPS are safe for other untracked files. No penny-stock/weak-quality speculative trades; user uses these as BUY WATCH inputs, never auto-orders. Use short and clear responses, UK timestamps in messages. Avoid claiming background jobs or bots running unless observed from a fresh VPS log; GitHub commits alone do not deploy code.
