# Rudra DDB V2 — 15-minute EMA9/EMA20 BUY WATCH

Updated 2026-11-23. Alerts use official A=22, B=17, C=10 (49 unique stocks).
The code file and mode selector retain their historical filenames for compatibility;
the runtime result mode is **ddb_ema_gann_15m_v2**. The Discord adapter MUST match
this versioned result mode (never the config selector **ddb_ema_gann_5m**).

## Active signal requirements
- A **real 15m EMA9 cross above EMA20** on the prior completed 15-minute candle.
- The next completed 15m bullish candle has its **entire body above EMA9**.
- Both EMA9 and EMA20 slopes positive; EMA9 slope must exceed EMA20.
- Confirmation is within 2.5% of EMA9. Group A requires bullish SMH.
- Signals only during US regular trading hours. No stale/incomplete 15m candles.
- Exactly three contiguous completed IBKR 5m OHLC bars form each 15m bar.
- No volume minimum or volume ratio filter; no Gann-level calculations or
  Gann values in delivered Discord alerts.

## Scope
No additional background job, live order, RVOL, Wicks, 1H Reversal,
premarket Scanner or automated DataLake import in this mode.
Group C remains the existing ten-stock research list.

## Dispatch safety
The DDB formatter receives versioned results through a dedicated mode-check
helper. Signals stay queued until Discord reports delivery success; rejected
delivery does not ACK them. The old formatter must not receive DDB results.

The external existing Chakra Discord sender must import
ASJR_Analyst/Tests/test_asjr_pipeline.py and call its
prepare_alert(result)/mark_alert_sent() hooks. This is the historical
integration documented in ASJR handoff; **VERIFY** on the actual VPS after deploying this patch.

## Operator deployment (requires actual user command)
1. In Discord: `!mbdstop`. Confirm `!runSCommand bot` -> STOPPED.
2. On VPS in /root/trading/ASJR: check git status, then
   `git fetch origin && git merge --ff-only origin/main`.
   Do NOT force reset/stash, or wipe any DataLake state.
   Alternatively use the existing `!gitpull` only when checkout clean.
3. Syntax-check and run pure offline tests before restart:
   `/root/trading/venv_new/bin/python -m py_compile RudraScanner/ddb_ema_gann_5m.py ASJR_Analyst/Tests/test_asjr_pipeline.py`
   `/root/trading/venv_new/bin/python -m unittest RudraScanner.tests.test_ddb_ema_gann_5m -v`
4. Inspect Chakra's real entry point/formatter wiring and Python environment.
5. In Discord: `!mbdstart`; check `!runSCommand bot` then
   `!runSCommand logs all 20`.
6. Confirm `RUDRA DDB 15M | requested=49 | received=...` and an actual qualifying
   completed-candle test delivered to Discord with ACK. A git commit alone
   does not prove VPS deployment or Discord delivery.
7. For emergency rollback, stop bot, set
   `ASJR_Analyst/config/alert_mode.json` mode to `legacy` and
   restart only after reviewing old jobs; old logic remains in source.

Important: This switch changes only the Chakra 5m pipeline. It does not
stop any independent tmux, systemd service, or ChatGPT scheduled automation.
