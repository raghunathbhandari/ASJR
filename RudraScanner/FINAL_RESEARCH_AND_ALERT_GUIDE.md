# ASJR Chakra — final research, implementation, sample alerts and next-session guide
**Checkpoint:** 2026-10-11, 17:20 BST (16:20 UTC). **Bot restart reported by user; no post-restart live log verified yet.** 
**Read alongside:** [AI_SESSION_HANDOFF.md](AI_SESSION_HANDOFF.md), [RUDRA_PREMARKET_SPEC.md](../ASJR_Analyst/RUDRA_PREMARKET_SPEC.md), [OPERATIONAL_HANDOFF.md](../ASJR_Analyst/OPERATIONAL_HANDOFF.md).

## 1. Executive status (do not overclaim)
- User reports **existing Chakra `trading_bot` restarted** after installing the full-round shared launcher lock. Restart is user-reported; **no post-restart scheduled-run log has been provided**.
- Lock installer output directly verified: `CHAKRA SHARED ROUND LOCK | INSTALLED`, backup at `/root/trading/utils/trading_sudarsan_chakra.py.backup_20261011_171515`, then `ALREADY INSTALLED`. Launcher itself is outside the Git checkout.
- User-provided VPS test log at commit `88e5f0b2`: **22/22 offline tests passed**: 15 RVOL/history/backfill/signal, 5 run_now, 2 launcher lock; Python compiled; launcher `--check` passed; no-broker dry run passed. Offline tests do **not** prove alert detection/delivery in a real session.
- **Rudra-Reversal 1H**: existing alert path retained, previously live, but actual operation **since restart unverified**.
- **Rudra-Premarket 5M**: coded into existing Chakra pipeline with BUY WATCH shadow evaluation, but **Discord explicitly OFF**: `RudraScanner/premarket_alert_config.json` contains `enabled:false` and `auto_backfill:false`.
- **RudraScanner pattern research** has independent double-approved Discord controls; not a third enabled strategy alert merely because shadow scanner runs.
- No automated BUY or SELL orders are initiated by the new BUY WATCH code.

## 2. Architecture and exact call flow
```text
Existing tmux trading_bot / scheduler (~5-minute cycle)
    -> /root/trading/utils/trading_sudarsan_chakra.py (external VPS launcher)
        -> shared .chakra_run_now.lock (launcher decorator, installed 2026-10-11)
        -> existing connected IBKR Gateway app (port 4002; one app)
        -> tp.run_asjr_manual_pipeline(app=app,
              trade_date=None, gapup_df=None,
              fetch_gapup_from_app=True, include_sector=True, git_submit=True)
            -> FIXED daily watchlist + AI CSV + IBKR scanner/movers
            -> reuse IBKR 5m history / capture actual bar WAP
            -> Rudra-Premarket RVOL5 durable reference, shadow EMA9/VWAP signal
            -> existing Wicks setup hook (configured disabled)
            -> locked Rudra-Reversal 1H alert logic
            -> RudraScanner selected AI/IBKR 5M scanner sidecar
            -> re-evaluate Rudra-Premarket from expanded selected universe
            -> gated 3-worker RVOL history backfill (currently OFF)
            -> existing sector/report/DataLake/Git cycle
        -> tp.prepare_alert(result)
            -> existing Rudra-Reversal / scanner messages
            -> append BUY WATCH only when new premarket alert gate enabled
        -> SN.send_to_discord(discord_message)
        -> tp.mark_alert_sent() after confirmed send
```
Full external launcher decorator holds the execution lock across **both pipeline and Discord send/ack**. `RudraScanner/run_now.py` uses the same lock for a manual stopped-bot one-shot, or queues work for the existing running Chakra bot. Do not launch a competing scheduler or independent broker client.

## 3. Two named trading strategies and their actual status

| Strategy | Bar length | Basic method | Message delivery |
|---|---|---|---|
| **Rudra-Reversal** | 1-hour | Existing locked mean-reversion logic after significant selling; original criteria/version unchanged by this integration | Established alert wiring; post-restart log still pending |
| **Rudra-Premarket** | 5-minute | Latest completed close **> EMA9 > session VWAP**, cumulative **RVOL5 <= 0.50x**, verified 5 prior sessions | **SHADOW ONLY; Discord disabled** |

