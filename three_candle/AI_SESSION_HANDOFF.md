## 31 Oct 2026 — v2.5.4 extra C1/C2/C3 research columns

Per each detected candle add signed distance (%) from **simple MA9**, **simple MA20**, and **simple MA200** (each computed on the displayed 15-minute chart, not daily); **ASJR Volume Delta Pressure 12-point buy/sell count, 12-band profile, modeled buy-share %**, **5-prior-session cumulative RVOL**; and **total wick/body**, **upper-wick/body**, **lower-wick/body** ratios. Use exact `upper_wick=High-max(Open,Close)`, `lower_wick=min(Open,Close)-Low`, `body=abs(Close-Open)`; wick/body ratios are undefined/NaN for zero-body doji, never infinite. Existing candle range/body/wick percentages remain. No extra filter or ranking applied; data are for subsequent win/loss analysis only. NQ volume pressure is a proxy from OHLCV, not true exchange bid/ask delta. Long-lookback values require sufficient earlier bar history and matching session alignment. Version v2.5.4-20261031.

## 31 Oct 2026 — cross-market expansion: 15-minute timeframe floor

User confirmed **15-minute candles minimum** for Rudra Three-Candle backtesting (do NOT test 1m/5m entry patterns). The 5-minute NQ archive remains valuable only for accurate aggregation into complete 15-minute candles and checking intrabar order. Research instruments: NQ=F (September–October extended futures archive), EUR/USD (`EURUSD=X` on Yahoo), GBP/USD (`GBPUSD=X` on Yahoo). Forex collection for September–October is **planned, not yet published or tested**. Forex is 24/5 with weekend pauses and different daily rollover from CME NQ; preserve instrument-specific session grouping. **Do not pass forex through NQ-only extended session builder**; extend the loader with a separately verified 24/5 FX resampler, then run only 15m or higher. Keep current underlying three-/four-candle BUY/SELL signal criteria unchanged across instruments; price-distance floor `r_floor_pct=0.20` is a current NQ modeling convention and must be explicitly reviewed before comparing forex risk, not silently marketed as a fit-to-forex parameter.

Forex quote precision ~0.0001 pip for common USD pairs, typically 0.00001 fractional pip in feeds: do not use the NQ 0.25 or default stock 0.01 tick for the ASJR kernel. Spot FX feed OHLCV may have zero/unavailable volume, making cumulative five-day RVOL and ASJR volume delta pressure **unavailable**; never equate zero vendor volume to zero buying interest, and never invent bid/ask volume. For forex backtests report spread/slippage/swap and timing limitations, with timestamps in Europe/London and stored as UTC. Preserve C1/C2/C3 per-candle research fields even when their volume-derived values are NaN.

## 31 October 2026 — September extension and October EXTENDED coverage

October's published CSV at `three_candle/data/NQ_2026-10_5m_UTC.csv` contains **6,020 5-minute NQ futures bars**, including non-RTH overnight/extended hours. On full-volume weekdays its coverage report shows ~275/276 five-minute bars, far exceeding the 78 bars of equities-style 09:30–16:00 ET RTH. This verifies extended bars are PRESENT, not that every session has no gaps. Audit continuity and the 30 Oct 19:00 UTC quarantined spike; never assume a 24-hour continuous futures market (weekend and exchange maintenance breaks are normal).

New September script `three_candle/collect_nq_september_2026.py` collects NQ 5m for September 1–30 (where Yahoo history permits), including **extended/overnight, RTH, pre/postmarket**, and publishes `three_candle/data/NQ_2026-09_5m_UTC.csv` plus `NQ_2026-09_coverage.json`. The coverage JSON provides RTH vs non-RTH bar counts. Use SSH from the safe `/root/trading/ASJR-Synced` repository as done successfully for October; the script's default REPO constant must be redirected to synced checkout via a temporary sed copy. It has NOT been run and September CSV publication is not yet verified. Yahoo 5m availability and retention limits may cause older September chunks to be missing; retain existing Gann research CSVs as fallback rather than presenting an incomplete download as full history.

User rule: **signal criteria remain unchanged**; all indicators (ATR/ADX/RSI/RVOL5/MA200-distance/gap/ASJR pressure) are per-candle research fields, not new entry filters. UK time presentation, UTC storage. Track comparable RTH-only vs extended-mode outcomes separately.

## 31 Oct 2026 — October full-month NQ 5m bridge collection request

Queued bridge operation `three_candle_nq_october_2026`, request ID `research-2026103108319`, file `RudraScanner/ResearchBridge/requests/research-2026103108319.json`. New restricted collector `three_candle/collect_nq_october_2026.py`, allowlisted in `RudraScanner/research_bridge_worker.py`. Destination GitHub `three_candle/data/NQ_2026-10_5m_UTC.csv`, companion `three_candle/data/NQ_2026-10_coverage.json`. Collects NQ=F 5min October 1–30 2026 in Yahoo seven-day chunks; missing data and anomalous bars are explicitly flagged; never invent OHLCV or mark the month complete without verifying continuity.

**Deployment/status:** GitHub request is QUEUED, not proof that the VPS has executed it. The running bridge worker must load this new allowlisted operation (normally updated source plus service restart under administrator control). Do not restart trading bot or Discord for this. Monitor `RudraScanner/ResearchBridge/results/research-2026103108319.json`; only call it collected/published when status SUCCESS and both destination files are present and inspected.

## 31 October 2026 — two-day execution check, 29/30 October (v2.5.3)

**Authoritative scope:** user-supplied `NQ_5m_VERIFIED_2026-10-29_30.csv`, RTH only, 29 and 30 Oct, UK timestamps; five-minute bars assembled into complete consecutive fifteen-minute bars; exclude anomalous 30 Oct 19:00 5m bar (extreme range). Tested the same breakout rules with **current phase-1 relaxed size defaults** `minC1RangePct=0, minC2RangePct=0`; no indicator changes or further signal filters.

