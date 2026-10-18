## 2026-10-18 — Local Jupyter 15m TA-Lib scanner (NEW)

File `RudraScanner/RudraGann/gann15_patterns.py` committed (independent of older 5m `strategy.py`). Uses **TA-Lib** Morning Star, Evening Star, Hammer, Inverted Hammer, Shooting Star, Hanging Man, Engulfing and Harami candlestick detectors. Reads existing 5m Yahoo session CSV, constructs aligned 15m candles only from 3 contiguous 5m candles. Gann fixed odd/even square levels. Pattern and level proximity ±15 default plus close direction required. Executes *hypothetical* trade at NEXT 15m open, stop beyond observed pattern extreme, 2R TP, stop-first OHLC if ambiguous. Signal result includes NY and UK signal time, pattern name, Gann line, detailed reason, entry, SL, TP, result, R and NQ index-movement gain/loss %. Not actual account return; ignores commissions/slippage. Visual plotting is **8–10 inline candlesticks** with Gann line using mplfinance. No live orders or bot changes. These are NEW exploratory 15m pattern rules, not the old 5m breakout/retest state machine; do not conflate backtests.

Windows clone path: `D:\\Trading\\OmJRTrading\\JRTrading\\ASJR_Trading\\RudraGann\\ASJR`; notebook: `D:\\Trading\\OmJRTrading\\JRTrading\\ASJR_Trading\\gann.ipynb`. In PowerShell run `git -C "D:\\Trading\\OmJRTrading\\JRTrading\\ASJR_Trading\\RudraGann\\ASJR" pull origin main`. In notebook:
```python
%pip install TA-Lib mplfinance pandas numpy matplotlib
import sys
sys.path.insert(0, r"D:\\Trading\\OmJRTrading\\JRTrading\\ASJR_Trading\\RudraGann\\ASJR")
from RudraScanner.RudraGann.gann15_patterns import run, plot_signal
bars, signals = run("2026-10-15")
for i in range(len(signals)):
    plot_signal(bars, signals, i, candles=10)
```
No sign-off for V1 strategy replacing any live trading logic. Validate results visually and check source gaps/rolls.

---

# Rudra-Gann — Data, VPS Bridge, Admin Commands and Strategy Handoff
Updated: 2026-10-18. READ THIS FIRST IN THE NEXT SESSION.

## 1. Source-of-truth folders
- ASJR repository: https://github.com/raghunathbhandari/ASJR
- Canonical research folder: `RudraScanner/RudraGann/`.
- Original BARS 1-minute source copies (do not overwrite): `RudraScanner/ResearchData/Gann/Source/BARS/`.
  - `NQ_1min_2025-01-01_2025-12-31_stitched.csv` — 353,233 rows.
  - `NQ_1min_2026-01-01_2026-10-08_stitched.csv` — 274,455 rows.
  - Source: https://github.com/kfccolonel1/BARS and https://github.com/kfccolonel1/BARS/blob/main/catalog.json.
  - Published by `RudraScanner/RudraGann/import_bars_sources.py` with SHA256 checks printed at import:
    - 2025: `1e7b695fa6e670c7808f4283200fc1db51a8e7bfcebdabd3240078c7d9f2c663`
    - 2026: `6a0aaa144118160da036409310df4e57cf41f7d23d9a07ce04671da50a154d65`
- Yahoo NQ=F 5m research files: `RudraScanner/ResearchData/Gann/NQ_YYYY-MM-DD_5m.csv`, verified 33 sessions September 1–October 16, 2026.
- Older research repository: https://github.com/raghunathbhandari/AlgoStrategy ; `NQ/rudra-reversal/HANDOFF.md`, `NQ/data/`, and `AI_Chunks/NQ/data/external/`.
- Local VPS isolated research worktree: `/root/trading/ASJR-Gann`; **live trading tree** `/root/trading/ASJR`. Do not modify/reset/clean/rebase live checkout.
- Optional local IBKR 5m checkpoint from `RudraScanner/RudraGann/import_ibkr_1y.py` is not confirmed pushed to GitHub.

## 2. Verified integrity status — 2026-10-18
VPS ran `/root/trading/venv_new/bin/python RudraScanner/RudraGann/audit_data.py` successfully:
- 2025: 353,233 rows, Jan 1 23:00 UTC–Dec 31 21:59 UTC; zero invalid times, duplicates, ordering or OHLC violations.
- 2026: 274,455 rows, Jan 1 23:00 UTC–Oct 9 03:58 UTC; same zero-error checks.
- Total 627,688 actual 1-minute rows, 33 separately stored Yahoo 5-minute session files.
- **Basic structural audit PASS; gap-by-gap trading session completeness, provider discrepancies, roll anomalies, 1m->5m completeness and full resampling NOT YET COMPLETE.** No claim of a validated full-year Gann backtest.

