# RudraScanner — Market-Wide Catalyst Discovery & Missed-Mover Audit
Updated: 2026-10-13 | Case study: BMBL, Monday 2026-10-12
Status: RESEARCH GUIDE / PROPOSED IMPROVEMENTS — NOT IMPLEMENTED IN BOT

## Purpose
Avoid missing major event-driven moves merely because a stock is outside the current sector leaders or fixed watchlist. Run TWO independent discovery branches:
1. INDEX → SECTOR/THEME → LEADERS (existing top-down approach).
2. MARKET-WIDE BREAKING EVENTS → TICKERS → PRICE/VOLUME CONFIRMATION (independent of sector leadership).
Merge results into Rudra-list discovery; preserve separate trade eligibility rules. A research mention is NOT a buy signal.

## BMBL incident — facts and limits
- 12 Oct 2026: BMBL closed $3.80 (+49.61% from $2.54), with roughly 41.58M volume vs ~1.05M previous day. These figures and initial story times were obtained in the retrospective conversation; revalidate against historical market feeds for any automated regression.
- Take-private discussions with Ithaca Holdings, reportedly around $1B, became public around 19:18–19:24 UK (14:18–14:24 ET); negotiations were not a finalized deal.
- The initial reported jump was around +21% (~$3.08) and the stock subsequently reached around +50%. Exact first moving 5m bar is UNVERIFIED until historical IBKR candles are checked.
- Our 20:00 UK AI market review did not surface BMBL, despite the publicly available breaking takeover report. This is an AI/web discovery coverage failure, not a claim that Reuters, Yahoo, or other sources failed.
- GitHub saved Oct 12 `raw/ibkr_scanner_list.csv` and `raw/ai_scanner_list.csv` do not contain BMBL. `reports/rudra_scanner_categories.txt` also lacks BMBL. This is a saved-output observation, NOT proof that IBKR never emitted BMBL earlier.
- Saved `raw/scanner_status.json` (generated 2026-10-12T23:58:52Z): IBKR four scan codes TOP_PERC_GAIN=50, TOP_PERC_LOSE=50, HOT_BY_VOLUME=49, MOST_ACTIVE=49; selected IBKR=10, FIXED=10, AI=0; AI entries enabled=1, expired=13; total selected=20. This proves stale AI coverage and constrained final selection at that snapshot, not the precise 19:20 UK failure point.
- `reports/rudra_scanner_research.txt` shows unavailable WAP/RVOL baselines, but that is a separate entry-research readiness issue and should NOT prevent catalyst discovery.

## Required web/AI research sweep — each scheduled Rudra-list run
1. Search independently of sector and fixed names: 'stocks moving on takeover reports today', 'breaking mergers acquisitions US stocks', 'stocks halted on news today', 'biggest unusual stock gainers with news', 'FDA decision stock move', 'earnings surprise guidance upgrade', 'major contract award stock surge'. Use fresh, dated sources (Reuters, AP, exchange/SEC filings, company IR, reputable financial wires, Yahoo Finance).
2. Search both **event-first** and **mover-first**; compare results. Do not depend only on preselected sectors, large caps, or known tickers.
3. For each candidate, capture ticker, company, headline, source URL, original published time (UTC), first observed time (UTC), catalyst class, confidence, session (PRE/RTH/POST/overnight), last price and timestamp, % change, volume, reference volume, and whether the news is confirmed/rumor.
4. Check source timestamps against UK/ET clocks. Never substitute a stale quote or prior session close for a live price. Confirm original reporting and distinguish reports of talks from completed deals.
5. Reconcile with the fixed list, AI CSV, IBKR RAW list and filtered board. If an event is significant but fails a trading filter, retain it in a separate **CATALYST DISCOVERY | RESEARCH ONLY** section with exclusion reason.
6. At each run, explicitly state **new material catalysts found** or **no verified new material catalysts**, plus last search time. Do not imply a scan ran unless it actually did.
7. For news breaking between scheduled runs, report at the NEXT run; a recurring alert/watch would need separate explicit authorization and a real automation implementation.

## Proposed scanner engineering (not active)
- Save each IBKR 5m scan snapshot with timestamp, scan code, ranks and complete returned symbols; never overwrite all intraday evidence with just the last scan.
- Save candidate transitions: DISCOVERED → ELIGIBLE/EXCLUDED → SELECTED/NOT_SELECTED → CATEGORY, including exclusion reasons and per-source cap.
- Maintain independent event-driven candidates so that sector rank, 10-IBKR selection cap, and penny-stock trading restrictions cannot silently erase a major catalyst from research visibility.
- Proposed anomaly triggers for research review (calibrate/backtest before enabling): >=10% price move, >=5x comparable volume, volatility halt, credible material acquisition headline. These are discovery flags, NOT entry rules; do not assume valid intraday RVOL from simple previous-day volume.
- Respect existing no-penny-stock/weak-fundamentals trade exclusions. BMBL (<$5) may appear in research-only discovery; do NOT automatically enable trading, alerts or BUY WATCH.
- Preserve existing Chakra, Discord, Wicks/Rudra-Premarket configurations. No new jobs or broker sessions without user approval.

## Investigation checklist for BMBL
1. Retrieve timestamped 2026-10-12 19:00–20:00 UK IBKR scanner snapshots or logs, if retained.
2. Check whether BMBL was returned by any scan code; if yes, determine filter/drop reason and timestamp.
3. Retrieve 5m BMBL OHLCV and establish first meaningful price/volume acceleration, news time, and volatility halt sequence.
4. Compare scheduled AI search execution logs and actual queries at/after 19:20 UK. Do not infer executed queries from a final report.
5. Backtest event-first and mover-first queries against this incident and additional positive/negative controls.
6. Verify the final report contains BMBL research-only with credible citation by 20:00 UK, without generating a trading signal.
7. Log detection delay, coverage, false positives, data availability and exact exclusion reason.

## Reporting template
RUDRA CATALYST DISCOVERY | YYYY-MM-DD HH:MM UK
TICKER | EVENT | FIRST NEWS (UK) | PRICE MOVE + SESSION/TIME | SOURCE | IBKR RAW? | FILTERED? | RESEARCH/TRADING ELIGIBILITY
Missing evidence = UNKNOWN, never NO. Clearly mark takeover rumors as unconfirmed.

## Source files
- `ASJR_Analyst/DataLake/2026-10-12/raw/ibkr_scanner_list.csv`
- `ASJR_Analyst/DataLake/2026-10-12/raw/ai_scanner_list.csv`
- `ASJR_Analyst/DataLake/2026-10-12/raw/scanner_status.json`
- `ASJR_Analyst/DataLake/2026-10-12/reports/rudra_scanner_categories.txt`
- `ASJR_Analyst/DataLake/2026-10-12/reports/rudra_scanner_research.txt`
- `RudraScanner/CURRENT_STATE.md`

## Non-goals
This guide does not assert that a new web search, code change, alert, or live scanner is running. It documents the learning and acceptance tests for future work.