### Observed candidate table (loose phase-1 rules)
| Date | Side | Trigger UK | Entry | C2/sweep SL | MFE gain % before SL | 1R | 2R | 3R | Observed initial SL time |
|---|---|---|---:|---:|---:|---|---|---|---|
| 29 Oct | BUY | 15:00 | 29526.00 | 29449.00 | +0.511% | Yes | No | No | 17:50 |
| 29 Oct | BUY | 16:45 | 29564.50 | 29519.75 | +0.143% | No | No | No | 17:10 |
| 29 Oct | SELL | 17:00 | 29563.50 | 29606.75 | +0.474% | Yes | Yes | No | Not observed by available data end |
| 30 Oct | BUY | 14:30 | 28672.75 | 28614.75 | +0.562% | Yes | Yes | No | 15:40 |

**Totals for phase-1 loose candidates:** 2 RTH dates; **4 candidates** (3 BUY, 1 SELL); 1R target touch **3/4=75%**, 2R **2/4=50%**, 3R **0/4=0%**; MFE price-excursion sum **+1.690%**, NOT realized strategy P&L. The 29 Oct 16:45 BUY is INCLUDED in discovery mode; it was previously rejected by narrow C1/C2 size rules. It may overlap temporally with 17:00 SELL and is not evidence that both could be held under a single-position portfolio policy. Historical candle color filters are still retrospective; do not market these percentages as executable fill-adjusted trading wins. Intrabar ambiguity must be audited with more granular data.

### Candle feature samples (from 15m candles; Wilder-style indicator using only these two RTH sessions)
| Signal | Candle | UK | Close | Volume | Range % | Lower wick % of range | ATR14 | ADX14 | RSI14 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 29 BUY 15:00 | C1 | 29 14:30 | 29577.50 | 27231 | 0.315 | 45.04 | N/A | N/A | N/A |
| 29 BUY 15:00 | C2 | 29 14:45 | 29526.00 | 29287 | 0.465 | 56.10 | N/A | N/A | N/A |
| 29 BUY 15:00 | C3 | 29 15:00 | 29613.00 | 23282 | 0.332 | 1.27 | N/A | N/A | N/A |
| 29 BUY 16:45 | C1 | 29 16:15 | 29567.75 | 14302 | 0.156 | 54.35 | N/A | N/A | N/A |
| 29 BUY 16:45 | C2 | 29 16:30 | 29564.50 | 12692 | 0.181 | 83.64 | N/A | N/A | N/A |
| 29 BUY 16:45 | C3 | 29 16:45 | 29591.75 | 10537 | 0.250 | 41.55 | 136.98 | N/A | N/A |
| 29 SELL 17:00 | C1 | 29 16:15 | 29567.75 | 14302 | 0.156 | 54.35 | N/A | N/A | N/A |
| 29 SELL 17:00 | C2 | 29 16:30 | 29564.50 | 12692 | 0.181 | 83.64 | N/A | N/A | N/A |
| 29 SELL 17:00 | C3 | 29 16:45 | 29591.75 | 10537 | 0.250 | 41.55 | 136.98 | N/A | N/A |
| 30 BUY 14:30 | C1 | 30 14:00 | 28679.50 | 38111 | 0.629 | 0.69 | 152.87 | 24.05 | 20.83 |
| 30 BUY 14:30 | C2 | 30 14:15 | 28672.75 | 37098 | 0.314 | 64.44 | 148.37 | 27.19 | 20.72 |
| 30 BUY 14:30 | C3 | 30 14:30 | 28793.25 | 39961 | 0.588 | 4.87 | 149.87 | 28.62 | 28.45 |

**Not available for these early signal candles from two days alone:** MA200 of 15m close, five-prior-session RVOL5, and full Pine ASJR 12-band readiness. Gap calculations based on the previous *available* session are provisional and should not be equated with true exchange overnight gaps. Gather warmup candles from preceding trading days before reading these indicators. Also note Wilder ADX/ATR estimates can differ from TradingView when the lookback and seed histories differ.

**Testing status:** independently reran the 29/30 October sample candles and reconstructed loose setup matches and approximate 5m target touches with the stored Python logic. This is **not an end-to-end import and execution of the exact GitHub Python module**; Pine parity also not demonstrated. Source Python version **2.5.3-20261031**; concise summary followed by all C1/C2/C3 feature tables, with no new indicator-based exclusions.

## 31 October 2026 — ASJR Volume Delta Pressure v1 added (Python v2.5.2)

The **user's source Pine v6** `ASJR_Volume_Delta_Pressure_v1_Lite.pine` is the reference. Python `calculate_asjr_volume_delta_12()` mirrors its EMA21 anchored 12 equal price bands, ATR14-localization kernel, preceding 12 candles, exponentially age-decayed volume, body/close-location buy share, lower/upper wick rejection weight 0.35, activity floor 0.03, buy threshold >0.53 and sell threshold <0.47. Default parameters: `anchor_length=21, memory=12, local_width=0.45, wick_weight=0.35`. Use NQ tick size 0.25. Collected per C1/C2/C3: `ASJR_buy_points`, `ASJR_sell_points`, `ASJR_neutral_points`, `ASJR_buy_share_pct`, `ASJR_12bands`, `ASJR_ready`. A 12-point vector uses **B** (buy-dominant), **S** (sell-dominant), **N** (active neutral), **.** (inactive). Neutral/inactive aren't counted in either points score.

**Strong limitation:** indicator is a modeled directional **OHLCV pressure estimate**, not actual bid/ask aggressor delta or a real footprint. It may output NOT READY for EMA inside candle body, inadequate prior bars, or insufficient anchor-to-body distance. Never turn unavailable values into zero pressure, never treat C3 values as pre-entry known if entry was intra-C3, and never claim exact TradingView parity until Python/Pine are numerically compared on identical feed and history. Retain earlier backtest reference as separate narrower strategy; wide-mode candidates are a larger analysis set.

