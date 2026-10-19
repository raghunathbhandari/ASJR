# Rudra-DDB — INTC comparison, 39-name expansion, and GitHub↔VPS operator guide
Date: 2026-10-16. Price evidence through the completed 2026-10-15 US session. **Research, not trading signals.**

## Membership — preserve original labels
Original Group A: INTC, AKAM, WDC, STX, KLAC.
Original Group B: CBOE, ZTS, V, CME, CDW.
Earlier provisional A technical candidates: CIEN, TER, LRCX, VRT, PANW.

Expanded **candidate** Group A (22; similar-to-INTC research): INTC, AKAM, WDC, STX, KLAC, CIEN, TER, LRCX, VRT, PANW, AMD, QCOM, TSM, SWKS, CRWD, ETN, KEYS, FLEX, GLW, COHR, ASML, AMAT.
Expanded **candidate** Group B (17; inverse-to-INTC research): CBOE, ZTS, V, CME, CDW, PGR, AJG, JKHY, O, YUM, VRSK, MRSH, NSC, PEP, PAYX, NEE, MCK.

These expanded lists are exploratory and do NOT replace the original approved 5+5 grouping or satisfy fundamental/price validation automatically.

## Actual historical analysis
Input: `RudraScanner/ResearchData/DDB_OPPOSITE_2026-10-16/DAILY_CLOSES_3M.csv` (64 daily sessions), analyzed in an AI session against 545 other adequately observed instruments. Market ETFs were also present; displayed new stock candidates were manually curated from rankings. Calculations used Pearson correlation of paired daily returns; separately Pearson correlation of overlapping trailing 10-session price returns; opposite days = share of daily returns with opposite signs. All are in-sample correlations, not forecasts or evidence of a hedge.

New A examples, 10-session return correlations with INTC: AMD +0.79, QCOM +0.71, TSM +0.71, SWKS +0.69, CRWD +0.68, ETN +0.66, KEYS +0.63, FLEX +0.61, GLW +0.59, COHR +0.56, ASML +0.51, AMAT +0.49.
New B examples: PGR -0.85, AJG -0.82, JKHY -0.80, O -0.78, YUM -0.75, VRSK -0.75, MRSH -0.73, NSC -0.69, PEP -0.67, PAYX -0.61, NEE -0.59, MCK -0.58.
Correlations of overlapping 10-session returns are serially dependent and must be validated using rolling/out-of-sample windows and dated inverse swing sequences.

Exploratory three-month pivot analysis: daily closes, 4% reversal confirmation, prices within 7% of a reference pivot considered in one cluster, independent pivot locations >=5 sessions apart. **Cluster sizes alone do not establish a valid support/resistance range** because the separately selected upper/lower clusters may never alternate between the SAME two levels.

| New name | Group | Bottom clustered pivots | Top clustered pivots | Completed legs >=7% |
|---|---|---:|---:|---:|
| AMD | A | 4 | 4 | 8 |
| QCOM | A | 2 | 2 | 4 |
| TSM | A | 4 | 3 | 4 |
| SWKS | A | 2 | 2 | 6 |
| CRWD | A | 2 | 2 | 5 |
| ETN | A | 2 | 4 | 6 |
| KEYS | A | 4 | 3 | 6 |
| FLEX | A | 6 | 6 | 9 |
| GLW | A | 6 | 7 | 8 |
| COHR | A | 5 | 5 | 15 |
| ASML | A | 3 | 4 | 6 |
| AMAT | A | 3 | 4 | 8 |
| PGR | B | 2 | 3 | 4 |
| AJG | B | 4 | 3 | 5 |
| JKHY | B | 3 | 2 | 3 |
| O | B | 1 | 0 | 0 |
| YUM | B | 3 | 2 | 3 |
| VRSK | B | 3 | 3 | 5 |
| MRSH | B | 3 | 2 | 2 |
| NSC | B | 3 | 2 | 1 |
| PEP | B | 2 | 2 | 1 |
| PAYX | B | 2 | 3 | 3 |
| NEE | B | 1 | 0 | 0 |
| MCK | B | 4 | 3 | 5 |

Focus for next validation: A FLEX, GLW, COHR, AMD; B AJG, VRSK, MCK, PGR. O and NEE have comparatively weak confirmed 3M daily-close swing structures despite inverse correlations. All need a separate strong-fundamentals audit (capitalization, profits, cash flow, balance sheet, dilution/earnings); mid/large cap status should not be guessed solely from ticker.