## 3. GitHub ↔ VPS Research Bridge
- Code: `RudraScanner/research_bridge_worker.py` and documentation `RudraScanner/ResearchBridge/README.md`.
- Requests: `RudraScanner/ResearchBridge/requests/research-<13digits>.json`; results: matching file in `RudraScanner/ResearchBridge/results/`.
- Request schema: `{"schema_version":1,"id":"research-<13digits>","operation":"<EXACT_ALLOWLIST>","batch":null}`.
- Worker polls GitHub; only explicitly allowed operations run. **A GitHub commit/request does NOT prove VPS execution. Verify a published SUCCESS result.**
- Existing operation examples: `health_check`, `research_46_batch`, `research_46_finalize`, `research_46_publish`, `gann_nq_20261016`, `gann_nq_october_2026`. Current worker does NOT allow arbitrary commands or generic BARS imports through bridge. Do not advertise those as supported.
- Live checkout has documented Git divergence; `!gitpull` has failed previously. Use isolated research worktree commands for Rudra-Gann research rather than forcing live Git sync. The separate `--git-safe-sync` flag is a worktree workaround, NOT a repair of live divergence.

### 4. Approved Discord/admin entry points
Approved *existing* script command style: `!runpy RudraScanner/scan_now\.py --flag`. Examples from bridge docs:
- `!runpy RudraScanner/scan_now\.py --bridge-check` (ONLY when no concurrent worker running).
- `!runpy RudraScanner/scan_now\.py --bridge-start` and `--bridge-refresh` (requires code available in the executing checkout; may need systemd permissions).
- `!runpy RudraScanner/scan_now\.py --gann-test` was added to remote code but **failed on live VPS** with unrecognized flag due to diverged checkout; do NOT claim it is deployed.
- Directly running newly added scripts via Discord may be denied by script allowlist.
- Do not run `--bridge-check` concurrently with active systemd research worker; only one bridge poller.

### 5. Verified safe SSH research workflow (no Chakra changes)
```bash
cd /root/trading/ASJR-Gann
git fetch origin main
git checkout --detach origin/main
/root/trading/venv_new/bin/python RudraScanner/RudraGann/audit_data.py
```
Other scripts: `RudraScanner/RudraGann/import_bars_sources.py` (BARS copy, already succeeded) and `RudraScanner/gann_september_import.py` / `gann_october_import.py` (already succeeded).
DO NOT `git reset --hard`/`git clean` in `/root/trading/ASJR`.
Do not touch active Chakra processes, alerts, schedules or DataLake.

## 6. Rudra-Gann strategy — research-only current V1
- Data: NQ futures. User marked 5-minute **Oct 16 SELL signal candles** at 10:50 NY (Gann 29,929) and 13:45 NY (Gann 29,585).
- Gann line: for n odd `n*n`; for n even `n*n+1`, fixed 1x price scale (research assumption).
- **MANDATORY:** Gann level interaction + touch/sweep/retest + recognizable bearish/bullish reversal candle. NO candle pattern = NO TRADE.
- SELL pattern thresholds: minimum bearish body 40% of full candle range, close in bottom 35% of range; Gann tolerance ±15 index points, allowed overshoot +25, break lookback 24×5m, confirmation window 4×5m bars.
- SL above confirmed SELL reversal candle high +0.25 tick; TP 2R. Long mirror: SL below bullish reversal low; TP 2R.
- **Critical no-lookahead:** Visually labeled 10:50/13:45 entry candles are known only after they close. Automated backtest executes at NEXT 5m candle OPEN. Claiming entry at same candle OPEN with stop based on that candle HIGH would be hindsight.
- Existing executable V1: `RudraScanner/RudraGann/strategy.py`; tests `test_strategy.py`; detailed `STRATEGY.md`.
- Verified October 16 V1 VPS scan: 203 bars, one detected SELL (13:45 signal, 13:50 entry 29,493, SL 29,549, TP 29,381, +2R). 10:50 user-marked reversal did NOT pass current automated logic; do not inflate automatic signals or rewrite thresholds based only on examples.
- Do not run strategy tests until the user finishes the data collection/quality verification phase. Then resample real 1m to 5m/15m/1H/4H and audit roll/gaps first.