**29/30 Oct focus:** retain 29 Oct BUY (15:00 C3, entry 29526.00), 29 Oct SELL (16:45 C3 upside sweep, 17:00 C4 trigger, entry 29563.50), 30 Oct BUY (14:30 C3, entry 28672.75) as narrow-setup reference. For each capture C1/C2/C3 OHLCV, 12-point modeled pressure, ATR, ADX, RSI, RVOL5, MA200 distance, and session gap. The local verified two-day 5-minute CSV does not contain sufficient preceding warmup to compute *all* 12-point, RVOL5 and MA200 observations reliably, particularly on 29 Oct. Do not fabricate these statistics. Collect earlier consecutive sessions and repeat on aligned 15m candles to populate comparables.

### 31 Oct follow-up — v2.5.1 WIDE SIGNAL DISCOVERY DEFAULT

Phase 1 deliberately sets `minC1RangePct=0.0` and `minC2RangePct=0.0` in `check_signals()` (and zero-size defaults in `backtest_breakout_reversals()`) so small-size candidates are **recorded rather than discarded**. Existing core sweep/wick and retrospective C3/C4 candle-colour conditions still apply, so this is *not literally every possible three-candle combination*. To reproduce the narrow Oct 29–30 benchmark, explicitly pass `minC1RangePct=0.20, minC2RangePct=0.25`. Do NOT compare new wide-mode success percentages with the old narrow-mode benchmark without labeling the change.

Important data-coverage warning: `check_signals()` currently constructs the indicators from the candles in its requested scan period. Single-session calls normally have **NaN** for MA200 and RVOL5 and early ATR/ADX/RSI observations. To collect valid MA200/RVOL5, the engine needs a preceding warm-up history, which is future integration work. Do not fill unavailable features with zero or fabricate prior-session observations. The report prints the same C1/C2/C3 fields even when some values are unavailable.

## 31 October 2026 — Phase 1 wide research data capture (Python v2.5.0)

User direction: **do not aggressively tighten signal rules in this phase**; identify a broad set of three-candle reversal candidates, then learn which market environments differentiate successful from failed signals. Present the compact signal performance summary FIRST, followed by **one C1/C2/C3 research table per signal**. Remove the former verbose C2-only detail dump.

New notebook output: `test["breakout_trades"]` for signal summary and `test["candle_research"]` for full tidy C1/C2/C3 rows. `check_signals()` and `show_chart()` stay callable.

Indicator columns on each candle: timestamp UK, OHLCV, range/body/upper/lower wick percentages, **ATR14**, ATR% of closing price, **ADX14**, **RSI14**, **five-session cumulative RVOL (RVOL5)** relative to comparable elapsed session periods, **200-bar MA** calculated on the chart's timeframe, distance from that MA as signed %, and session-opening **gap %**. Missing indicator warmup is `NaN`, not 0. A 200-period 15-minute average is NOT the same as the daily MA200; for daily MA200 a separate daily price feed is needed. ADX and RSI use Wilder-style smoothed 14-period estimates. The default five-day RVOL needs five prior comparable sessions in the loaded dataset, not just the requested scan day; if there isn't enough history then it remains unavailable.

SELL pattern includes an additional entry trigger candle (C4). Its printed C1/C2/C3 metrics describe the three candles **ending in the C3 upside sweep**; the SELL trigger is the next red candle C4 and is included in the compact signal summary.

**Restrictions:** Do not claim success rates are executable trade win rates: green-C3/red-C4 requirements in the existing scanner are retrospective at intrabar entry, and 15-minute OHLC can be ambiguous about order of entry versus stop. New features must never be used as hidden filters before an actual separate statistical test. Keep previous benchmark outcomes as historical reference only.

**Pending for full statistical analysis:** collect sufficiently long 5m history for 200-bar warmup and RVOL5 baseline, distinguish RTH/extended session offsets, verify prior-session gap history is complete, add independent 20-day RVOL benchmark and daily MA200 if requested, and retain fully causal, lower-timeframe fill simulation before reporting true net profit.

# RUDRA THREE-CANDLE — LOCKED RESEARCH HANDOFF (30 OCT 2026)

## Final user-confirmed signal rules — use these by default for 29/30 Oct comparison

**Data:** NQ=F, verified 5-minute OHLCV resampled to complete consecutive 15-minute bars. All timestamps UK local. Never interpolate missing bars; quarantine anomalous futures quotes, including 30 Oct 19:00 UTC anomalous high 29562. For reproducibility preserve raw data source, date coverage and code version with results.

**BUY (C1/C2/C3):**
1. C1 is reference candle; minimum complete candle high-low range **0.20% of close**.
2. C2 has high-low range **at least 0.25% of close**, sweeps below C1 low, and has **lower wick longer than the absolute C2 body**. A **red C2 with long lower wick is preferred**, but red or green C2 is allowed in the code.
3. Enter **during C3** as soon as its price crosses upward over the **LOWER BOUNDARY OF C2 BODY**: `buy_entry = min(C2.Open,C2.Close)`. For red C2 this is **C2 CLOSE**; for green C2 this is **C2 OPEN**. **Never substitute max(C2.Open,C2.Close), C2 High, or C3 Close for this specified entry level.**
4. Initial stop: **C2 Low**. For the 29 Oct example: C1 14:30, red C2 14:45, trigger inside C3 15:00, entry **29526.00**, stop **29449.00**.
5. The current research scanner additionally requires **C3 to close green** and C3 close above C2 close in the legacy pattern finder. This is **look-ahead if used to filter an entry during C3**, so identify as ex-post confirmation only. Do not claim fully executable historical win rates from this rule. Volume optional, default `checkVol=False`.

