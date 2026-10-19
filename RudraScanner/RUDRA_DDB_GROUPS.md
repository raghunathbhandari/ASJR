## LOCKED 2026-10-16 — RUDRA-DDB OFFICIAL MASTER LIST (USER CONFIRMED)

**This supersedes older draft/10-ticker lists and older fundamental Pending statements.** Official universe is **39 tickers, Group A 22 + Group B 17**. Group A: INTC, AKAM, WDC, STX, KLAC, CIEN, TER, LRCX, VRT, PANW, AMD, QCOM, TSM, SWKS, CRWD, ETN, KEYS, FLEX, GLW, COHR, ASML, AMAT. Group B: CBOE, ZTS, V, CME, CDW, PGR, AJG, JKHY, O, YUM, VRSK, MRSH, NSC, PEP, PAYX, NEE, MCK.

**Canonical source of truth:** `RudraScanner/ResearchData/DDB_OPPOSITE_2026-10-16/DDB_39_3M_RANGE_SCREEN_2026-10-16.csv` (as of 2026-10-16 commit `88192a61`). The user's desired full display is group-separated with ticker, 3-month historical bottom/top, 3M range percent, completed daily-close swings >=7%, percent above 3M bottom/DD band, **Fundamental** and **Dilution** as TWO DISTINCT columns; retain sector, prices/as-of date, holding notes, and fiscal quarter/evidence URLs in the underlying master. Data are historical through Oct 15, not live. A daily-close zero swing count does not imply no 4H swings (e.g. V). Clusters/extremes are not proven range boundaries.

**Fundamental scoring LOCKED:** use newest available published quarter, or previous quarter if newest audit/report is not available. PASS = profitable OR positive year-over-year revenue growth. FAIL only if neither holds per a verified quarter. The 2026-10-16 master currently records **39/39 as PASS on this simplified screening rule**, with quarter identifiers and reference URLs; do not imply comprehensive balance-sheet or audit clearance. **Dilution independent of Fund:** preserve specific flags for INTC (equity offering/conditional warrants), AKAM (convertible notes/warrants), WDC (historical preferred conversion), VRT (debt offering, not direct common-share dilution), COHR (historical preferred conversion), AJG (historical equity offering), NEE (equity units future settlement). Other rows say no specific event identified in **initial** screen; NOT a full SEC no-dilution guarantee. Six issuer equity/convertible events plus VRT debt-financing flag; do not collapse into misleading count. User currently HOLDS AKAM (size/entry unknown); AKAM Fundamental PASS + convertibles flagged. Never automatically fail fundamentally healthy names for dilution flag. This is a research watchlist, not trading clearance.

**Still outstanding (do not misstate as completed):** issuer-level comprehensive share-dilution SEC review across all 39; independent confirmation that prior quarterly source links resolve and fully support each PASS; all-39 1Y swing comparison export/workflow success and validation of repeated two-sided top/bottom boundary tests. These are separate deeper validations, not reasons to replace all Fund scores with Pending. Do not alter bot/Chakra operation or claim live prices/VPS processing.

---

## 2026-10-16 — Fundamental report fallback (user confirmed)
For each ticker, use the newest verified published financial report. If the current quarter's audit is pending or not yet available, use the **last completed quarterly financial report** as the fundamental evidence base; label the fiscal quarter and publication date. Fundamental PASS = reported profitability OR positive year-over-year revenue growth; FAIL only when latest available verified quarter establishes neither. Keep dilution/financing separately flagged, even when Fundamental PASS. Do not invent outcomes or quietly use an older quarter without identifying it. If no verified quarterly report is accessible, state unverified rather than fabricate PASS/FAIL. Use established 39-ticker A/B master table format.

---

## 2026-10-16 — Latest user reporting preference
Use the last 39-ticker Rudra-DDB Group A/B report as the fixed table base. Fundamental result: PASS when latest verified report shows profit OR positive YoY revenue growth; FAIL only when verified report shows neither. Dilution risk remains its own separate flagged column and does not by itself change fundamental PASS. **Do not show a generic PENDING status in the finished user-facing report**; obtain missing issuer data first. If verification is unavailable, disclose that clearly as unverified rather than mislabeling PASS or FAIL. Preserve current DD columns and holdings.

---

