# Friday 9 October 2026 — One-round RudraScanner historical test

**Purpose:** Replay one entire Friday US cash session (09:30–16:00 ET,
14:30–21:00 UK BST) through the **same RudraScanner feature engine and
five setup detectors**, with as-of-candle index/sector checks. This is
not a bot restart or Discord/test trade order.

## Latest actual test run — one synthetic mock assertion fixed

On 2026-10-10 12:41 UTC the user's VPS completed
**65 tests with 1 failure** (`0.746s`). The
Friday historical IBKR WAP replay itself completed successfully
with **11 pattern labels, 10 distinct opportunities,
40.00% unique-entry win rate and +0.0147% average
before costs**, matching earlier observed research results.

**Failure was isolated to test code**:
`test_markout_entry_next_bar_and_exit_after_six` used an
unconditional fake pattern detector, which could signal at
5M RTH candle 6 although the real detector needs at least
15 complete RTH bars. The test's mock has now been changed
to enforce the real 15-bar minimum. No actual detector
or market calculation rules changed. **Re-run of the
65-case suite is pending; pass not yet verified.**

```bash
cd /root/trading/ASJR
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
```

Do not download Friday IBKR historical bars again; they
remain cached in the common DataLake.

---

## VERIFIED Friday IBKR historical replay — 2026-10-10 user VPS output

**The user successfully ran the NEW research backfill and one-day
five-pattern replay**, after initially seeing "No such file"
before `git pull`. After a successful Git fast-forward to
`940f949d`, the script was found and completed successfully.

Command actually executed:

```bash
/root/trading/venv_new/bin/python RudraScanner/friday_round.py \
  --date 2026-10-09 --download-ibkr \
  --host 127.0.0.1 --port 4002 \
  --client-id 91 --save
```

**ACTUAL observed historical IBKR response:**

- **40/40** requested US stocks/sector ETF instruments returned historical
  data (30 frozen retrospective stocks + SPY + QQQ + eight sector ETFs).
  `failures: {}`.
- **22,290 5-minute bars**, **40 tickers**, all 22,290 rows had
  real reported historical IBKR WAP/average values.
- **9,360 RTH bars** had valid calculated session-reset exact VWAP.
- The research pass evaluated **2,160** post-opening-gate
  stock RTH candles, with the following blocks:
  **1,853** missing/mixed directional context;
  **36** insufficient pattern-history bars;
  **8** setups too late for the fixed 30-minute forward
  comparison. `missing_wap: 0`.
- **11 pattern-tagged research signals**, all LONG, **5 positive,
  6 negative**, average hypothetical 30-minute markout
  **+0.0311%** per pattern hit before trading costs; displayed
  **45.45%** signal-level win rate.
- Detector counts:
  `HITCHHIKER` **6** (2 positive, mean **−0.0364%**),
  `BACK$IDE` **4** (2 positive, mean **+0.0914%**),
  `SECOND CHANCE` **1** (1 positive, **+0.1947%**),
  `RUBBERBAND` **0**, `FASHIONABLY LATE` **0**.
- **IMPORTANT SAME-BAR DUPLICATE:** AMZN at **20:25 BST**
  generated both HITCHHIKER and SECOND CHANCE, with identical
  next-open / 30-minute markout of **+0.1947%**.
  Counting that *once* yields **10 distinct entry
  opportunities**, **4 positive, 6 negative**, **40.00%**
  positive, average **+0.0147%** per unique entry
  before commissions/spread/slippage. Other AMZN/HUM signals
  may overlap while earlier hypothetical entries remain open,
  so even these 10 opportunities do **not** equal 10
  independent portfolio positions.
- Best printed single markout was HUM BACK$IDE
  **+0.6329%** (19:00 BST signal); worst was AMT
  HITCHHIKER **−0.5489%** (18:55 BST signal).
- `real_live_signals: 0`, `discord_sent: 0`,
  `orders_sent: 0`. Research files saved only to the
  common **2026-10-09 DataLake**.