**SELL — separately defined four-candle sweep reversal:**
1. Candle C3 makes upside liquidity sweep: `C3.High > max(C1.High,C2.High)`.
2. Next candle C4 is **red** and crosses **below the LOWER edge of C3's body**: `sell_entry=min(C3.Open,C3.Close)`. Enter during C4 when crossed, stop **C3 High**.
3. Current historical scanner checks C4 closes red ex-post; avoid asserting the final colour could be known at the immediate breakdown entry.
4. 29 Oct example: C3 sweep **16:45**, C4 red **17:00**; SELL trigger **29563.50**, stop **29606.75**.

**Backtest mechanics and reporting:**
- Use `risk_points=max(abs(entry-stop),entry*0.20/100)` for R thresholds in current code. Exact 1R/2R/3R touch calculations must use this floor, not round the 1.96R BUY to 2R.
- Start observing breakout in C3 for BUY and C4 for SELL. Actual 5-minute order matters; if entry and stop share a bar and sequence is unknown, report *ambiguous*, not a certain win. A bar opening beyond the trigger may require open-price fill, not the theoretical trigger. Include commissions/slippage only when modeled.
- Always report **Entry, SL, direction, UK timestamps, 1R/2R/3R targets and hit rates, maximum favourable Gain %, realized/stop Gain %, number of signals and data coverage**. Separate maximum favourable excursion (MFE) from booked profit. No profit should be claimed from a target merely touched without an explicit exit rule.
- Support/resistance confirmation is causal, and nearest-swing filter is OFF for these exploratory comparisons.

## Fixed 29–30 October 2026 RTH reference results (verified 5-minute source)

| Date | Trigger time UK | Direction | Entry | SL | Maximum favourable Gain % | 1R touched | 2R touched | 3R touched | Notes |
|---|---|---|---:|---:|---:|---|---|---|---|
| 29 Oct | 15:00 C3 | BUY | 29526.00 | 29449.00 | +0.511% | Yes | **No** | No | Max favourable 1.96R; later initial SL hit |
| 29 Oct | 17:00 C4 | SELL | 29563.50 | 29606.75 | +0.474% | Yes | Yes | No | No initial SL observed before available data ends; no proved booked profit |
| 30 Oct | 14:30 C3 | BUY | 28672.75 | 28614.75 | +0.562% | Yes | Yes | No | Later initial SL hit; trigger vs first 5-minute open introduces fill uncertainty |

**Counts from these three retrospectively identified RTH candidates:** 3 setups; **1R touched 3/3 = 100%**, **2R touched 2/3 = 66.7%**, **3R touched 0/3 = 0%**. Sum of maximum favourable instrument price moves **+1.547%** (not portfolio P&L, not realized profit; equal-notional hypothetical excursion sum). The reported 30 Oct 2R uses the 0.20% R floor. The 29 Oct BUY does **not** reach 2R.

**Coverage caveat:** This 3-setup result covers verified **RTH 13:30–20:00 UK** for 29/30 Oct, not full overnight futures sessions. The anomalous 30 Oct 19:00 quote must be excluded. No claim of 100% traded success/profitability or broad statistical reliability.

**Code and compatibility:** Source `three_candle/three_candle.py` version **2.4.3-20261030**; main notebook methods `check_signals()` and `show_chart()` preserved. Dedicated breakout engine `backtest_breakout_reversals()`; legacy `find_three_candle_setups()` uses retrospective C3 conditions and may yield different signal counts. For these locked reference results use breakout engine's rules and verified source, not the legacy touch summaries. The main chart may still draw swing lines only. Preserve this section as primary handoff and document any later experimental variants separately.

---

## 2026-10-30 — v2.4.3 confirmed C3 body-bottom BUY and 30 October RTH retest

- **BUY**: C1 range >=0.20%; C2 range >=0.25%, C2 lower wick > absolute body, C2 low < C1 low; entry during C3 as it crosses **min(C2.Open,C2.Close)** upward (red C2 -> close; green C2 -> open), stop at C2 low. C3 ultimately green is a **retrospective** pattern-quality filter: not knowable at the real-time breakout. Historical scan with this filter has look-ahead/selection bias.
- **SELL** remains C3 high sweeping both C1/C2 highs; enter on next red C4 breakdown through min(C3.Open,C3.Close), stop at C3 high. This is a separate hypothesis.
- **30 Oct NQ=F, verified RTH 5m CSV** 13:30–20:00 GMT: 77 observations; quarantined anomalous 19:00 five-minute candle (1278.75-point high-low range). Rebuilt 24 complete 15m candles; excluded incomplete 19:00 15m. **One BUY**: C1 14:00, C2 14:15, C3 14:30; C2 body-bottom entry **28672.75**, SL **28614.75**. C3 first five-minute candle opens 28673.00 (above proposed 28672.75 stop-entry); realistic fill could be >=28673.00, not guaranteed 28672.75. Maximum favourable high before stop **28834.00** = +0.5624% from nominal entry; min 0.20% R floor gives 2R target touches; later SL at 15:40 GMT = -0.2023% gross hypothetical stop-loss if no trailing/target exits. No SELL from cleaned RTH data.
- Previous 30 Oct **overnight** manually found 01:45 BUY and 05:30 / 06:30 SELL candidates on partial 15m data with a different loose model. Those are *not directly comparable* and this verified CSV covers RTH only. Full extended 30 Oct retest not yet executed.
- Code version **v2.4.3-20261030** corrects misleading docstring in backtest_breakout_reversals; BUY formula had already been modified in v2.4.2. Existing check_signals/show_chart notebook API retained. Backtest still evaluates initial stops before target on ambiguous same candles; cannot substantiate precise intrabar fills, fees or realized return.


## 2026-10-30 v2.4.2: corrected BUY trigger inside C3

- BUY entry price is **min(C2.Open, C2.Close)**, the lower edge of C2 body, crossed upward during C3. For the 29 Oct 14:45 red C2, entry=29526.00 rather than 29577.00; stop remains C2 low 29449.00.
- SELL entry rule stays separate and unchanged (C3 high sweep followed by C4 red breakdown).
- The BUY scanner still requires C3 to close green in its ex-post pattern qualification; this cannot be known at the intrabar entry time. Consequently historical results are research signals rather than a causal live-executable strategy without modifying that confirmation requirement.
- Verified against known 29 Oct supplied 15m OHLC and 5m candles; do not interpret target touches as realised profits.

