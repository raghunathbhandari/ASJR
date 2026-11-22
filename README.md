# ASJR Trading — Algorithmic Trading Research & Market Intelligence

**Python trading research • Quantitative strategy development • Market-data engineering • Broker/API integration • TradingView Pine Script • AI-assisted analysis**

ASJR is a personally developed, evolving research and automation project for **US equities, index futures and selected other markets**. It brings together market-data collection, systematic signal generation, indicator research, historical backtesting, chart visualisation, watchlist screening and broker-connected alert workflows.

The project is designed around a practical research loop:

**Market context → Candidate discovery → Rules-based setup → Entry/exit simulation → Risk review → Chart validation → Iteration**

> **Project status:** Active development and experimentation. The repository contains working Python implementations, research prototypes, historical datasets, test suites and Pine Script source. **A strategy being implemented, backtested or alerted does not mean it is profitable, independently validated, deployed live or placing orders.** Individual folders document their own assumptions and validation status.

## Contents

- [Mean Reversal](Backtesting/MeanReversal/)
- [MA Golden Cross (EMA9/EMA21)](three_candle/ma_strategy_v2.py)
- [Bollinger Band](Backtesting/MeanReversal/bb_mean_reversal_backtest.py)
- [VWAP/MA Trend Following](Backtesting/VWAP_EMA9/)
- [4% Up/Down — 4% Down Alert](ASJR_Analyst/Strategies/MeanReversal4Pct/README.md)
- [Tickers 360 Analysis](ASJR_Analyst/README.md)
- [AI Automation](RudraScanner/FINAL_RESEARCH_AND_ALERT_GUIDE.md)
- [VPS Bridge Automation](RudraScanner/ResearchBridge/README.md)
- [Daily DataLake & Data Import Preparation](ASJR_Analyst/README.md)
- [Linux VPS Server Automation](RUDRA_DOWNLOADER_GUIDE.md)
- [IBKR / IB Gateway Automation](Backtesting/DataLoader/IBKR_24H_IMPORT.md)
- [ASJR Renko and SuperTrend V2 — contiguous Renko bricks and SuperTrend](Renko%20and%20SuperTrend/README.md)
- [ASJR Renko V4 — scroll-aware contiguous bricks](Renko/README.md)
- [ASJR Volume Delta Pressure V2 — 12-zone pressure with EMA9/EMA21/EMA200](Volume%20Delta%20Pressure/README.md)
- [ASJR 360 View V5 — responsive EMA21 trend colouring and two-row dashboard](ASJR%20360%20View/README.md)
- [ASJR Gann Swing V2 — diagonal swing + purple High/Low step overlay](ASJR-Gann-Swing/README.md)
- [ASJR Monk (Lama) colour guide — default editable palette](Design/ASJR_Monk_Lama_Colors.md)

