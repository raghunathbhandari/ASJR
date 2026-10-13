> **V2 refinement 2026-10-13:** HIGH RVOL5 threshold is >= 2.00x (previously 2.50x). LOW remains <= 0.58x. Both still require Price > EMA9 > VWAP and data readiness. Not yet verified live or Discord enabled.

> **2026-10-13 V2 APPROVED (supersedes V1 threshold):** Two disjoint RVOL5 cumulative bands: LOW <= 0.58x or HIGH >= 2.50x. Both require completed 5m Price > EMA9 > IBKR WAP VWAP, fresh bars and a ready previous-five-session same-time volume baseline. Exclude 09:30–09:59 ET. Scan EVERY eligible ticker ingested in the common daily DataLake (FIXED + AI + IBKR discovered), not only INTC/WDC/AKAM. BUY WATCH only, label the band in diagnostic/alert. RVOL20 remains excluded. GitHub candidate filter and offline regression tests updated; this does NOT imply live Discord integration, feature readiness, full-universe live verification, or VPS deployment. Do not relax the three-condition check or send partial signals.

> **HISTORICAL 2026-10-11 V1 (superseded by V2 above):** Start with RVOL5 CUMULATIVE ONLY, threshold <= 0.50x. The 20-day criterion is removed; no 20-day history import. Header + one line per qualifying ticker, RV5 only. Still not live until tested and deployed.

# Rudra-Premarket — confirmed user requirements (2026-10-11 UK)

Status: V2 candidate-filter implementation committed; end-to-end readiness, tests on VPS, and Discord activation NOT verified. Do not claim live activation.

## Trigger, every existing 5-minute Chakra cycle
For every eligible ticker with valid synchronized price, EMA9, IBKR WAP-based VWAP and historical same-time relative-volume data:
- 5m price (completed bar close) > EMA9 > VWAP, strict ordering.
- V2: previous-five-session cumulative Relative Volume at Time <= 0.58 OR >= 2.50; classify LOW/HIGH.
- 20-day RVOL is NOT part of initial V1; defer until user requests.
- The ratio use TODAY's cumulative volume to the current completed 5m bar divided by average volume accumulated to that same intraday timestamp across 5 previous comparable trading sessions, respectively. Do not confuse with 5-bar moving average or RudraScanner's existing 20-day RTH-only RVOL. Separate extended-hours premarket, RTH, and after-hours handling must be validated; missing history means no signal, not zero.
- Exclude only 09:30 <= NY exchange-local time < 10:00 America/New_York (US cash-session open); timezone conversion DST aware. All other times when the existing broker actually supplies fresh 5m data are eligible, including premarket, RTH after 10, after-hours; do not invent all-night coverage when none exists.
- Scan all tickers actually ingested by the existing shared pipeline, not just INTC; do not restrict by +4% price change. Do not assume the IBKR scanner searches the entire market each 5 minutes; universe coverage should be stated truthfully.
- BUY WATCH only, not an automatic order.
- Dispatch immediately on the completed 5m cycle, without waiting for Git push or extra scanner import. Use a single fixed header followed by one line for EVERY qualifying ticker from that scan, UK 24h time. If several tickers qualify in the same 5m scan, put them all on separate lines under the single header; send promptly. Do not wait for future scans to batch tickers. Example:\n```text\nRUDRA-PREMARKET\nINTC | 17:35 | BUY WATCH | Price > EMA9 > VWAP | RV5 0.42x\n```
- Per-ticker per-bar dedup; prevent repeated spam each 5m while one continuously qualifying episode remains active, unless user explicitly requests repeated alerts. Independent simultaneous ticker signals should each send immediately, not be held for a consolidated scheduled batch.

## Replace alert type
- Disable legacy Wicks detection/Discord messages (not merely formatting), but preserve other features using wick state/files until code consumers reviewed. Do not inadvertently disable catalyst or locked 1H Rudra-Reversal alerts.
- Keep the original connected IBKR EClient/EWrapper, existing Chakra 5-minute scheduler, DataLake and Git operations; no second gateway/client/scheduler.
- Existing 2026-10-10 code in ASJR_Analyst/Utils/asjr_alerts.py and Tests/test_asjr_pipeline.py explicitly treats Wicks as first-priority and pushes scanner later. Update this integration carefully with tests so the new condition is evaluated and delivered with minimal latency, without breaking Rudra Reversal, Scanner shadow isolation or existing Discord sender.

## Required tests prior to enablement
- Exact V2 boundaries 0.58 and 2.50 (both inclusive), intermediate band excluded; > EMA9 > VWAP, missing/zero volume, no lookahead or partial-bar comparisons, premarket/RTH/after-hours session matching, US/UK DST mismatch, excluded 09:30 and 09:55 ET vs allowed 10:00 ET, all ticker events/dedup, high burst dispatch, no wick output, other alerts untouched, scanner and IBKR pacing compatibility.
- Validate broker historical coverage for previous 5 same-time sessions, especially extended hours. Observe actual live bot log/version after user git pull/restart; no claim of live monitoring until verified.