## 2026-10-30 — v2.4.0 breakout reversal research and 29 October RTH

- Added `backtest_breakout_reversals(data, min_c1_range_pct=0.20, min_c2_range_pct=0.25, r_floor_pct=0.20)` to `three_candle.py`. `check_signals` runs and prints its table and returns `breakout_trades`; existing notebook entrypoints retained. This is a **research model**, not audited execution P&L.
- BUY: C1 candle range >=0.20%, C2 range >=0.25%, C2 lower wick longer than absolute body and low below C1 low; C3 green and breaks above max(C2 open,C2 close); entry at C2 body upper edge during C3, SL at C2 low.
- SELL (separate pattern): C3 high above BOTH C1 and C2 highs; the next C4 candle is red and breaks below min(C3 open,C3 close); entry at that C3 body lower edge during C4, SL=C3 high. Note this intentionally uses C3 as sweep candle, NOT as SELL entry candle. No SELL candle-size threshold was requested.
- Effective R for target calculations is max(initial stop distance, 0.20% of entry); the optional `r` parameter from `check_signals` is passed to this function as the percentage floor. Conservative stop-first when 15m OHLC is ambiguous. BUY C3 green and SELL C4 red are known **only at candle close**: such trades are retrospective pattern confirmations, and breakout entries cannot claim fully live-causal signals unless confirmation requirement is changed or shorter intrabar data is used. Signals/targets do not prove exact historical fills.
- **Verified 29 Oct 2026 NQ RTH 5m source**, 78 candles reconstructed into 26 15m: one qualifying BUY C2=14:45, C3=15:00, entry=29577, SL=29449, +0.338% maximum favourable move, SL -0.433%. One SELL C3 sweep=16:45, next C4=17:00 red, entry=29563.50, SL=29606.75, +0.474% maximum favourable move, 2R reachable by data end; SELL actual exit remains open/unresolved. Small 16:30 BUY rejected (C1 0.156% and C2 0.181% ranges).
- Earlier success percentages from C3-close or C2-close hypothesis are NOT comparable to these intrabar body-break entries. Always show Gain % and distinguish MFE, target hit and realised outcome.

## 2026-10-30 — v2.3.2 minimum-size filter; SELL setup identified for separate research

- User observed that the second BUY (C2 16:30 UK on NQ 29 Oct) is invalid because C1 and C2 are too small. Added **configurable provisional minimum whole-candle (High-Low) ranges**, as percentages of each candle's closing price: `minC1RangePct=0.20`, `minC2RangePct=0.25`. Both must pass. Function parameters in `check_signals` and helpers; existing notebook method names kept. These defaults are initial research choices, **not optimised/validated thresholds**.
- Exact 29 Oct examples: 14:30 C1 range 0.315%; 14:45 C2 range 0.465% => original BUY candidate remains. 16:15 C1 range 0.156%; 16:30 C2 range 0.181% => second BUY rejected.
- User's operational BUY entry is **intrabar during C3** upon crossing above the higher of C2 open/close. The historical `check_signals` target-touch method still uses an older ex-post reference; do **not** represent it as executable entry P&L until replaced and intrabar stop ordering verified using 5m/1m data.
- User also proposed a **separate SELL model** where **C3 is the sweep candle and entry triggers on the next red candle**. This is a research direction, **not yet implemented**; decide exact prior high swept, entry price threshold and confirmation timing before reporting a sell performance.
- Version: `2.3.2-20261030`. No change to chart colours/signals UI or SELL backtest yet.

## 2026-10-30 — v2.3.1 relaxed bullish C2 / green C3 confirmation

- Requested: allow bearish **or** bullish C2 sweep, but C3 must be **green** for a BUY signal. C2 no longer has to close above C1 low. The existing C2 lower wick > absolute C2 body and C2 low < C1 low checks remain.
- Function: `is_bullish_three_candle_sweep()`; `checkVol=False` default remains unchanged, optional volume-on mode remains available; still requires C3 close > C2 close. This is a pattern-detection change, **not** proof of a profitable entry or a filled trade.
- 29 Oct NQ 15m user-identified sequence: C1 14:30 low 29531.75, C2 14:45 red (O29577.00 L29449.00 C29526.00; lower wick 77 > body 51), C3 15:00 green (O29525.75 C29613.00). This case now passes the BUY predicate with volume OFF. Since C3 opens 15:00, confirmation occurs at **15:15 UK**, not at the start of 15:00.
- Printed version increased to `2.3.1-20261030`. Existing `check_signals()`, `show_chart()` API unchanged; chart still shows swing lines only.
- Only the supplied example's Boolean predicate was checked during the change; full 29/30 October scanner regression and data feed retrieval have not been rerun.

## Developer review guide — function map and execution flow (v2.3.0)

The source of truth is `main/three_candle/three_candle.py`.
The user will review and edit Python personally. Keep method names descriptive and retain
the public notebook interface. On every future code change, **increment `__version__`**
and print it on import and when `check_signals()` runs.

### Notebook calls

```python
import importlib, three_candle
importlib.reload(three_candle)
three_candle.show_method_flow()  # prints this processing sequence

test = three_candle.check_signals(
    "NQ=F", "15min", "2026-10-30", "2026-10-30",
    r=0.20, checkVol=False, session="extended",
    swingLeft=3, swingRight=3, swingProximity=0.25,
    nearSwingOnly=False
)
three_candle.show_chart(test)  # all swing price lines; signals hidden
```

### Exact order of execution