Other scanner research and disabled Wicks setups must not be mistaken for enabled additional strategy alerts.

### Rudra-Premarket V1 precise conditions
1. Each 5-minute candle must be **completed**, timezone-aware, fresh and the most recent completed candle for that ticker, without stale replay.
2. Strict **Close > EMA9 > VWAP**; EMA9 uses real, completed IBKR bars and remains continuous across PRE/RTH/POST.
3. VWAP uses **actual historical IBKR WAP multiplied by bar volume**, cumulatively within that session and only where 5-minute bars are contiguous from the segment opening bar; missing WAP/zero volume/missing bar = fail closed. No HLC3 substitute.
4. **RVOL5 cumulative at same clock time**: today's cumulative volume versus the average cumulative volume of the five prior **complete** same-session days. Threshold <= **0.50x**. No RVOL20 in V1.
5. No BUY WATCH during **09:30–10:00 America/New_York**.
6. Signals require valid VWAP **and** RVOL reference; sparse extended-hours data legitimately produces no signal. Exclude explicitly blocked tickers such as ONDS and BEAT through discovery.
7. All alert timestamps are shown in **Europe/London** time (DST-aware).
8. Alert creation is analysis-only; **no orders**. Dedup key ticker + completed candle timestamp, persisted on successful Discord acknowledgement.

**Important research distinction:** Segment-isolated PRE/RTH/POST cumulative VWAP and RVOL here may **not** match a TradingView '1 Day' anchor across sessions. Do not promise parity until explicitly agreed and compared.

## 4. Session eligibility — ET and UK
US EDT on 2026-10-12 and UK BST until 2026-10-25, so the following **specific Monday** conversions hold. Future dates must use timezone rules, not hardcoded offsets.

| ET equity session | Monday 2026-10-12 UK | Current new-strategy eligibility |
|---|---|---|
| PRE 04:00–09:30 ET | 09:00–14:30 BST | Eligible with fresh valid 5m bars |
| Opening exclusion 09:30–10:00 ET | 14:30–15:00 BST | **NO signals** |
| RTH 10:00–16:00 ET | 15:00–21:00 BST | Eligible |
| POST 16:00–20:00 ET | 21:00–01:00 BST next day | Eligible only if Chakra actually runs, IBKR supplies complete bars, history valid |
| Overnight / Asia 20:00–04:00 ET | 01:00–09:00 BST | **NOT SUPPORTED** by Rudra-Premarket V1 |
| Sunday/holidays | No eligible US stock session | Canonical pipeline may return `SKIPPED_CLOSED_SESSION` |

**Do not confuse a VPS tmux process staying alive with the canonical stock pipeline continuing to execute.** On Sunday the prior manual full round connected to IBKR but returned `SKIPPED_CLOSED_SESSION`. The bot may remain running overnight yet the pipeline may skip closed sessions. The user's plan to observe the Asian session is a **monitoring experiment for connectivity**, not evidence that the 5m BUY WATCH will operate 20:00–04:00 ET. After-hours and premarket scheduler reachability still need live logs.

## 5. Historical datasets and confirmed results
- Sources: dated FIXED watchlist `ASJR_Analyst/DataLake/2026-10-09/config/fixed_watchlist.csv`, AI `ASJR_Analyst/config/ai_scanner_list.csv`, actual saved Friday IBKR mover file `ASJR_Analyst/DataLake/2026-10-09/raw/ibkr_gapup.csv` (not a new Sunday live scan).
- One-off 2026-10-09 import: **30/30 IBKR fetches succeeded**, common 1,920 x 5m bars/ticker; some less. Friday sources: 19 fixed rows -> 18 included after ONDS exclusion, 14 AI enabled, 87 saved IBKR movers. Imported symbols in the import/handoff logs.
- RVOL reference built for Monday 2026-10-12: **27,744 reference rows, 30 tickers, 86/90 eligible ticker-session groups**: RTH 30/30, POST 30/30, PRE 26/30. PRE insufficient: WTTR 1, OPRX 0, AMT 2, HUM 1 fully complete prior sessions. Do **not** assign zero RVOL or create bogus candles for these.
- Durable CSV migrated and verified on VPS:
  `/root/trading/ASJR/ASJR_Analyst/state/rudra_premarket_rvol5.csv`