## Correction: Visa V is NOT 'zero swings'
Saved `RUDRA_DDB_GROUPS_1Y_SWINGS_AOI.csv` reports **0 swings >=25%** under its annual daily-close zigzag definition. The user's 4H chart visibly measured a -7.62% decline and +12.63% rebound. That shows at least two measured sub-25% legs, not necessarily two *independent top tests and bottom tests*. Daily closes cannot reproduce 4H high/low swings. Collect actual 4H OHLCV when available and count dated legs and boundary tests; mark unavailable data as unverified, never zero.

## Locked DDB qualification and lessons
1. Strong fundamental businesses only; no penny/speculative weak-capitalization names in primary shortlist. PENDING never equals PASS.
2. Both support and resistance require >=2 genuine, distinct nonconsecutive tests, separated by real swings. Use ATR-aware zone width, price reaction and dated alternating traversals. Clustered-pivot count and 25%+ annual-leg count are *different* metrics.
3. Rolling ~3 months for repeatable up/down structures, not a 52-week drop alone. For each name show ticker, sector, actual verified support/resistance price, amplitude %, dated test counts, completed full/partial legs, quote timestamp/session, current range position, catalyst and fundamental verification.
4. **Do not force a fixed 25% threshold on quality large caps**: report both >=25% counts and smaller volatility-appropriate swing bins (e.g. >=7%, >=10%, >=15%) separately. Those bins are *research suggestions*, not a user-locked live scanner rule. Never relabel 0 >=25% as 0 total swings.
5. A/B classifications are defined by tested INTC similarity or inverse behavior; correlation alone does not imply contemporaneous switchable bottom/top opportunities. Perform out-of-sample stability checks; the originally approved A/B cohorts stay distinct from the expanded candidate pool.
6. Original 1Y calculated AOI from ten lowest closes and 64-day highest close was withdrawn as an **actionable** support/target. Revalidate before publishing price of interest. Need sweep/base/CHOCH and sector confirmation before entries.
7. Prefer interactive hoverable comparative price charts where available. Do not invent 4H candles, live quotes, correlations, or verified VPS execution.

## GitHub and VPS execution — read before requesting user SSH
Repository: `raghunathbhandari/ASJR` (main). VPS checkout `/root/trading/ASJR`; venv `/root/trading/venv_new/bin/python`. GitHub connector has repository file fetch/create/update; this does **not** itself grant an SSH terminal or arbitrary VPS shell.

**Verified AI → GitHub → VPS research bridge** (2026-10-16):
- Worker: `RudraScanner/research_bridge_worker.py`, systemd `asjr-research-bridge.service`, polls GitHub approximately each 60 seconds.
- AI writes allowlisted JSON requests to `RudraScanner/ResearchBridge/requests/research-XXXXXXXXXXXXX.json`; schema: exactly `{"id":"research-<13 digits>","schema_version":1,"operation":"health_check","batch":null}` (replace operation only with one supported type). Worker publishes `RudraScanner/ResearchBridge/results/<id>.json` after processing. **A GitHub request commit is not proof of a completed VPS job**.
- As last checked, code allowed **only** `health_check`, `research_46_batch` (integer batch 1..5), `research_46_finalize`, `research_46_publish`. New DDB collection or analysis is **NOT currently allowlisted**. Implement/tests/review an explicit safe DDB operation, deploy it via approved process, then check result JSON before claiming VPS execution. Never submit an unsupported operation and call it executed.
- Proven result examples: `research-2026101608501` health SUCCESS, `research-2026101610002` 10/10 Yahoo batch SUCCESS, and `research-2026101611051` 46-ticker collector/publish SUCCESS with 93 files, as recorded in `AI_SESSION_HANDOFF.md`. For any new job, check its own result and data outputs.
- For research changes requiring deployment, safe existing Discord controls: `!gitpull`, then only if needed `!runpy RudraScanner/scan_now\.py --bridge-refresh` (reloads research bridge service ONLY; does not restart Chakra). `!runpy RudraScanner/scan_now\.py --bridge-start` installed existing service previously. Do **not** run `--bridge-check` alongside active service. `!runSCommand` external Discord handler was stale/unverified; don't presume admin execution. No unrestricted shell through Discord.
- Preserve live Chakra, IBKR scanner jobs, Discord alerts/schedules and `/root/trading/utils/trading_sudarsan_chakra.py`. Do not expose GitHub credentials or Discord IDs. Follow `RudraScanner/ResearchBridge/README.md` and `ASJR_Analyst/OPERATIONAL_HANDOFF.md`.

## Recommended next work
Retrieve recent 4H OHLCV (especially V), and for all 39 candidates compute dated pivot legs (in %), verified *two-sided alternating* boundary tests, location within validated range and robust correlations split by time period. Compare fundamentals and earnings/catalysts; label PRIMARY only on independent PASS of both hard gates. Commit a reproducible script and supporting research output without touching trading infrastructure.