1. `check_signals()` parses ticker/date/timeframe/session, validates `checkVol`.
2. `get_timeframe_minutes()` converts requested timeframe into numeric minutes.
3. `download_candles_from_yahoo()` gets raw 5m OHLCV **or** `load_candles_from_csv()` loads research data.
   - `clean_downloaded_candles()` normalizes columns/time/index.
   - `find_missing_regular_hours_candles()` detects US RTH gaps for retry and reporting.
   - `remove_suspicious_nq_candles()` quarantines extreme/invalid NQ bars.
4. `build_regular_market_candles()` aggregates RTH only, or `build_extended_nq_candles()` aggregates NQ's extended futures session. `build_extended_nq_4hour_candles()` handles the special 4H grouping.
   - Only complete consecutive 5m groups form higher timeframe bars. No synthetic prices.
   - `get_trading_session_dates()` keeps pattern sequences inside the correct session.
5. `find_confirmed_swing_levels()` collects confirmed local support/resistance pivots, using configured `swingLeft` and `swingRight` candles; a level is only available after the right-hand confirming candle has closed.
6. `find_three_candle_setups()` iterates contiguous C1/C2/C3 and calls `is_bullish_three_candle_sweep()`. Volume comparison is OFF with `checkVol=False`.
7. `find_nearest_swing_for_setup()` tests each C2 wick against already-confirmed supports/resistances using `swingProximity`. `nearSwingOnly=True` filters results; default False does not.
8. `count_future_target_touches()` and `sum_hypothetical_target_returns()` produce **ex-post** research metrics only; these are not executable P&L or win rates.
9. `check_signals()` prints summary/details and returns a dictionary containing `data`, `signals`, `swing_levels`, `swing_matches`, `touches`, `potential_gains_pct`, and settings.
10. `show_chart(test)` plots full-period candlesticks/volume plus **all** confirmed swing support and resistance price lines. It currently intentionally does NOT plot signal entry, stop, or targets.

### Code edit guide

| What Raghu wants to change | Edit method |
| --- | --- |
| Yahoo download/data range | `download_candles_from_yahoo()` |
| Missing bars or abnormal NQ candles | `find_missing_regular_hours_candles()`, `remove_suspicious_nq_candles()` |
| RTH versus overnight candle aggregation | `build_regular_market_candles()`, `build_extended_nq_candles()` |
| C2 wick/sweep and C3 confirmation conditions | `is_bullish_three_candle_sweep()` |
| Pivot support/resistance sensitivity | `find_confirmed_swing_levels()`; knobs `swingLeft`, `swingRight` |
| Proximity of Three-Candle C2 to a prior level | `find_nearest_swing_for_setup()`; knob `swingProximity` |
| Historical target-hit research | `count_future_target_touches()`, `sum_hypothetical_target_returns()` |
| Print layout and public parameters | `check_signals()` |
| Chart candle/volume/swing line styling | `show_chart()` |

**Compatibility:** Previous internal function identifiers remain as aliases in the Python file;
`check_signals()` and `show_chart()` are unchanged public entry points. The Python
code is version `2.3.0-20261030`. This guide is documentation-only; no code change,
version bump or new performance claim accompanies this document update.

---

## 2026-10-30 — v2.3.0: human-readable Python methods for user maintenance

- Renamed internal functions into descriptive verbs (`download_candles_from_yahoo`, `build_extended_nq_candles`, `find_three_candle_setups`, `find_confirmed_swing_levels`, `count_future_target_touches`, etc.).
- Grouped code under numbered comment sections from inputs through data download, resampling, pattern, swings, ex-post research, public `check_signals` and chart.
- New `three_candle.show_method_flow()` prints the complete main call sequence.
- Preserved external notebook API `check_signals(...)` and `show_chart(test)`, current session, `checkVol=False`, all-swing chart behavior and default settings. Old internal names are kept as backwards-compatible aliases.
- Display version increments and prints `2.3.0-20261030`.
- Python syntax parse and runtime import/alias/helper checks succeeded on the prior unsectioned v2.3 content; final sectioned version passed Python syntax parsing. Trading performance was not re-backtested; this is intended as a naming/documentation refactor only.

## 2026-10-30 — v2.2.1 all swing lines first

- `show_chart(test)` now plots **one full-range candle chart** with **all** confirmed swing support (turquoise dashed) and resistance (orange dashed) levels; removed nearest-six limit.
- Each horizontal level begins at its confirmation timestamp and extends to the last candle, rather than appearing before it could have been known.
- No Three-Candle signal boxes, entry, SL, 1R/2R/3R or matching overlay are drawn in this version. The pattern research output from `check_signals` is preserved.
- `show_chart(test, signal_number=...)` remains callable, but signal_number is currently ignored in the lines-first display.
- Version prints `2.2.1-20261030` on import and in the scan.

## 2026-10-30 — v2.2.0: confirmed swing price lines + Three-Candle proximity

- Kept existing notebook API, default `checkVol=False`, `session="extended"` for NQ; version printed as `2.2.0-20261030`.
- New kwargs: `swingLeft=3`, `swingRight=3`, `swingProximity=0.25` (percent), `nearSwingOnly=False`.
- Causal pivot detection: price is a strict local minimum (SUPPORT) or maximum (RESISTANCE) versus `swingLeft` prior candles and `swingRight` subsequent candles. Pivot is known only after last confirming candle closes. Pivot neighbours must be contiguous in the same US session, including NQ extended futures trade-date grouping.
- Match a Three-Candle C2 sweep to *already-confirmed* price levels: measure C2 low distance to support and C2 high distance to resistance; choose the closest and report `NEAR`/ `FAR` with wick distance percent and pivot timestamp. This is a proximity research metric, **not** yet statistical evidence of signal edge.
- Console summary prints total confirmed swings and near-swing signal count. Details print the nearest swing price line.
- `show_chart(test)` overlays the three closest confirmed support prices below the proposed entry and three closest resistance prices above it, turquoise/orange dashed horizontal lines, based only on levels known at C2 close.
- `nearSwingOnly=True` optionally filters reported signals to those within `swingProximity`. OFF by default so old signal counts and touches remain unchanged. No executed trade P&L model added.
- Test: synthetic consecutive 15-minute prices produce three pivot levels, all with `confirmed_at > pivot_time`; Python syntax and pivot code executed. A full live Yahoo download and September regression was **not** rerun.

