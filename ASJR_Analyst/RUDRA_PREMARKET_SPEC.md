# Rudra-Premarket — confirmed user requirements (2026-10-11 UK)

Status: SPECIFICATION ONLY; NOT implemented or live. Do not claim Discord activation.

## Trigger, every existing 5-minute Chakra cycle
For every eligible ticker with valid synchronized price, EMA9, IBKR WAP-based VWAP and historical same-time relative-volume data:
- 5m price (completed bar close) > EMA9 > VWAP, strict ordering.
- 5 previous trading-session cumulative Relative Volume at Time <= 0.50.
- 20 previous trading-session cumulative Relative Volume at Time <= 0.50.
- Both ratios use TODAY's cumulative volume to the current completed 5m bar divided by average volume accumulated to that same intraday timestamp across 5 or 20 previous comparable trading sessions, respectively. Do not confuse with 5/20-bar moving average or RudraScanner's existing 20-day RTH-only RVOL. Separate extended-hours premarket, RTH, and after-hours handling must be validated; missing history means no signal, not zero.
- Exclude only 09:30 <= NY exchange-local time < 10:00 America/New_York (US cash-session open); timezone conversion DST aware. All other times when the existing broker actually supplies fresh 5m data are eligible, including premarket, RTH after 10, after-hours; do not invent all-night coverage when none exists.
- Scan all tickers actually ingested by the existing shared pipeline, not just INTC; do not restrict by +4% price change. Do not assume the IBKR scanner searches the entire market each 5 minutes; universe coverage should be stated truthfully.
- BUY WATCH only, not an automatic order.
- Dispatch immediately on the completed 5m cycle, without waiting for Git push or extra scanner import. Use a two-line message: fixed header plus one line per qualifying ticker; UK 24h time. EXACT example:\n```text\nRUDRA-PREMARKET\nINTC | 17:35 | BUY WATCH | Price > EMA9 > VWAP | RV5 0.42x | RV20 0.38x\n```
- Per-ticker per-bar dedup; prevent repeated spam each 5m while one continuously qualifying episode remains active, unless user explicitly requests repeated alerts. Independent simultaneous ticker signals should each send immediately, not be held for a consolidated scheduled batch.

## Replace alert type
- Disable legacy Wicks detection/Discord messages (not merely formatting), but preserve other features using wick state/files until code consumers reviewed. Do not inadvertently disable catalyst or locked 1H Rudra-Reversal alerts.
- Keep the original connected IBKR EClient/EWrapper, existing Chakra 5-minute scheduler, DataLake and Git operations; no second gateway/client/scheduler.
- Existing 2026-10-10 code in ASJR_Analyst/Utils/asjr_alerts.py and Tests/test_asjr_pipeline.py explicitly treats Wicks as first-priority and pushes scanner later. Update this integration carefully with tests so the new condition is evaluated and delivered with minimal latency, without breaking Rudra Reversal, Scanner shadow isolation or existing Discord sender.

## Required tests prior to enablement
- Exact threshold values 0.5 and > EMA9 > VWAP, missing/zero volume, no lookahead or partial-bar comparisons, premarket/RTH/after-hours session matching, US/UK DST mismatch, excluded 09:30 and 09:55 ET vs allowed 10:00 ET, all ticker events/dedup, high burst dispatch, no wick output, other alerts untouched, scanner and IBKR pacing compatibility.
- Validate broker historical coverage for previous 5 and 20 same-time sessions, especially extended hours. Observe actual live bot log/version after user git pull/restart; no claim of live monitoring until verified.