- **HINDSIGHT / SELECTION BIAS PERSISTS:** The 30 selected
  candidates were chosen using Friday after-close archived
  legacy movers and Saturday AI research. This is NOT a
  prospective Friday morning scanner backtest.
  Also, exits are the provisional next-open to
  30-minute horizon, not user-locked EMA9/trailing/stops,
  and costs are excluded. No strategy edge is established.

### Follow-up improvement committed, not yet re-verified on VPS

`RudraScanner/friday_round.py` now reports
`distinct_entry_opportunities`,
`overlapping_pattern_labels`,
`distinct_entry_wins`,
`distinct_entry_win_rate_pct`,
`distinct_entry_average_markout_pct` and
`by_pattern_diagnostics` in JSON, while preserving
the 11 raw pattern-tagged rows and legacy report fields.
A new test in `tests/test_friday_round.py`
verifies the duplicate calculation. This makes the
source test suite **65 methods** (56 previously verified
on VPS, 9 new Friday replay tests not yet VPS-verified).

Run from VPS **without another paid IBKR backfill**,
because `raw/rudra_friday_ibkr_wap.csv` already exists:

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/friday_round.py --date 2026-10-09 --save
```

Expected after new code (but **not yet rerun**):
65 tests OK; 11 raw pattern hits, 10 distinct entries,
40% distinct-entry positive, +0.0147% mean unique
markout before costs. Do not claim the test suite or
updated summary passed until actual user VPS output is observed.

---

## Precise limitations

1. The user-verified Friday archived 5M file includes 56,027 completed
   candles across 106 historical tickers but **does NOT include actual
   IBKR bar WAP**, so the strict exact RTH VWAP cannot be calculated.
   A run on saved OHLCV alone will report **no evaluable setups**,
   **not** an actual zero-win/zero-loss trading result.
2. Archived Friday `sector_market_daily.csv` has missing `today_pct`
   (including SPY/QQQ). The replay requires **timestamped historical
   5M IBKR TRADES bars** for SPY, QQQ and each evidenced sector ETF;
   it computes current percent move versus Thursday's verified
   15:55 ET regular-session close at EACH Friday candle (not a
   hindsight end-of-Friday percent change).
3. **Frozen 30 names are from Saturday Oct 10 research**:
   fixed `AKAM AMAT CRDO INTC MSFT ORCL QCOM SMCI WDC WTTR`,
   AI `AAPL AMT AMZN HUM JPM LITE NVDA PLTR SPCX TMUS`,
   and legacy IBKR-mover replay
   `ASTS AXTI DDOG DE MRNA SNOW SWKS T VZ ZS`.
   Thus **universe selection contains hindsight**. These are suitable
   for retrospective chart/pattern review but **NOT** a fully unbiased
   Friday 09:30 trader-discovery backtest. SPCX must be confirmed
   against real IBKR contract identity and the company quality filters.
4. Only one 2026-10-09 session is scored. Real 20-prior-session
   cumulative RVOL20 may be unavailable, explicitly so; the pattern
   code uses clearly labelled **prior-12-bar median relative volume**,
   not a false RVOL20 approximation. EMA9 crosses actual completed
   premarket / previous-day bars. Exact VWAP resets at 09:30 ET.
5. Existing five detectors still have **provisional thresholds**.
   The session is evaluated bar-by-bar with **NO LOOKAHEAD** on
   market/sector or price features. No entry before the first
   30 minutes. Indicators lacking valid input => blocked, NOT zero signals.
6. There is **no approved strategy exit rule** for these five
   RudraScanner setups yet. For a consistent comparison, optional
   research markouts use the **next 5M open** after signal and
   **close six bars after signal (30-minute horizon)**, before
   commissions, spread, slippage and borrow costs. Consecutive/
   overlapping setup events are counted independently; these
   calculations are **not portfolio returns or locked P&L**.

## One command — archived offline audit, no Gateway needed

```bash
cd /root/trading/ASJR
git status --short
git pull --ff-only origin main
/root/trading/venv_new/bin/python -m unittest discover -s RudraScanner/tests -p 'test_*.py' -v
/root/trading/venv_new/bin/python RudraScanner/friday_round.py --date 2026-10-09
```

This attempts to use a saved isolated IBKR WAP backfill first:
`ASJR_Analyst/DataLake/2026-10-09/raw/rudra_friday_ibkr_wap.csv`.
If absent, it falls back to the original
`raw/intraday_5m.csv` with **missing WAP** and reports
`NO EVALUABLE SIGNALS` plus exact blocker counts.
It does NOT invent HLC3 VWAP, sector % or trades.

The previous suite was **56/56 passed on VPS**. New
`RudraScanner/tests/test_friday_round.py` adds **seven
UNVERIFIED cases**. Until user runs new suite, expected case
count is **63**, not yet observed.

## When IB Gateway API is available — historical WAP/ETF backfill

The stand-alone research client connects with separate
`client-id 91` in **read-only** mode to an already-running Gateway.
It does **not** start Chakra or send orders, and it does not alter
the old `intraday_5m.csv` or locked Reversal. Vendor
`ib_async.BarData.average` is IBKR's historical bar WAP.
Only real `TRADES` bars are used; missing WAP cannot be patched.

If your Gateway uses port **4002** for paper, run:

```bash
/root/trading/venv_new/bin/python RudraScanner/friday_round.py \
  --date 2026-10-09 --download-ibkr \
  --host 127.0.0.1 --port 4002 --client-id 91 --save