## 2026-10-30 — v2.1.4 NQ extended session (5m / 15m / 30m / 1h / 4h)

- Added `session="extended"` to `check_signals` (default `"RTH"` preserves all older calls).
- Exact notebook call: `check_signals("NQ=F", "15min", "2026-10-30", "2026-10-30", r=0.20, checkVol=False, session="extended")`; `show_chart(test)` remains unchanged.
- Extended is currently NQ=F-only; RTH existing behavior remains unchanged; 4h continues using futures trading hours.
- 5m-source bars are anchored to 18:00 US Eastern futures-session open, 17:00–18:00 ET exchange break omitted. Start/end refer to US futures *trade dates*. Candles are complete 5m-group aggregates only; no fabricated Yahoo candles, including missing 30 October 18:55 UK bar.
- NQ overnight 30 October 01:45 UK C2 has long lower wick and reclaims the 01:30 C1 low. Its 02:00 C3 closes higher but has lower volume (3683 vs 4852); `checkVol=False` allows this pattern. A synthetic 5m resampling/logic unit test using the user's **15m OHLC values** verified the 01:45 C2 is detected with volume OFF, excluded with volume ON. **This is not a claim that Yahoo's genuine underlying 5m download has been independently validated**.
- All signal reports remain **ex-post C2-close hypotheses**, not causal execution backtests. Stop/target order and fees aren't simulated. Separate 01:45 entry at 02:00 with C2-open stop may hit SL before reaching profit targets.
- Version printed on import and every check: `2.1.4-20261030`. Display labels show session.

# Rudra Three-Candle — AI session handoff

## Highest-priority update: V2.0.0 rewritten 2026-10-30

The user explicitly requested **completely new code, retaining only calling
functions**. `three_candle.py` was rebuilt around the archived RTH strategy.
`check_signals(ticker,start,end,r=0.10)` and `show_chart(test)` stay callable.
Console version `2.0.0-20261030`, model `RTH_C2_SWEEP_EXPOST`. All previous
breakout default / 2R-trailing references below are **historical only** and
must not be interpreted as describing the new runtime.

New implementation uses Yahoo 5m data, RTH resampling to completed 15m candles,
C2 lower-wick sweep/reclaim of C1 low, C3 greater volume and greater close.
C2-close/SL=C2-open are **hypothetical ex-post levels**, not causal live fills,
because C3 volume cannot be known at C2 close. Output is 1R/2R/3R future
price-touch counts only; it no longer fabricates a 0%/100% executed win rate.
Charts: green C2-close hypothesis, red SL, purple R references (not realised TP).

Tests passed on archived September IBKR 5m ten-ticker data: 83 total setups,
83/75/64 price touches. `check_signals` and `show_chart` also tested locally
against archived INTC CSV: 11 INTC signals; 11/9/8 touches. Yahoo retrieval of
28 October still needs user-side confirmation. Accept old unused
`target_r` and `require_breakout` notebook keyword arguments for compatibility
but they do not change the historical pattern.
Updated: 2026-10-30 (UK). Canonical documentation folder: `main/three_candle/`.

**New validation:** historical CSV mode and archived-data unit test added 2026-10-30. Ten September 2026 tickers exactly reproduce setup counts 5,8,11,10,12,7,9,11,4,6 (total 83), and price touches 83/75/64 at 1R/2R/3R. Executed-trade result is **not** established. See README for the regression command; the original Yahoo post-C3 C2-high breakout logic remains separate.