## 2026-10-16 — USER UPDATED FUNDAMENTAL PASS POLICY (SUPERSEDES PRIOR DILUTION BLOCK)
**Fundamental PASS criterion:** confirmed profitability OR positive revenue growth qualifies for fundamental PASS under user's simplified screen. Report which test passed and filing period/source. Positive revenue level alone without growth/profit is not evidence of strength; clarify in edge cases. **Dilution is a separate FLAG/AUDIT informational column, NOT an automatic fundamental FAIL, HOLD, or trading prohibition.** Check offerings/convertible shares/warrants and flag risk without blocking PASS. Serious solvency or financial distress still warrants separate caution. Never invent company data or give PASS without verified profitability or positive growth. AKAM: already evidenced Q2 2026 net income $79.4M and revenue +5% YoY, hence **FUNDAMENTAL PASS**, with convertible financing risk flagged separately; user currently holds AKAM (quantity/cost not provided). The previously documented stricter gate requiring dilution clearance is superseded for scoring, though trading confirmation still requires price structure.

---

## 2026-10-16 — USER CONFIRMED RUDRA-DDB MASTER LIST + FUNDAMENTAL GATE

**Trigger:** when user writes "Rudra-DDB", present both full expanded groups with all available columns: Group, ticker, sector, 3M historical bottom, 3M historical top, 3M range %, 3M completed legs >=7%, 3M bottom/top *candidate* pivot counts, 1Y >=25% swings and 1Y range once available, last verified close and timestamp, % above 3M bottom, color, DD status, fundamental status and dilution risk. For missing annual data mark PENDING, not 0. Source: `RudraScanner/ResearchData/DDB_OPPOSITE_2026-10-16/DDB_39_3M_RANGE_SCREEN_2026-10-16.csv`; annual 39-stock collector `RudraScanner/research_ddb_39_1y.py` and GitHub workflow pending verified output. Historical extremes are NOT validated two-sided AOI. Color: GREEN <=2% above bottom; YELLOW >2%-5%; AMBER >5%; below range RED. DD WATCH is NOT a buy order. Do not substitute cached close for live quotes.

**Locked groups (39):**
- A (22): INTC, AKAM, WDC, STX, KLAC, CIEN, TER, LRCX, VRT, PANW, AMD, QCOM, TSM, SWKS, CRWD, ETN, KEYS, FLEX, GLW, COHR, ASML, AMAT.
- B (17): CBOE, ZTS, V, CME, CDW, PGR, AJG, JKHY, O, YUM, VRSK, MRSH, NSC, PEP, PAYX, NEE, MCK.
Original 5+5 historical classification preserved separately as described below.

**User trading exclusion:** weak fundamentals, distressed balance sheets, or material unmitigated shareholder dilution risk => NO TRADE. Keep any such names in research reference only (for correlation) rather than silently deleting them. Full issuer-filing audit required for each company; don't infer 39 fundamental passes. Check 10-K/10-Q, cash flow, debt/maturities, outstanding shares, ATM/convertible/equity-unit offerings, shelf registrations, warrants, secondary issuance, capital needs and earnings. Use labels PASS / HOLD_RISK / PENDING_VERIFY, and source+as-of dates. Correlation/technical ranges do not override this gate.

**Verified initial flags at 2026-10-16:** INTC HOLD_RISK: Q2 2026 10-Q describes net losses, escrowed government shares and conditional DOC warrants; review dilution effects before investing: https://www.intc.com/filings-reports/all-sec-filings/content/0000050863-26-000157/intc-20260627.htm . NEE HOLD_REVIEW: Mar 3 2026 SEC filing describes $2.3bn equity units with future mandatory purchases of common stock: https://www.sec.gov/Archives/edgar/data/753308/000075330826000020/nee-20260303.htm . WDC operating cash flow was $3.929bn FY2026 vs $1.691bn FY2025, encouraging but NOT a comprehensive PASS: https://investor.wdc.com/static-files/885b2c03-508d-491d-8555-281fa5214179 . Other 36 company-specific diligence not yet completed => PENDING_VERIFY. Not all potential dilution is automatically disqualifying; assess magnitude and financing need rather than claim no risk.

---

# Rudra-DDB — Locked Group A and Group B research watchlists
Last updated: 2026-10-16
Data cutoff: completed US session 2026-10-15 (not live quotes)