```

Use the actual Gateway port if different, and a client ID not
already in use. The program paces historical requests, validates
trading-stock contracts, and requests up to 30 frozen tickers
plus SPY/QQQ and supported sector ETFs sequentially. This
can take several minutes depending on market-data pacing.
The historical API may be **unavailable on a closed-market
weekend, denied for subscriptions, or fail for individual contracts**.
If so the program reports real errors instead of claiming success.
IBKR stock contract resolution alone does not verify fundamentals.

Historical source output (namespaced test only):

- `raw/rudra_friday_ibkr_wap.csv` — REAL archived 5M bar
  OHLCV and IBKR historical average/WAP for available contracts.
- `reports/rudra_friday_ibkr_backfill_status.json` — exact
  requested symbols, unavailable contracts, actual bars and errors.
- `reports/rudra_friday_round_status.json` — session,
  eligibility/blocker counts, research-only summary.
- `reports/rudra_friday_round_markouts.csv` — each retrospective
  setup, next bar entry, six-bar close, signed return before costs.
  Only generated with `--save`.

The script does not make any order, post Discord, push Git or
modify the live bot configuration. The saved files are under the
existing COMMON DataLake but are **not** live signal outputs.

## How to interpret result

- `missing_wap` > 0: no legitimate WAP-based VWAP for those
  bars. Cannot evaluate strategy.
- `missing_sector_or_index` > 0: no as-of signal because
  SPY/QQQ or the mapped sector ETF is missing/mixed.
- `no_future_exit_bar`: setup near Friday close cannot be
  evaluated over full six-bar horizon. Do not drop silently
  from backtest without reporting.
- `research_signals_with_markout`: experimental setups on
  completed candles with valid inputs and as-of context.
- `win_rate_pct` and `average_markout_pct` are defined only
  when enough evaluable signals exist. A single day and
  hindsight universe must not be advertised as a validated edge.
- A historical read-only IBKR WAP backfill is NOT a successful
  live `TOP_PERC_GAIN/TOP_PERC_LOSE/HOT_BY_VOLUME/MOST_ACTIVE`
  scanning test.

**Project next stage after one-round report:** review actual
tickers/signals, whether first market-hour signals were missed,
the limits of the after-30-minute gate, provisional setup
definitions and realistic risk/exit policy. The 1H Rudra-Reversal
and Wicks are intentionally NOT backtested by this research tool;
their locked rules and live alert status are unchanged.

**Do not turn on `RUDRA_SCANNER_MODE=active` or scanner Discord
flags just because research markouts look profitable.**
