# Rudra DDB 5M EMA9/EMA20 + ASJR Gann — deployment
As of 2026-11-12, target universe A=22, B=17, C=10 (49 unique stocks).
Group C is provisional research (BKNG RCL MAR DAL WM CTAS LMT URI DE VLO).
Only BUY WATCH: newest COMPLETED 5-minute candle LOW > EMA9 > EMA20,
with the previous completed candle not already satisfying the same condition.
Thus a bullish false-to-true transition generates one alert, not one per every
trending candle. PRE/RTH/POST included, UK times used.
Levels follow ASJR Pine n=1..100: odd MAIN n*n; even MAIN n*n+1;
MID three quarter-spaced levels between neighboring MAIN levels;
restrict to 150 latest Yahoo daily bars' low/high, show 5 nearest.
Yahoo 1D may differ from TradingView 150D during a forming session.
No Gann levels are fabricated if daily history is incomplete.
No live orders. No RVOL, Scanner, Wick, 1H reversal or DDB360 in this mode.

The external existing Chakra Discord sender must import
ASJR_Analyst/Tests/test_asjr_pipeline.py and call its
prepare_alert(result)/mark_alert_sent() hooks. This is the historical
integration documented in ASJR handoff; **VERIFY** on the actual VPS.

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
6. Confirm `RUDRA DDB 5M | requested=49 | received=...` and an actual qualifying
   completed-candle test delivered to Discord with ACK. A git commit alone
   does not prove VPS deployment or Discord delivery.
7. For emergency rollback, stop bot, set
   `ASJR_Analyst/config/alert_mode.json` mode to `legacy` and
   restart only after reviewing old jobs; old logic remains in source.

Important: This switch changes only the Chakra 5m pipeline. It does not
stop any independent tmux, systemd service, or ChatGPT scheduled automation.
