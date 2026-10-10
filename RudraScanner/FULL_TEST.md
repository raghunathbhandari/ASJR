# RudraScanner — Full Test and Activation Checklist

Date: **10 October 2026 (UK)**. Read this alongside `RudraScanner/README.md`.
Repo: `raghunathbhandari/ASJR`, branch `main`.

## Verified evidence from user VPS BEFORE this code extension

- Input smoke test: **20/30** = 10 FIXED + 10 AI + 0 IBKR.
- Friday historical replay: **30/30** = 10 FIXED + 10 AI +
  10 archival mover-list IBKR-source substitutes (84 screened).
- First combined unit suite: **24 tests in 0.170 sec; OK**.
- These results are VERIFIED user console output, but do **not**
  validate any of the new features, indicator/parser/1H/Discord tests
  added after the original 24 tests.
- No real connected four-code scanner, production 30-name import,
  live WAP/VWAP, or live scanner Discord delivery has been verified.

## Added since the 24/24 verification

| File | Purpose |
|---|---|
| `RudraScanner/volume_history.py` | Preserve time-matched cumulative RVOL20 reference from 20 full prior RTH sessions in the same dated DataLake; read latest prior day, never fake missing history |
| `RudraScanner/tests/test_volume_history.py` | 3 new strict prior-day, rollover, and missing-data tests |
| `RudraScanner/reversal_bridge.py` and `tests/test_reversal_bridge.py` | 2 new first-use 150-bar readiness and historical-alert-flood prevention tests |
| `RudraScanner/features.py` | Actual IBKR WAP-weighted regular-session VWAP, continuous EMA9 import, true 20 prior complete RTH session RVOL (unavailable without coverage) |
| `RudraScanner/wap_capture.py` | Optional timestamp-aligned historicalData callback WAP capture on the SAME IBKR app |
| `ASJR_Analyst/Utils/asjr_ibkr.py` | Add WAP to returned 5-minute DataFrame when sidecar has a correct timestamp match; original six-field parser unchanged |
| `RudraScanner/patterns.py` | Five 5M symmetric LONG/SHORT research detectors; numerical thresholds are **PROVISIONAL**, alerts gated |
| `RudraScanner/topdown.py` | SPY + QQQ -> verified sector ETF -> ticker matching, unknown/mixed => WAIT |
| `RudraScanner/engine.py` | Consistent saved features and human-readable research report under the SAME DataLake |
| `RudraScanner/hourly.py` | Hourly-throttled, max-30 native IBKR 1-hour stock historical importer; same existing app; shared raw/intraday_1h.csv |
| `RudraScanner/reversal_bridge.py` | First-use marker for new Reversal stocks (>=150 complete 1H bars) to prevent historical alert replay |
| `RudraScanner/delivery.py` | Scanner-only independently acknowledged Discord delivery, disabled unless both approval flags are set |
| `ASJR_Analyst/Tests/test_asjr_pipeline.py` | Existing Chakra method now has OFF, SHADOW and explicit ACTIVE paths. No separate job or bot |
| `RudraScanner/datalake_test.py` | Offline raw 5M indicator/quality smoke test |
| `RudraScanner/tests/test_features.py` | 9 additional WAP, exact VWAP, no-WAP, EMA continuity and detector gating checks |
| `RudraScanner/tests/test_hourly.py` | 3 new fake Gateway 1H importer / cache / active fail-close checks |
| `RudraScanner/tests/test_topdown.py` | 5 new benchmark/sector WAIT/LONG/SHORT checks |
| `RudraScanner/tests/test_delivery.py` | 4 new Discord deduplication, approval and retry checks |

**Expected test inventory:** **50 test methods** (24 previously verified +
26 newly added). This is a SOURCE COUNT, not a claimed successful run.

## Run NOW on Saturday — no live IBKR required

### Step 1: Safe Git update

    cd /root/trading/ASJR
    git status --short
    git pull --ff-only origin main

If dirty files or merge errors appear, STOP: do not hard-reset or force-push
the running live-bot repo.

### Step 2: Syntax check

    /root/trading/venv_new/bin/python -m compileall -q RudraScanner ASJR_Analyst/Tests/test_asjr_pipeline.py ASJR_Analyst/Utils/asjr_ibkr.py

No output and exit code 0 indicate Python parsing succeeded.

### Step 3: Run ALL 50 unit tests

    /root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v

**Expected**: 45 tests; ending `OK`. Share the complete output. DO NOT
claim 50/50 passed until the actual VPS output is reviewed.

### Step 4: Test historical 30-stock input (read-only)

    /root/trading/venv_new/bin/python RudraScanner/bot_test.py --date 2026-10-09 --ibkr-source-date 2026-10-09

Expected: 30/30 historical candidates, `LEGACY_GAPUP_REPLAY_NOT_LIVE`,
zero real trade alerts; **NOT** the live four-code IBKR scanner.

### Step 5: Test 5-minute data quality, EMA9 and exact VWAP (read-only)

    /root/trading/venv_new/bin/python RudraScanner/datalake_test.py --date 2026-10-09