> **2026-10-16 EXPANDED RESEARCH (39 candidates):** Original approved Group A/B membership below remains unchanged; the new INTC-relative expanded candidate lists, 545-instrument correlation screen, smaller-swing/4H Visa lessons and verified GitHub↔VPS access instructions are in [RUDRA_DDB_INTC_EXPANSION_2026-10-16.md](RUDRA_DDB_INTC_EXPANSION_2026-10-16.md). New names are exploratory, not qualified primary trading ranges.

## Group A — Discounted / bottom-side research
INTC, AKAM, WDC, STX, KLAC

## Group B — Strong / top-side research
CBOE, ZTS, V, CME, CDW

| Group A | 10-session return | Group B | 10-session return |
|---|---:|---|---:|
| INTC | -20.5% | CBOE | +11.1% |
| AKAM | -13.7% | ZTS | +13.5% |
| WDC | -22.9% | V | +11.1% |
| STX | -26.9% | CME | +9.2% |
| KLAC | -12.9% | CDW | +13.6% |

**The rows are NOT asserted pairwise opposites.** Measured out-of-phase
candidate pairs include INTC-CBOE, INTC-ZTS, INTC-V, INTC-CME and KLAC-CDW.
The original study examined 562 symbols with 560 valid datasets and found
historical inverse relationships; this is exploratory and vulnerable to
in-sample selection bias. All source statistics are historical, not predictive.

## Group roles and next-lot process
- Track both groups together using interactive normalized three-month price histories.
- Group A: potential bottom candidates. Require attractive support, liquidity sweep,
  stabilized base, bullish CHOCH, positive EMA9/EMA20 momentum and sector confirmation
  before a trade. Group B: currently stronger candidates for **later** pullback/reversal.
- Reassess the groups' actual range location each completed session; group labels can
  change or reverse. Distinguish approaching bottom from confirmed bottom.
- Watch Group B for a genuine discount while analyzing Group A entries, so the next
  batch of candidates is ready. No fixed schedule or Discord alerts authorized.
- Do not assume Group B tops are short signals or that A must be bought.
- Confirm market cap and fundamental durability independently, exclude weak
  fundamentals and penny stocks from investable recommendations.
- Validate historical inverse relationships out of sample, compare swing dates,
  inspect catalysts and earnings, and account for both groups falling together.

## Research source files
- RudraScanner/ResearchData/DDB_OPPOSITE_2026-10-16/DDB_TWO_GROUPS_REPORT.md
- RudraScanner/ResearchData/DDB_OPPOSITE_2026-10-16/ALL_STOCK_PHASES.csv
- RudraScanner/ResearchData/DDB_OPPOSITE_2026-10-16/BOTTOM_TOP_OPPOSITE_PAIRS.csv
- RudraScanner/ResearchData/DDB_OPPOSITE_2026-10-16/SECTOR_ETF_CORRELATIONS.csv


## Mandatory eligibility gates — locked 2026-10-16

**Gate 1: Fundamentally strong company (PASS required).** For investable Rudra-DDB candidates verify credible financial durability: material revenue/business franchise, earnings/operating cash generation or clearly demonstrated improving economics, healthy balance sheet/debt capacity, no near-term solvency/dilution issue, credible business moat and guidance. Exclude weak-fundamental penny/speculative names. If information is unverified, mark **PENDING** and DO NOT promote to actionable/watch AOI.

**Gate 2: Repeatedly TESTED BOTH boundaries (PASS required).** A valid DDB trading range needs at least **two independent touches/tests of the bottom support zone and two independent touches/tests of the top resistance zone** during the studied period, separated by a material intervening swing; prevent consecutive daily candles or wick noise being counted as separate tests. A one-off lowest close, highest close, or one zigzag turn is **not** a valid range. Assess zones with ATR-aware tolerance, timestamps, reversal reaction, and support/resistance reclaim. If either side has fewer than two genuine tests, label **UNCONFIRMED RANGE — DO NOT USE AS AOI OR FUTURE TOP TARGET**. The exact 2+2 threshold is a conservative working interpretation of user's 'tested multiple times', amend if they specify stricter count.

**Gate 3: Recent 3-month multi-swing structure and bottom-to-top rotation.** Repeated meaningful up/down movements (25%+ major legs for research), attractive current price, and bullish CHOCH/sweep/base before any buy. 1-year swing counts are descriptive only and cannot substitute for support and resistance retests.