- [Technology and architecture](#technology-and-architecture)
- [Strategy catalogue and entry/exit rules](#strategy-catalogue-and-entryexit-rules)
- [Three-Candle research](#three-candle-research)
- [Gann price levels and price-action research](#gann-price-levels-and-price-action-research)
- [Gann time cycles and Time = Price](#gann-time-cycles-and-time--price)
- [Gann learning and historical studies](#gann-learning-and-historical-studies)
- [Books and further reading](#books-and-further-reading)
- [Research references and source material](#research-references-and-source-material)
- [TradingView Pine Scripts](#tradingview-pine-scripts)
- [Rudra scanner, DDB and market intelligence](#rudra-scanner-ddb-and-market-intelligence)
- [Data engineering, testing and reproducibility](#data-engineering-testing-and-reproducibility)
- [Getting started](#getting-started)
- [Research limitations and disclaimer](#research-limitations-and-disclaimer)

**Visual design:** [ASJR Monk (Lama) colour palette](Design/ASJR_Monk_Lama_Colors.md) supplies default adjustable indicator colours; a requested colour (such as the Gann Swing High/Low purple) takes priority.

## Technology and architecture

| Area | Tools / approach |
| --- | --- |
| Core research | **Python**, Pandas, NumPy, notebooks, rules-based OHLCV analysis |
| Market data | **Interactive Brokers (IBKR)** APIs/Gateway, Yahoo Finance / yfinance, historical CSV datasets |
| Broker / provider integration | Data retrieval, scanner inputs, market-session processing and broker-connected research/alert pipelines |
| Technical indicators | EMA, VWAP, Bollinger Bands, RSI, ADX, ATR, RVOL, price structure, candlestick patterns and Gann levels |
| Backtesting | Historical replay, next-bar execution assumptions, structural stops, R-multiple tracking, trailing exits, MFE/MAE, diagnostics |
| Charts | Matplotlib, mplfinance, notebook charts, **TradingView Pine Script v6** |
| Automation / reporting | Scheduled or on-demand scans, Discord-oriented alert/report integrations, JSON/CSV research outputs |
| Engineering | Modular Python components, test suites, Git/GitHub version control, Linux/VPS operating workflows |
| AI research | AI-assisted market-context interpretation, strategy prototyping and analysis; numerical rules and backtests remain independently inspectable |

**Design principle:** Separate *discovery*, *signal confirmation*, *simulated execution* and *actual broker execution*. Avoid treating a price touch, a visual chart signal or an AI assessment as a filled trade.

## Repository map

| Location | Purpose |
| --- | --- |
| [`three_candle/`](three_candle/) | Three-candle strategies, MES/NQ/Gold research, MA strategies, market structure, archived backtests and results |
| [`Backtesting/`](Backtesting/) | Bollinger reversion, session breakout, VWAP/EMA signal research and market-data loaders |
| [`RudraScanner/`](RudraScanner/) | IBKR scanner research, momentum rankings, premarket RVOL, DDB watch rules, Gann retest experiments and unit tests |
| [`ASJR_Analyst/`](ASJR_Analyst/) | Analyst pipeline, strategy-specific alerts, market-data processing, configuration and tests |
| [`Gann%20Ideas/`](Gann%20Ideas/) | Gann price/time-cycle Pine indicators, mathematical study notes and reference tests |
| [`Candle%20Patterns/`](Candle%20Patterns/) | Pine v6 candlestick-pattern overlay with Three-Candle and Gann confluence options |
| [`Renko%20and%20SuperTrend/`](Renko%20and%20SuperTrend/) | ASJR Renko and SuperTrend V2 test release: V4-style contiguous bricks plus brick-aligned SuperTrend overlay; prior versions preserved |
| [`Renko/`](Renko/) | ASJR Renko V4 Pine v6: contiguous green/red price bricks, scroll/zoom-aware historical reconstruction, intraday and daily charts; prior versions preserved |
| [`Gann/`](Gann/) | Gann book studies and research/source-comparison notes |
| [`Rudra-DDB/Gann/`](Rudra-DDB/Gann/) | Fixed-anchor INTC Gann research, daily records and historical study |
| [`utils/asjr_small_repeatable_v1.py`](utils/asjr_small_repeatable_v1.py) | EMA/VWAP pullback research and signal diagnostics |
| [`tests/`](tests/) | Small Repeatable smoke test |

## Strategy catalogue and entry/exit rules

**Status key:** *Alert/watch* = signals or decision support, **not** automatic orders. *Backtest/research* = simulated or exploratory logic, **not** verified live results. Each linked source or strategy document is the authority for its particular version.

| Strategy | Core entry / trigger | Exit, stop or outcome model | Implementation |
| --- | --- | --- | --- |
| **ASJR Small Repeatable V1** | 5m directional EMA/VWAP regime; pullback to EMA area, confirmation candle and break of its high/low; first two signals per episode | Candidate diagnostics (MFE/MAE), optional R/R evaluation and chart review; no final optimised trade contract | [Code](utils/asjr_small_repeatable_v1.py) · [Test](tests/test_small_repeatable.py) |
| **Rudra Three-Candle — causal V1** | 5m bullish C2 with lower rejection wick, C1-low sweep and reclaim; after C2 closes, stop-buy at C2 body top on C3 break | Initial SL at C2 open; R-based step trail, effective on later bars; conservative same-bar ambiguity treatment | [Code](three_candle/three_candle_v1.py) · [Entry guide](three_candle/V1_ENTRY_GUIDE.md) |
| **Three-Candle pattern / V2 structure research** | C1 range → C2 liquidity sweep → C3 body-break confirmation; alternative relaxed, structure/CHOCH/BOS and location filters under study | Variant-dependent structural stop and step-trail or research outcomes; distinguish candidates from executable fills | [Learning engine](three_candle/three_candle_learing.py) · [Structure](three_candle/market_structure_v2.py) |
| **Rudra-Gold V2** | Complete 15m C1/C2/C3 from 5m data; C2 sweeps previous high/low, C3 confirms, enter at C4 open | SL at C2 extreme, reject risk over 0.20%; experiment with step, confirmed swing or partial+swing exits | [Backtest](three_candle/backtest_gold_v2.py) · [Rules](three_candle/GOLD_V2_BACKTEST.md) |
| **MA Strategy V1** | Independent MES moving-average alignment / slope setup, using IBKR history; BUY-side research | Configurable 1R protective stop and step trail, EMA9 exit or fixed-R target | [Code](three_candle/ma_strategy_v1.py) |
| **MA Strategy V2** | EMA9 crosses EMA21; both 3-bar slopes agree, RSI14 above/below 50, ADX14 >20 and rising | Next-candle-open research entry, fixed-point initial SL and simulated exits | [Code](three_candle/ma_strategy_v2.py) |
| **Rudra Reversal 1H** | Long-only: at least two of last three completed 1H candles touch/near lower BB(20,2); 0.15% tolerance and minimum 20% range-depth filter | Reference entry at signal close; exit at/near upper BB; maximum two reconstructed positions per ticker | [Code](ASJR_Analyst/Strategies/RudraReversal1H/rudra_reversal.py) |
| **4% Mean Reversal alert** | First completed 5m candle down at least 4% from the *previous completed daily close* | Watch levels: **SL -1%, TP +4%** from detected close; alert only | [Rules](ASJR_Analyst/Strategies/MeanReversal4Pct/README.md) · [Code](ASJR_Analyst/Strategies/MeanReversal4Pct/mean_reversal.py) |
| **Bollinger mean reversal — 4H** | Long after completed 4H-style candle **closes below** lower BB(20,2) | Exit on later completed close above upper BB; no fixed SL/TP in the plain model | [Code](Backtesting/MeanReversal/bb_mean_reversal_backtest.py) |
| **Bollinger + ADX** | Same lower-band close, gated by a low-trend-strength ADX filter | Later completed close above upper band; backtest research only | [Code](Backtesting/MeanReversal/bb_mean_reversal_adx_backtest.py) |
| **VWAP + EMA9** | 5m bullish RTH VWAP reclaim above rising EMA9, with time-of-day relative-volume and candle-quality checks | Next-bar signal-high break, stop beyond signal low, nominal **3R** target; other close/EMA exits in test variants | [Code](Backtesting/VWAP_EMA9/vwap_ema9_detector.py) |
| **NQ Session / Opening Range Breakout** | Confirmed 5m close outside a defined session opening range; optional EMA alignment, retest and candle filters | Entry next bar open, configurable range/ATR/confirmation stop and R:R target; flatten by session cutoff | [Code](Backtesting/SessionBreakout/nq_session_breakout_5m.py) |
| **Rudra-Gann price retest V1** | Break a calculated Gann level, retest/reject it, then require a completed bearish candle confirmation | Next 5m open short, stop above confirmation high + tick, **2R** target; conservative stop-first testing | [Rules](RudraScanner/RudraGann/STRATEGY.md) · [Code](RudraScanner/RudraGann/strategy.py) |
| **Rudra DDB 15m EMA/Gann BUY WATCH** | First completed 15m candle with **entire real body above EMA9**, and **EMA9 > EMA20**, evaluated from contiguous broker 5m bars | No trade execution; watch/alert plus nearby calculated Gann levels | [Rules](RudraScanner/DDB_EMA_GANN_LIVE.md) · [Code](RudraScanner/ddb_ema_gann_5m.py) |
| **Premarket / session RVOL research** | Cumulative completed-bar relative volume versus prior comparable sessions; low RVOL5 ≤0.58, high RVOL5 ≥2.00 research classes | Discovery/filtering, not an independent buy or sell order | [Code](RudraScanner/premarket_rvol.py) · [Spec](ASJR_Analyst/RUDRA_PREMARKET_SPEC.md) |

**Important:** These are distinct models. Some are long-only, some consider both directions, and some merely generate alerts. Stops, R definitions, sessions, volume tests and timeframes **must not be transferred between variants without re-running the study**.

## Three-Candle research

The [`three_candle/`](three_candle/) folder contains multiple related **but intentionally different** C1/C2/C3 designs.

### 1. Liquidity-sweep concept

- **C1 — Reference:** establishes the preceding candle/range.
- **C2 — Sweep/rejection:** trades through a C1 extreme; particular versions additionally require a wick/body ratio and reclaim.
- **C3 — Confirmation/trigger:** breaks an identified C2 body or high/low level; whether the candle must *close* to confirm depends on the variant.
- **BUY:** sweep below C1 low and bullish trigger. **SELL:** mirror around C1 high where the specific implementation supports shorts.

**Executable sequencing is central:** A C3 close, its final volume and its final high/low are not known at the start of C3. The [causal V1](three_candle/V1_ENTRY_GUIDE.md) places its trigger after **C2 closes**, instead of using C3's future volume to justify an earlier fill.

### 2. Research variants

| Variant / resource | What is being studied |
| --- | --- |
| [`three_candle.py`](three_candle/three_candle.py) · [Strategy comparison](three_candle/STRATEGY.md) | Historical RTH sweep/reclaim reproduction versus separate Yahoo-based breakout simulator; their results are **not interchangeable** |
| [`three_candle_v1.py`](three_candle/three_candle_v1.py) | Causal C2-body breakout entry on MES 5m data, with C2-open stop and stepped trailing |
| [`three_candle_learing.py`](three_candle/three_candle_learing.py) | Candidate scanning, condition-by-condition explanations, location/volume/wick checks and visual learning plots |
| [`three_candle_relax_mode_v1.py`](three_candle/three_candle_relax_mode_v1.py) · [MES research](three_candle/results/MES_2026-09_10_ThreeCandle_RELAX_MASTER_GUIDE.md) | Relaxed sweep/body/volume profiles, including kept-and-labelled rejected candidates |
| [`market_structure_v2.py`](three_candle/market_structure_v2.py) | Confirmed pivots, structure breaks (BOS), change of character (CHOCH), ATR and V-shaped reversal diagnostics |
| [`backtest_gold_v2.py`](three_candle/backtest_gold_v2.py) | Separate Gold 15m C2-sweep/C3-confirmation strategy and multiple simulated exits |
| [`test_three_candle.ipynb`](three_candle/test_three_candle.ipynb) | Interactive chart and notebook review |
| [`results/`](three_candle/results/) | Timestamped research CSVs, filter matrices and methodological reports |

**Historical interpretation:** The documented September study's 83 setups and subsequent 1R/2R/3R **price touches** are *not* 83 proven executed wins. Entry/stop sequence, costs and intrabar order require separate validation. See the [strategy contract](three_candle/STRATEGY.md) and [research results](three_candle/results/).

## Gann price levels and price-action research

ASJR investigates **W. D. Gann-inspired price geometry**, with reproducible mathematical conventions rather than unsupported claims that a level must act as support or resistance.

### Square-of-Nine / square-root rotation

For a positive reference price `P` and relative angle `θ`, one modern research convention is:

`Upper(P, θ) = (√P + θ/180)²`  
`Lower(P, θ) = (√P − θ/180)²`, where the inner root stays positive.

Research angles include **45°, 90°, 135°, 180°, 270° and 360°**. The anchor may be static or derived from a *confirmed* price reference. A calculated level is a **watch area**, not an automatic entry. Require additional price-action confirmation, risk controls and market context.

Another **separate**, historically used ASJR horizontal-level experiment uses `n²` for odd integer `n`, `n² + 1` for even `n`, and intermediate subdivisions. It is documented in [Rudra-Gann strategy research](RudraScanner/RudraGann/STRATEGY.md) and [DDB EMA/Gann alerts](RudraScanner/DDB_EMA_GANN_LIVE.md). **Do not conflate these two level-generation methods.**

Further research includes **Gann level sweep/reclaim**, close-break → retest → candle confirmation, fixed-anchor INTC level tracking, Gann price/angle confluence and support/resistance chart overlays.

- [Gann Ideas source and documentation](Gann%20Ideas/)
- [Gann mathematical study notes](Gann%20Ideas/GANN_STUDY_NOTES.md)
- [Rudra-Gann price-action experiment](RudraScanner/RudraGann/STRATEGY.md)
- [INTC fixed-anchor Gann research](Rudra-DDB/Gann/README.md)

## Gann time cycles and Time = Price

**Gann time study is a separate research topic from the horizontal price levels.** The principle being examined is whether independently defined *time windows* and *price-level interactions* show reproducible confluence around market turning points. This is a hypothesis to test, **not a forecast guarantee**.

The [ASJR Gann Ideas Pine V15](Gann%20Ideas/ASJR_Gann_Ideas_V15.pine) overlay includes **exactly two independent vertical time-cycle switches with editable lengths**:

| Switch | Length | Independent unit choices | Example interpretation |
| --- | --- | --- | --- |
| **Cycle A** | Editable, default **12** | `bars / mi / hh / day / m / y` | 12 bars by default; set 10 bars, 100 bars, etc. |
| **Cycle B** | Editable, default **90** | `bars / mi / hh / day / m / y` | 90 bars by default; independently set 10 or 100 bars. |

- `bars` = chart bars; `mi` = minutes; `hh` = hours; `day` = elapsed 24-hour days; `m` = calendar months; `y` = calendar years.
- Both have their **own** enable switch, editable length (1–500) and unit dropdown. **V12 additionally supports a Pivot HIGH or Pivot LOW cycle anchor that updates when the visible chart range changes**, plus an unchanged Manual UTC anchor.
- **12 and 90 are just the default lengths, not fixed cycles or years.** Change them to 10, 100 or any allowed period according to the selected unit.
- **Release policy:** Every new ASJR Gann version is published as a new numbered Pine file; older versions are preserved in GitHub.
- Market closures, missing candles, exchange calendars and DST can affect where an eligible vertical line appears. Time-only signals are insufficient to enter a trade.
- Explore a time window **together with** Gann price level, candle confirmation, trend and location. Compare against non-cycle baseline dates rather than selecting only successful examples.

More detail: [Gann Ideas README](Gann%20Ideas/README.md) · [Gann study notes](Gann%20Ideas/GANN_STUDY_NOTES.md).

## Gann learning and historical studies

The research also includes notes and source comparisons related to W. D. Gann's writing and later educational interpretations:

- **Square of Nine / square-root angles:** exact arithmetic, static versus dynamic anchors, angle/price conversions and tick rounding.
- **Factor of Eight, yearly highs/lows, squares, cubes, Square of 360:** eight price-tool families investigated as independently selectable indicator methods.
- **Time and seasonal cycles:** trading-calendar timing, historical 12/90-cycle discussions and the difference between calendar cycles and chart-bar cycles.
- **Time = Price:** hypothesis of intersecting time and price geometry, requiring independent tests instead of retrospective chart fitting.
- **Source criticism:** separate material attributed to Gann, later teaching conventions, screenshots and ASJR's own working implementations.

Reading/research files: [`Gann/Gann book source comparison`](Gann/BOOK_SOURCE_COMPARISON.md), [`Gann Ideas/GANN_STUDY_NOTES.md`](Gann%20Ideas/GANN_STUDY_NOTES.md), and [`Rudra-DDB/Gann`](Rudra-DDB/Gann/).

**Attribution note:** Dynamic H/C and Square-of-360 formulations in the Pine prototype are documented *working interpretations*, not verified replicas of a third-party proprietary indicator or authenticated original Gann algorithms. Historical/astronomical correlations have not been shown to have predictive power here.

## Books and further reading

ASJR combines hands-on market research with the study of classic trading literature. The titles below help contextualise **price action, market structure, candlesticks, risk management and Gann-inspired price/time analysis**. The list distinguishes material studied in the project from **additional reference reading**; mentioning a book does not mean its full contents have been read or its methods reproduced.

### W. D. Gann — studied and discussed

| Book | Author | Relevance to ASJR |
| --- | --- | --- |
| **Truth of the Stock Tape** (1923) | W. D. Gann | Tape reading, price/volume behaviour, trends and market participation; discussed in the project’s ongoing Gann study |
| **The Tunnel Thru the Air; Or, Looking Back from 1940** (1927) | W. D. Gann | Historical cycles, time, forecasting ideas and source-text study; chapter notes and Nepali translation research are tracked separately |
| **Speculation: A Profitable Profession** | W. D. Gann | Principles of speculation, discipline and market reasoning; discussed as part of the Gann reading programme |

**Further Gann bibliography:** *45 Years in Wall Street* and *How to Make Profits Trading in Commodities* are additional titles relevant to the time-cycle, trend and trading-method research. They are **reference/future-reading titles**, not represented here as completed book studies.

See [Gann book/source audit](Gann/BOOK_SOURCE_COMPARISON.md), [Gann learning notes](Gann%20Ideas/GANN_STUDY_NOTES.md) and [Gann project directory](Gann/). The book-source audit documents incomplete translations and verification limits; those are not publicly certified editions.

### Other trading and technical-analysis reference books

These are **widely used background references relevant to the topics investigated in ASJR**—not claims that the project has implemented a named author's proprietary method, followed each book end-to-end or independently verified its trading results.

| Book | Author | Related ASJR topic |
| --- | --- | --- |
| **Japanese Candlestick Charting Techniques** | Steve Nison | Candle anatomy, engulfing, stars, hammer/pin-bar context and pattern research |
| **Technical Analysis of the Financial Markets** | John J. Murphy | Trend, support/resistance, moving averages, momentum and multi-timeframe context |
| **Trading for a Living** | Dr. Alexander Elder | Trading systems, market psychology, confirmation and risk discipline |
| **Trade Your Way to Financial Freedom** | Van K. Tharp | Position sizing, risk, expectancy and R-multiple evaluation |
| **Reminiscences of a Stock Operator** | Edwin Lefèvre | Speculation, trend behaviour, market psychology and lessons in risk |

The strategy source files and test reports—not these books alone—define the exact rules used in ASJR.

## Research references and source material

For readers wanting to **trace a rule to its code, data definition or test**, useful starting points include:

| Reference | How it is used |
| --- | --- |
| [ASJR Gann Ideas — study notes](Gann%20Ideas/GANN_STUDY_NOTES.md) | Square-of-Nine mathematical convention, time cycles, fixed/dynamic anchors and attribution caveats |
| [Gann book source comparison](Gann/BOOK_SOURCE_COMPARISON.md) | Research provenance and limitations of chapter translation/source verification |
| [Three-Candle strategy contract](three_candle/STRATEGY.md) | Explicit distinctions between historical setup studies and executable-entry variants |
| [Three-Candle historical research results](three_candle/results/) | Candidate matrices, validation notes, archived samples and outcomes |
| [Rudra-Gann strategy study](RudraScanner/RudraGann/STRATEGY.md) | Price-level calculation and close-break/retest/candle confirmation model |
| [Gold V2 experiment](three_candle/GOLD_V2_BACKTEST.md) | Reproducible candle, stop and exit variants with research limitations |
| [RudraScanner research guide](RudraScanner/FINAL_RESEARCH_AND_ALERT_GUIDE.md) | Broker scanner terminology, saved datasets, candidate rankings and alert-state caveats |
| [IBKR 24-hour data import guide](Backtesting/DataLoader/IBKR_24H_IMPORT.md) | Historical data collection and session-aware market-data handling |
| [TradingView Pine Script documentation](https://www.tradingview.com/pine-script-docs/) | Language and indicator-platform reference |
| [Interactive Brokers API documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/) | Broker interface and market-data API background |

**Sources and attribution:** Original books, independent educational sources, exchange/broker feeds and ASJR's own models should be distinguished. Indicators and backtests here are original research implementations **informed by general published trading concepts**; they are not authenticated reproductions of book-specific or third-party proprietary systems.

## TradingView Pine Scripts

TradingView indicator source lives in dedicated folders.

| Indicator | Main features | Source / guide |
| --- | --- | --- |
| **ASJR Gann Ideas V15** | Stable historical **Pivot LOW/HIGH** cycle phases independent of chart viewport; completed historical lines retained up to the drawing budget; Manual UTC fixed anchor; 12/90 default cycle lengths and monk colours preserved | [V15 Pine source](Gann%20Ideas/ASJR_Gann_Ideas_V15.pine) · [Guide](Gann%20Ideas/README.md) |
| **ASJR Gann Ideas V1–V5** | Preserved development history for levels, colour controls, label placement and right-side label spacing | [Versions folder](Gann%20Ideas/) |
| **ASJR Candle Patterns** | 17 selectable candlestick pattern groups, bullish/bearish highlighting, optional quality gates and Gann reference confluence | [Pine source](Candle%20Patterns/ASJR_Candle_Patterns.pine) · [Guide](Candle%20Patterns/README.md) |
| **ASJR Renko and SuperTrend V2 (test release)** | Contiguous V4-style Renko bricks, packed SuperTrend steps, Source Close, Traditional 8.33 / ATR / % sizing, ST(14, 3), scrolling reconstruction and optional flip markers. Validation pending. | [Pine V2](Renko%20and%20SuperTrend/ASJR_Renko_and_SuperTrend_V2.pine) · [V1 archive](Renko%20and%20SuperTrend/ASJR_Renko_and_SuperTrend_v1.pine) · [Guide](Renko%20and%20SuperTrend/README.md) |
| **ASJR Renko V4 — Scroll-Aware, Brick Only** | Contiguous green/red bricks reconstructed through the chart's visible right edge, re-rendered on scroll/zoom; ATR snapshot / fixed / percent snapshot size, 1m/5m/15m/1H/4H/daily. No EMA/BUY/SELL icons. | [V4 Pine source](Renko/ASJR_Renko_V4.pine) · [Guide](Renko/README.md) · [V3](Renko/ASJR_Renko_V3.pine) |
| **ASJR Volume Delta Pressure V2** | 12 price-zone OHLCV pressure estimate; existing EMA21 anchor; independently styled EMA9 and EMA200 chart overlays | [V2 Pine source](Volume%20Delta%20Pressure/ASJR_Volume_Delta_Pressure_V2.pine) · [Guide](Volume%20Delta%20Pressure/README.md) |
| **ASJR 360 View V5** | EMA21 trend-first GREEN/RED after completed aligned EMA candles (or optional strict 360 mode); pressure and RSI still shown and checked; RVOL-at-Time 5/20 reference only; bordered two-row configurable dashboard; retains V4 plot-count fix. | [V5 Pine source](ASJR%20360%20View/ASJR_360_View_V5.pine) · [Guide](ASJR%20360%20View/README.md) |
| **ASJR Gann Swing V2** | Two independently toggleable overlays: diagonal 1/2/3-bar Gann Swing path and purple confirmed High/Low step line; adjustable Monk (Lama) colours, widths and reversal alerts | [V2 Pine source](ASJR-Gann-Swing/ASJR_Gann_Swing_V2.pine) · [V1](ASJR-Gann-Swing/ASJR_Gann_Swing_V1.pine) · [Guide](ASJR-Gann-Swing/README.md) |

**Eight Gann price families:** Factor of Eight; Yearly Highs/Lows; Power of Squares; Power of Cubes; Square of Nine Static; Square of Nine Dynamic H; Square of Nine Dynamic C; Square of 360. The additional two switches are the **12 and 90 vertical cycles**.

**Candle Patterns** covers engulfing, hammer/shooting star, morning/evening star, pin bars, inside/outside bars, tweezers, piercing/dark-cloud patterns, harami, doji, marubozu, three soldiers/crows, **Gann level sweep + reclaim**, and **ASJR Three Candle Detector**. The Pine Three-Candle visual detector is **not identical** to every Python Three-Candle entry model.

**Renko limitation:** ASJR Renko V4 reconstructs contiguous synthetic bricks from completed ordinary chart closes up to the visible chart's right edge (not tick data). The brick positions are packed visually and **do not mark real formation timestamps**. ATR/percentage snapshots can change when browsing older dates; for comparable history use Fixed. Use actual market candles and prices for trading execution, never a synthetic brick as a fill. See the [Renko guide](Renko/README.md).

**Validation:** Pine files are committed source/research builds; the folders document that TradingView Pine Editor compilation and live-chart validation were **not yet independently confirmed**. Python reference tests validate selected numerical/pattern examples, **not** the TradingView runtime. No Pine indicator in this repository is an automated broker order strategy.

## Rudra scanner, DDB and market intelligence

The [RudraScanner](RudraScanner/) and [ASJR Analyst](ASJR_Analyst/) components research a **market → sector → stock** workflow, combining watchlists with technical features and market context.

- **Broker scanner discovery:** IBKR gainers, losers, hot-by-volume and most-active categories, with additional experimental scanner and momentum ranking paths. The raw scanner membership is distinct from filtered research rankings. See [scanner guide](RudraScanner/FINAL_RESEARCH_AND_ALERT_GUIDE.md).
- **Top In Play / momentum:** Candidate boards, rankings, intraday activity, session change and volume diagnostics; *scanner membership is not itself a buy/sell signal*. See [top_in_play.py](RudraScanner/top_in_play.py) and [momentum_movers.py](RudraScanner/momentum_movers.py).
- **Premarket volume:** Completed 5-minute relative-volume profiles, low/high RVOL classifications and quality gates. See [premarket_rvol.py](RudraScanner/premarket_rvol.py).
- **Rudra DDB A/B/C:** Grouped stock research/watch universe, 15-minute EMA9/EMA20 BUY WATCH and ASJR Gann nearby levels. See [DDB research groups](RudraScanner/RUDRA_DDB_GROUPS.md), [alert specification](RudraScanner/DDB_EMA_GANN_LIVE.md).
- **Research / AI analysis:** News catalysts, index/sector context, potential support/resistance, watchlists and multi-factor *360-style* discretionary review. **360 scores should not be read as an independently validated automated signal engine.**
- **Alerts and integration:** IBKR-derived price data, processed reports and Discord-oriented delivery hooks, subject to environment-specific configuration, availability and deployment verification.

The repository is **not** a turnkey live trading bot: having code committed does not prove a remote bot is up to date, a Discord alert was delivered, or an order was placed.

## Data engineering, testing and reproducibility

Key research engineering themes:

1. **Data source provenance:** Keep IBKR dated futures contracts, Yahoo continuous futures and third-party stitched data explicitly distinguished.
2. **Multi-timeframe construction:** Resample complete 5m candles into 15m/1H where required; do not silently fill missing bars.
3. **Session-aware processing:** Recognise premarket, regular and postmarket sessions; preserve original market timestamps and report research times in **Europe/London** where applicable.
4. **No look-ahead:** Generate confirmed signals from information actually available at decision time; simulate entry on a later candle when required.
5. **Risk and outcome accounting:** Track SL, risk distance, R milestones, MFE/MAE, gap/stop priority, open/unfilled/rejected states and ambiguous OHLC cases.
6. **Reproducibility:** Version rules, keep strategy variants separate, record period/instrument/data source and distinguish historical samples from untouched holdout data.
7. **Automated checks:** Unit tests in [`RudraScanner/tests/`](RudraScanner/tests/), [`Gann Ideas/tests/`](Gann%20Ideas/tests/), [`Candle Patterns/tests/`](Candle%20Patterns/tests/) and independent strategy tests.

Useful data tools: [`Backtesting/DataLoader/`](Backtesting/DataLoader/) · [`three_candle/download_mes_mnq.py`](three_candle/download_mes_mnq.py) · [`three_candle/split_ibkr_daily.py`](three_candle/split_ibkr_daily.py) · [`IBKR_import.py`](IBKR_import.py).

## Getting started

Clone the repository and install the small common Python dependency set:

```bash
git clone https://github.com/raghunathbhandari/ASJR.git
cd ASJR
python -m pip install -r requirements.txt
```

Run the original signal/chart exploration:

```bash
python tests/test_small_repeatable.py
```

The default Small Repeatable smoke test studies **QQQ, 30 days**, and plots recent candidate signals. Data-provider limits and availability can change.

Run selected reference/unit suites:

```bash
python -m unittest discover -s "Gann Ideas/tests" -p "test_*.py"
python -m unittest discover -s "Candle Patterns/tests" -p "test_*.py"
python -m unittest discover -s RudraScanner/tests -p "test_*.py"
```

**Environment notes:** Many modules need additional packages, dated IBKR CSVs, a running IBKR Gateway or external datasets. Run them only after reading their specific folder instructions. `requirements.txt` covers common research libraries, **not every optional broker, notebook, automation or backtest dependency**. Do not commit broker credentials, Discord tokens or private account information.

## Research limitations and disclaimer

- **Research and educational use only. Not financial advice.**
- No backtest, model score, Gann level or candle pattern guarantees future performance.
- Results can be affected by **survivorship/selection bias, future-data leakage, session/DST handling, dataset gaps, futures rolls, intrabar sequencing and parameter overfitting**.
- A simulated price touch is **not** an executable fill; gross price points are **not** necessarily account profits. Fees, bid/ask spreads, slippage, margin, position sizing and risk controls must be included before real-world evaluation.
- Some Gann and time-cycle methods are **experimental interpretations**, not certified original formulas.
- Public source visibility is not a grant of rights beyond an applicable licence; check repository licensing before reuse.

---

**Maintained by [Raghu Nath Bhandari](https://github.com/raghunathbhandari)** · ASJR Trading · **README, Since 2022, Last updated 21 November 2026**.

*Built to study market behaviour systematically, test ideas honestly, and turn repeatable research into better-informed trading decisions.*