## Read first
1. [STRATEGY.md](STRATEGY.md) distinguishes the archived C2-close/1R model from the new code's post-C3 C2-high/2R model.
2. [three_candle.py](three_candle.py) is the operational source for current Python behaviour. Read function bodies, not only README defaults.
3. [README.md](README.md) has the run examples and research warnings.
4. Historical research: [2026-10-25 handoff](https://github.com/raghunathbhandari/ASJR/blob/rudra-data-results/Rudra-Three-Candle/AI_SESSION_HANDOFF.md), [2026-10-25 strategy](https://github.com/raghunathbhandari/ASJR/blob/rudra-data-results/Rudra-Three-Candle/STRATEGY.md).

## User intentions and visual conventions
- Project: **Rudra Three-Candle Strategy**. Primary historical focus INTC; multi-ticker research AMAT GOOG INTC LRCX META MU NVDA PLTR SPY XOM.
- Price chart legend: **entry green**, **profit-taking / winning trailing exit purple**, **stop-loss red**. Do not portray a hypothetical/unfilled entry as an actual fill.
- UK date/time labels, including BST/GMT. The US/UK DST mismatch week must be handled explicitly.
- Experiments include 0.10% and 0.20% minimum R; trailing from 1R versus from 2R; 15m/30m/1h; $10k and $20k allocation; IBKR tiered fees/slippage. Each scenario requires its own reproducible backtest; previous rough results are not interchangeable.
- The user has cited 100% success on 83 September signals. That refers to a historical *price-touch* observation and is **not a verified execution win rate**. Explain carefully and investigate the event ordering.

## Current exact implementation (main)
- Yahoo native 15m `prepost=True`, date boundaries UK, default INTC.
- C2 green and either wick > body; C3 volume > C2 volume; C1 is present but has no liquidity sweep filter; optional C3 high > C2 high.
- After C3, entry trigger C2 high; initial SL C2 open; risk=max(entry−SL, entry×0.10% by default).
- Trail starts at 2R by default, advancing on the next bar. Existing stop checked first. Unfilled/open signals excluded from completed-trade success denominator.
- Caveat: same bar used for entry fill may also be used to hit SL, and exact intrabar ordering is not known. No fees or gaps modeled.

## Previously observed, NOT validated executed P&L
- September historical 10-ticker: 83 ex-post setups; subsequent 1R/2R/3R price touches = 83/75/64, respectively.
- September INTC: Yahoo 8 qualifying patterns vs IBKR 11; audit discrepancy.
- October first three INTC: later highs 2R, 9R, 4R; C3 timing and initial SL ambiguity. Do not assert 3 verified winners.
- Older quoted +8.30%, +15.00%, +19.20% theoretical fixed-step totals and subsequent net-gain discussions must not be treated as audited fee-adjusted realized results.

## Data provenance and next action
Data stored on `rudra-data-results` branch (see STRATEGY.md for explicit paths); do not silently copy large exports to live `main`.
First reconcile filters and session alignment, then generate an event-by-event execution ledger with ambiguous bars, SL-before-target, no-fill/open, and costs. Only then report audited success rate and capital returns. No trading orders are authorized by this handoff.

## Change management
Before changing Python or claiming an improved success rate, record the model version, exact filter diff, data date span/source, fees, same-bar assumption, and test commands. Preserve old research counts as historical rather than rewriting them.

## Timeframe support — V2.1.0 (2026-10-30)
The notebook now accepts either `check_signals("INTC","2026-09-01","2026-09-30",r=.10)` (old, defaults 15min) or `check_signals("NQ=F","15min","2026-09-01","2026-09-30",r=.20)` (new timeframe argument). Supported: `5min`, `15min`, `30min`, `1h` (aliases 5m/15m/30m/60m). All use complete 5m source bars grouped from 09:30 ET RTH, never bridging sessions; the incomplete final 30-minute block is omitted for 1h. C3 confirmation label adds selected timeframe minutes. Tested locally for all four intervals on archived IBKR INTC, and old 15min API still reproduces 11/9/8 1R/2R/3R touches across 11 signals. Results are ex-post price touches, not executed P&L. Do not compare raw signal counts across different timeframes as though filters operated on equivalent candles.

## NQ extended 4H — V2.1.1 (2026-10-30)
User chose extended futures hours for `check_signals("NQ=F","4h","2026-09-01","2026-09-30",r=.20)`. Implementation: fetch 5m Yahoo futures from one calendar day before the first requested trading date; group futures trading sessions beginning 18:00 ET previous calendar day, ending at 17:00 ET trade date; omit 17:00–18:00 ET maintenance and incomplete 14:00–17:00 ET final three-hour segment. Five complete 4H bars (18–22, 22–02, 02–06, 06–10, 10–14 ET) per full session, when 5m data are complete. Three-candle patterns must stay within one futures session. The `1h` and shorter intervals retain the existing 09:30–16:00 ET RTH treatment. 4H is restricted to `NQ=F`; other symbols raise a clear error. Model banner prints `NQ_EXTENDED_C2_SWEEP_EXPOST` and version `2.1.1-20261030`.

Validation: synthetic 5m overnight data produced 5 correctly anchored complete 4h bars per session; local archived INTC 15min regression remained 11/9/8 touches over 11 signals, and 1h call succeeded. Real Yahoo NQ 4h September retrieval and resulting signals remain **unverified** until user runs the notebook. 4h ex-post target touches still do not represent executable wins.

## Yahoo NQ data integrity fix — V2.1.2 (2026-10-30)
The 30-Oct-2026 NQ=F 5m Yahoo export contained 155/156 RTH candles, missing **18:55 GMT**, plus anomalous **19:00 GMT** OHLC (O/H 29562, L 28283.25, C 28307.25; 1278.75-point range). The old resampler omitted incomplete 18:45 15m bar and its scanner incorrectly joined nonadjacent 18:30 and 19:00 as C2/C3, manufacturing a 1R/2R/3R target-touch signal from the anomalous high. This is **not** valid performance.

V2.1.2 now: normalizes/deduplicates Yahoo 5m, checks expected 09:30–15:55 ET 5m timestamps for observed RTH dates, retries missing-date downloads once, prints unresolved timestamps in UK time, quarantines NQ 5m bars whose high-low exceeds 2% of previous close (or violate OHLC envelope) for manual verification, rejects incomplete aggregation groups, and enforces exact adjacent C1/C2/C3 timeframe spacing. Does **not** invent missing candles or claim the Yahoo source is repaired; 2% NQ threshold is a conservative quarantine heuristic, not proof a legitimate extreme move is impossible. The source file may still remain incomplete pending alternate vendor/IBKR confirmation.

Validation on user-uploaded 30-Oct NQ CSV: 19:00 suspect bar quarantined; 24 complete 15m RTH bars remained, **0 qualifying signals**, eliminating the false positive. September archived IBKR INTC 15m regression remained 11 signals with 11/9/8 target touches. No live Yahoo retry could be validated in this isolated test; user should observe console warnings. Do not interpret the zero as proof no real 18:55 overnight setup existed: the 18:55 RTH candle remains missing.

## Optional C3 volume filter — V2.1.3 (2026-10-30)
User requested `checkVol=False` by default in `check_signals(..., checkVol=False)`; `checkVol=True` restores the original C3 Volume > C2 Volume predicate (with nonzero C2). C3 bullish-close filter, C2 sweep/reclaim, source integrity and candle continuity are unchanged. Console prints version/timeframe/checkVol flag; signal details identify whether volume is on. Tests confirmed the user-provided 30-Oct NQ overnight C1 01:30/C2 01:45/C3 02:00 pattern fails checkVol=True (C3/C2=0.759×) and passes False, and historic Sept IBKR INTC scan with volume ON still gives 11 signals. **Important:** 15min still scans RTH only; this overnight setup is not yet automatically discoverable by `check_signals("NQ=F","15min",...)`. 4h uses NQ extended session. Prior historical signal counts were with volume ON and must not be compared to new default-off counts as equivalent tests.