**RETROACTIVE STATUS:** The saved RUDRA_DDB_GROUPS_1Y_SWINGS_AOI.md calculated bottom from the ten lowest closes of 64 days and future top from the sole 64-day maximum. Those numbers have NOT passed both-boundary retest validation; therefore **withdraw their status as actionable AOI and price targets until re-screened**. Retain as historical price references only. The existing Group A/B tickers remain exploratory and are NOT all assumed to pass fundamental or boundary tests.



## PRIMARY vs SECONDARY DDB lists — user clarification 2026-10-16

Do **not** discard stocks whose fundamentals or two-sided range tests are not verified. Maintain both tiers, separately for Group A and B:

- **PRIMARY TOP WATCHLIST** (must satisfy ALL): verifiably fundamentally strong/durable company; recent multi-swing range with >=2 independent, meaningfully separated tests of BOTH bottom support and top resistance; typical recurring trough-to-peak upside **at least 25% and preferably 25–50%** within the relevant three-month regime; current attractive AOI supported by verified retests; bullish setup/CHOCH required before any actual trade. Estimate actual repeated cycle amplitudes from validated paired swings, not theoretical distance to one untested historical high. Explicitly record support test count, resistance test count, and measured recurring range gain.
- **SECONDARY RESEARCH WATCHLIST**: promising discounted/strong business, large swing or inverse-group candidate but not yet confirmed on any primary gate. Keep it visible and label clearly which checks are pending/failed, and what would promote it.
- Historical Group A (INTC AKAM WDC STX KLAC) and Group B (CBOE ZTS V CME CDW) stay in their group membership regardless of primary/secondary tier pending formal rescreen. **Do not claim these names presently qualify for PRIMARY** without verified financial and range test evidence.
- A move substantially beyond 50% is not inherently disqualifying, but distinguish explosive/outlier price moves from repeatable 25–50% rotations; avoid speculative penny or weak-balance-sheet names. Do not translate every large one-way swing into a tested tradable range.
- Refresh tier whenever new completed candles/financial evidence arrive. Research only; no new bot automation or order modifications.



## Broad-market strict DDB rescreen result — 2026-10-16
Source: `RudraScanner/ResearchData/DDB_OPPOSITE_2026-10-16/DDB_STRICT_RETESTED_GROUPS_REPORT.md`.

Screened 560 saved daily historical series (S&P 500 membership plus supplied names and ETFs); used last 64 completed daily candles through Oct 15, 2026. Hard mechanical range: 2+ independently spaced confirmed support pivots, 2+ resistance pivots, within 7% tolerances, plus 2+ completed alternating range legs of 25-50%. **9 stocks passed structural price test**, of which **5 have provisional Yahoo-based $2B+ and positive earnings/cash flow fundamental flags**: CIEN 4/2 touches +37.7%, TER 4/2 +34.6%, LRCX 2/3 +31.8%, VRT 2/3 +28.4%, PANW 2/2 +27.0%. They are **PRIMARY_RESEARCH_PENDING_AUDIT, NOT verified primary buy-ready**. Remaining structural names AEHL, FVNNU, DNA, COHR stay SECONDARY. Historical level centers as saved in report need adjusted-price/corporate-action validation.

**Opposite rotation not yet validated:** no compelling pair among financially provisional tested-range names from a different sector. Prior Group A/Group B remain exploratory as before; do not represent the nine retested stocks as verified inverse groups, or confuse sector anticorrelation with reliably alternating individual stocks. Prior 1-year 25%+ swing counts do NOT establish two-sided repeated tests. The stock universe is expandable, with future sector diversification and out-of-sample multi-cycle checks required.


## Research priority update — 2026-10-16
Group A is now the main expansion priority. Keep original Group B (CBOE ZTS V CME CDW) unchanged as secondary/opposite-phase benchmarks; no need to add B tickers unless stronger evidence appears. Prioritize auditing CIEN (4 support/2 resistance, 37.7%), TER (4/2, 34.6%), LRCX (2/3, 31.8%), VRT (2/3, 28.4%) and PANW (2/2, 27.0%) as potential additions to Primary Group A, NOT approved primary or proven current-bottom entries. Validate split-adjusted prices, independent retest dates, 25-50% completed alternating legs, multiple-year recurrence, current phase and financial statements before promotion. Preserve original A names for comparison; no bot or trading changes authorized.