Friday's legacy IBKR raw file lacks the historical WAP field. The
new rolling RVOL20 baseline is likely also absent until twenty full
prior RTH sessions have been retained in common DataLake snapshots.
Expected: completed bars and continuous EMA9, but
`WAP_MISSING_OR_INCOMPLETE_RTH`; no verified VWAP-based entries,
`RVOL20` unavailable unless the full 20-session baseline exists.
A DATA_NOT_READY or NO VERIFIED TRADING SIGNALS result is
**correct** and must never be substituted with made-up entries.

Optional `--save` only after review: publishes namespaced diagnostic
files in the common dated DataLake, not Discord, and does not Git push.

## Modes in existing Chakra process

| Mode | Activation | Expected behavior |
|---|---|---|
| OFF | Default, unset or `RUDRA_SCANNER_MODE=off` | No extra IBKR calls; legacy Wicks/Reversal unchanged |
| SHADOW | `RUDRA_SCANNER_MODE=shadow` in existing bot process environment | New four-code scanner saves capped candidates in common DataLake; captures real WAP on the *existing* 5M import, saves diagnostics; no change to legacy ticker import or scanner Discord alerts |
| ACTIVE | `RUDRA_SCANNER_MODE=active` in existing bot process environment | **NOT YET LIVE TESTED.** If all four scanner calls complete and daily AI/fixed sources are valid, replace the ASJR imported universe with selected <=30 stocks, download shared 5M and bounded hourly-throttled 1H history, and evaluate the same locked Reversal logic on these symbols plus Yahoo NQ. Wicks detector remains unchanged but its monitored ticker universe changes. On scanner partial/error, fall back to old legacy pipeline |
| REPLAY | CLI-only `bot_test.py` with explicit allow_replay | Friday archival mover list. Cannot accidentally run inside production pipeline |

**IMPORTANT:** exporting variables in an interactive SSH shell does
NOT change the environment of an existing tmux bot. Only a
user-controlled restart/reconfiguration of the actual running
Chakra process can change production mode. Do NOT restart automatically.

The ACTIVE mode is implemented **for validation only** until the
Gateway, bar-source mapping, pacing, true 1H coverage and
Wicks ticker-scope change have been reviewed.

## Experimental detector and Discord gates

- `RUDRA_SCANNER_RESEARCH=1` enables provisional research-only pattern
  calculations AFTER daily sector data has been fetched.
- Missing/unverified SPY/QQQ or sector alignment => WAIT, zero
  detected signals.
- A pattern still needs actual WAP-based RTH VWAP and completed
  five-minute bars; premarket is included in continuous EMA9,
  not in regular-session VWAP.
- Pattern numerical thresholds are **research hypotheses, not user-locked
  trading settings**. Do not make investment decisions from the
  provisional research report.
- Discord requires **both**
  `RUDRA_SCANNER_ALERTS=1` and
  `RUDRA_SCANNER_THRESHOLDS_APPROVED=1` in the existing bot process,
  plus research enabled and the existing message sender. No such
  approval/activation has yet been given. Both flags stay OFF.
- State is independent from Wicks and Reversal:
  `ASJR_Analyst/rudra_scanner_delivery_state.json`.
  It acknowledges only successful sends, deduplicates by
  ticker/pattern/side/candle, and retries failures on later runs.
- A research flag by itself **never** sends scanner Discord messages.

## Controlled future US-market test — NOT on closed-market Saturday

1. Confirm 48/50 unit tests and Friday offline raw-data report.
2. Audit the actual VPS external caller
   `/root/trading/utils/trading_sudarsan_chakra.py`,
   EWrapper.historicalData callback, timing and IBKR pacing.
3. With user approval, enable **SHADOW** in existing process for
   one US regular-session test. Confirm all four scanner callback states,
   exact candidates, WAP values, datetimes, 5M completeness, and
   path/provenance of new DataLake files. Inspect logs and Git commits.
4. Review before ACTIVE: 5-minute monitoring universe will change to
   selected <=30 stock names; Wicks rules unaffected, but coverage
   changes. Confirm that this is acceptable.
5. Verify 1H source has >=150 completed bars per new ticker;
   verify new-ticker state seeding prevents stale alerts.
   NQ still uses Yahoo Finance.
6. Review and explicitly lock detector numerical thresholds and
   indicator source/quality rules; replay test actual trade outcomes.
7. Only then consider enabling production scanner Discord delivery
   with two user-controlled gates and verified ACK/retries.
8. AI research snapshot expires 2026-10-12 12:00 UTC
   (13:00 BST); no automatic hourly AI task exists yet.
   Refresh valid sources before Monday US RTH.

## No completed live verification claim

Friday saved source and Saturday SSH tests prove historical candidate
selection only. Full code is now committed, but live Gateway correctness,
stream freshness, actual WAP prices, broad 1H readiness, strategy
thresholds, sustained five-minute performance and delivered alerts
remain pending. Do not call this deployed or profitable based
only on passing offline tests.