- AI scheduled GitHub **ASJR DataLake cleanup** at approximately 08:00 UK daily removes only expired date directories under `ASJR_Analyst/DataLake`. Its prompt was explicitly amended to preserve the 5-session reference. It must never delete `ASJR_Analyst/state`; if only needed history is in an expired date folder and safe retention cannot be verified, skip deleting it.
- `premarket_live_backfill.py`: up to 3 new tickers per cycle, one serialized IBKR request at a time, separate opt-in gate **currently false**, merges into durable state rather than replacing prior tickers.

## 6. Sample Discord messages — illustrative only, NOT actual detected trades
**Rudra-Reversal 1H sample** (format based on previously observed alert; price/timestamp are historic sample, not current):
```text
RUDRA REVERSAL | 1H
NQ | BUY #2 | 09:00 | 31244.50 | DEPTH 33.7%
```
**Rudra-Premarket 5M sample** (invented numeric values to demonstrate formatting; no market signal has been established):
```text
RUDRA-PREMARKET
INTC | 09:15 | BUY WATCH | Price > EMA9 > VWAP | RV5 0.42x
MSFT | 09:15 | BUY WATCH | Price > EMA9 > VWAP | RV5 0.35x
```
Both use the canonical Discord sender; actual combined output may include an existing Reversal message followed by a Rudra-Premarket section **only after gate activation**. Do not send the sample as a real signal.

## 7. Final user-confirmed test, restart, and implementation checklist
- [x] Friday 30/30 history fetch successful.
- [x] 27,744-row rolling history migrated into durable `ASJR_Analyst/state`.
- [x] Reference count 30 RTH, 30 POST, 26 PRE.
- [x] GitHub 22/22 offline tests passed on VPS: 15 premarket, 5 manual runner, 2 launcher-lock installer.
- [x] Shared launcher lock installed with timestamped backup `trading_sudarsan_chakra.py.backup_20261011_171515`.
- [x] **User reports Chakra Bot restarted** on 2026-10-11 ~17:17 BST.
- [ ] Obtain first **post-restart canonical run log**; confirm no errors, existing Reversal works, new signal shadow features/selected tickers logged.
- [ ] Observe first valid 2026-10-12 PRE, RTH, and POST market-session cycles and bar completeness.
- [ ] Verify exact WAP VWAP, selected extra ticker coverage, UK timestamps, dedup and combined Discord payload length using real session data.
- [ ] Confirm lock prevents true parallel scheduled/manual rounds in deployment; avoid force simultaneous tests in market hours.
- [ ] Review `premarket_alert_config.json` **separate gates**; do not enable `auto_backfill` or Discord `enabled` until live evidence is good and user approves.
- [ ] After activation, confirm an actual BUY WATCH delivered and acknowledged before calling it LIVE.

## 8. Operator commands
```bash
cd /root/trading/ASJR
git pull --ff-only origin main
bash RudraScanner/check_chakra_launcher.sh
/root/trading/venv_new/bin/python RudraScanner/install_chakra_round_lock.py --check
/root/trading/venv_new/bin/python RudraScanner/run_now.py --dry-run
```
These commands do not by themselves test real market alerts. The existing bot has been restarted by user; **don't restart needlessly**. Avoid Git clean, destructive data operations, or adding raw market files into Git unintentionally.

**Next-session first question:** Request the newest after-restart Chakra cycle log, including `ASJR Analyst Version`, `RUDRA-PREMARKET | SIGNAL SHADOW`, `RUDRA-PREMARKET | RVOL5 history`, `RUDRA-PREMARKET | ALL SOURCES`, `RUN | SUCCESS` or explicit `SKIPPED_CLOSED_SESSION`. If none exists during closed hours, wait for eligible market session; do not manufacture one. Logs may report exceptions that should be fixed before gate activation.
