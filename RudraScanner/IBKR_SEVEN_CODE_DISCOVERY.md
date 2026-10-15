# RudraScanner — Momentum Discovery + Seven IBKR Codes
## Canonical operating guide and AI handoff | 2026-10-15 (UK)

> **Read this document first** for the new Qullamaggie-inspired monthly/3-month momentum workflow. It describes the code committed to GitHub `main`, what the user actually verified in Discord, and which parts still need real broker testing. The older sections of [AI_SESSION_HANDOFF.md](AI_SESSION_HANDOFF.md), [README.md](README.md), and [ASJR operational history](../ASJR_Analyst/OPERATIONAL_HANDOFF.md) describe earlier stages and must not override this current snapshot.

### 1. Operator decisions (locked)

- **User interface is Discord only** while on the phone. Supply `!gitpull` and `!runpy` commands; do not make them use SSH, install another Discord bot, or give arbitrary VPS command execution.
- The user wants **two independent on-demand reports**: `1-MONTH MOMENTUM` and `3-MONTH MOMENTUM`, each ending with a **comma-separated watchlist** that can be copied. The combined `--momentum` command also remains available.
- Discover more US stocks using **seven native IBKR scanner categories**, but keep the new broker call **on demand**, separate from Chakra's existing automatic four-code/5-minute pipeline. Never imply the seven codes are already part of scheduled Chakra runs.
- No changes to `/root/trading/utils/trading_sudarsan_chakra.py`. In particular, do not run optional installers that patch that external launcher. The live Chakra hook remains:
  ```python
  result = tp.run_asjr_manual_pipeline(
      app=app, trade_date=None, gapup_df=None,
      fetch_gapup_from_app=True, include_sector=True, git_submit=True,
  )
  ```
- Protect regular IBKR imports, locked Reversal and other existing production functionality. No trading orders, new schedules, automatic Discord watchlist alerts, or RVOL changes are in scope.
- This is **momentum discovery, not a trade-entry signal, an earnings/catalyst verifier, or a fundamentals-quality screen**. Penny stocks and weak-fundamental companies should not be recommended for trading merely because the price/volume filter passed.

### 2. Discord operator runbook (in this order)

**Step A — Bring GitHub code to VPS** (only if a new commit needs pulling):
```text
!gitpull
```
If Git reports local tracked modifications, do **not** reset, stash, or overwrite live DataLake data; diagnose Git synchronisation first.

**Step B — On-demand fresh IBKR seven-category discovery:**
```text
!runpy RudraScanner/scan_now\.py --ibkr-7
```
This makes a **new short-lived read-only** localhost API connection to the existing IBKR Gateway and queries seven categories. It is **not** the normal four-code saved-data reader. Look for `SNAPSHOT | SAVED`, `UNIQUE DISCOVERED`, and per-code `DONE` / `TIMEOUT` / `API ERROR` / `NOT ADVERTISED`.

**Code-based IBKR results (new individual scan):** List allowed codes without an IBKR call:
```text
!runpy RudraScanner/scan_now\.py --ibkr-codes
```
Run any of the seven codes individually and display its direct IBKR-ranked list (up to 50 symbols):
```text
!runpy RudraScanner/scan_now\.py --ibkr-code HIGH_LAST_VS_EMA50
```
Replace the value with an exact code name from section 4, such as `HIGH_VS_13W_HL` or `HOT_BY_VOLUME`. Only the seven allowlisted codes are accepted. A single-code call is a short-lived read-only IBKR API connection. Its result is **native IBKR rank**, **not** the Yahoo 1M/3M momentum filter. The full comma-separated symbol list is printed at the end; individual code calls **do not overwrite** the seven-code shared cache. Use `--ibkr-7` to refresh the shared discovery universe.

**Step C — Return just the monthly report:**
```text
!runpy RudraScanner/scan_now\.py --momentum-1m
```

**Step D — Return just the 3-month report:**
```text
!runpy RudraScanner/scan_now\.py --momentum-3m
```

**Optional combined report:**
```text
!runpy RudraScanner/scan_now\.py --momentum
```
The combined report prints both Top 15 rankings and three comma-separated lines (monthly, 3-month, unique union), though long Discord outputs may be clipped by the bot.

**Existing commands, not replaced:**
```text
!runpy RudraScanner/scan_now\.py --ibkr-raw
!runpy RudraScanner/scan_now\.py --top
!runSCommand logs all 5
!runSCommand version
```
`--ibkr-raw` reads the saved four-code Chakra scanner; `--top` reads its prepared SMB Top 5. Neither launches the new seven-code request. Keep normal reporting independent. Do **not** call the new `RudraScanner/ibkr_seven_scanner.py` or `momentum_movers.py` by direct `!runpy`: the Discord bot's script allowlist blocks new file paths; their approved entrypoint is `scan_now\.py`.

### 3. Architecture and data provenance

```text
Existing Chakra ~5-minute scanner: 4 native IBKR codes
   -> dated ASJR DataLake CSVs -> base symbol universe
               |
               +--- on-demand IBKR seven-code discovery
                    (distinct API client; 3-code batches; max 50/code)
                    -> RudraScanner/state/ibkr_seven_latest.json
                    (separate local cache, NOT ASJR DataLake)
               |
               v
  Union of base ASJR symbols + CURRENT-DAY cached seven-code symbols
               |
               v
  Yahoo Finance yfinance six-month adjusted 1-D prices / daily volume
               |
               +-> 21-session % return -> independent 1-month Top 15
               +-> 63-session % return -> independent 3-month Top 15
               +-> comma-separated 1M, 3M and (combined view) unique union
```

**Existing ASJR symbols** are read by `RudraScanner/momentum_movers.py::tickers_from_datalake` from the newest dated `ASJR_Analyst/DataLake/YYYY-MM-DD` folder with suitable CSV data. Candidate files/columns: `raw/ibkr_gapup.csv:ticker`, `config/fixed_watchlist.csv:ticker`, `processed/ticker_summary.csv:Ticker`. It is **not** an all-US listed-symbol feed. The on-demand seven-code results can extend it substantially.

**Seven-code result store:** `RudraScanner/state/ibkr_seven_latest.json`. Written atomically after at least one scan has `DONE` plus symbols, with UTC collection time, ET session date, each code's status, per-code symbols and deduplicated ticker union. This is a **runtime cache**, not part of the existing five-minute DataLake import; do not assume it is shared across VPS/GitHub environments. The momentum scripts read this cache only when the date **matches the DataLake date** and the cache is no more than **24 hours old**. Otherwise they fall back silently only in the sense of continuing with the ASJR list, but the report prints `IBKR SNAPSHOT | UNAVAILABLE OR STALE`.

**Important stale-cache caveat:** a failed later `--ibkr-7` run does **not** delete an earlier same-day cache. Therefore a subsequent momentum call can still use that earlier cache while it remains within the same-day/24-hour rule. Always check the direct report's `SNAPSHOT` status and collection time before calling it newly refreshed.

**Price history:** independent `yfinance.download(period="6mo", interval="1d", auto_adjust=True)`, up to 35 symbols per batch; minimum 65 usable daily closing observations. Intraday `yfinance` current-day data can change between successive runs; never present these prices as verified live IBKR quotes. Data errors or partial Yahoo batches reduce the eligible count.

### 4. Seven-code IBKR scanner contract

| Code | Discovery meaning | Implementation |
| --- | --- | --- |
| `TOP_PERC_GAIN` | Current percentage gainers | Already used by scheduled 4-code scanner |
| `TOP_PERC_LOSE` | Current percentage losers | Already used by scheduled 4-code scanner |
| `HOT_BY_VOLUME` | Unusually active volume | Already used by scheduled 4-code scanner |
| `MOST_ACTIVE` | Most actively traded stocks | Already used by scheduled 4-code scanner |
| `HIGH_VS_13W_HL` | Strength relative to 13-week high/low | New on-demand category |
| `HIGH_VS_52W_HL` | Strength relative to 52-week high/low | New on-demand category |
| `HIGH_LAST_VS_EMA50` | Price strength relative to EMA50 | New on-demand category |

- Module: `RudraScanner/ibkr_seven_scanner.py::run_ibkr_seven`; invoked only by `scan_now.py --ibkr-7`.
- IBKR Gateway address `127.0.0.1:4002`, **API client ID 684** (distinct from older `ibkr_direct.py` client 682); `EClient/EWrapper` short-lived thread. This is **not** the existing Chakra-connected client. Two simultaneous TWS/Gateway sessions from different IPs have caused real broker failures in the past.
- On-demand scanner queries `reqScannerParameters` (3-second wait) and tests subscriptions. Set `STK`, `STK.US.MAJOR`, `stockTypeFilter=CORP`, `abovePrice=10`, 50 rows maximum per code; it **does not apply a broker-side minimum average volume**. Subsequent momentum ranking applies the final 20-day volume filter.
- Scans are run in **three sequential batches** (3 + 3 + 1 requests) with an **8-second per-batch deadline**, plus startup/parameter waits. This reduces—not eliminates—competition with Chakra and risks timeout in the existing Discord `!runpy` runner; do not claim performance until the user posts the live result. IBKR active scanner limit and supported codes are broker-dependent.
- Status handling: `DONE` means the scan ended without listed scanner error codes, `TIMEOUT` means it did not finish in the batch deadline, `API ERROR` means a known scanner error, `NOT ADVERTISED` means absent from XML parameters. `DONE` is **not** proof that all 50 rows were returned; counts are explicit in output.
- Display: five names per code in direct summary; save up to 50 per successfully completed code; show up to 30 unique symbols in Discord preview. Only the successfully completed codes' membership is cached. This **does not scan every US stock**—it samples the top ranks in seven scanner categories.
- No IBKR 1M/3M performance statistic is fetched by the seven-code call. Percentage-return ranking always comes from subsequent Yahoo daily data. No historical IBKR 5m import is initiated here.
- **No broker orders**: code uses scanner requests/cancel/disconnect only. It does not call `placeOrder` or `run_asjr_manual_pipeline`.

### 4A. Critical operator distinction: direct vs refined

- **Direct code-based list:** `--ibkr-code CODE` shows the selected broker scanner's native ranking and applies its own US stock / minimum $10 broker request configuration. It is **not** filtered again by Yahoo return %, 20-day volume, EMA or business quality. One code = one ranked watchlist, with up to 50 ticker symbols.
- **Refined period-based list:** `--momentum-1m` / `--momentum-3m` fetch Yahoo adjusted daily OHLC/volume for the union of saved ASJR symbols and recently discovered 7-code IBKR symbols. It **does** apply at least $10 latest daily price, 20-day mean volume >=1 million, at least 65 daily rows, the BEAT/ONDS exclusion, then sorts by 21-/63-session return respectively. Each emits a Top 15 watchlist.
- **No direct-to-refined implicit refresh:** calling a single `--ibkr-code` does not replace the previously saved 7-code universe. To add *new* IBKR symbols to refined rankings, run `--ibkr-7` first. Otherwise refined lists use the saved ASJR base plus any already-valid full-discovery cache.
- *Do not interpret* `HIGH_LAST_VS_EMA50` as guaranteed price > EMA50 until IBKR confirms exactly how it ranks; the broker code is authoritative, and tests of our code are not proof that a Gateway supports that scanner.

### 5. Momentum ranking rules (V1, as implemented)

| Rule | Exact behavior |
| --- | --- |
| 1-month ranking | `100 * (latest adjusted close / adjusted close 21 completed trading intervals earlier - 1)`; code uses `close.iloc[-22]` |
| 3-month ranking | `100 * (latest adjusted close / adjusted close 63 completed trading intervals earlier - 1)`; code uses `close.iloc[-64]` |
| Reference high | Last 63 daily **closing** values; report's `3M-HIGH%` measures below that close, **not intraday 13-week high** |
| Price floor | Latest daily adjusted close at least **$10** |
| Volume floor | 20-day mean reported Yahoo daily volume at least **1,000,000 shares/day** |
| History required | At least 65 valid closing rows |
| Excluded symbols | `BEAT` and `ONDS` |
| Number shown | Top 15 each by default; alphabetical tie order is not a user-specified strategy rule |
| Output | Compact ticker, percentage gain and daily price; own comma-separated watchlist at end |
| Quality & entries | No fundamental screening, no earnings/catalyst ranking, no sweep/CHOCH/flag detection and no automatic trade |

Potentially extended or low-quality names can rank highly. Example: a +90% three-month mover currently 40% below its recent high is **not** a confirmed Qullamaggie breakout. Rank by timeframe, then review trend/base, tightness, volume contraction, market/sector alignment, and business quality separately.

### 6. Observed versus pending status (never conflate)

**User-confirmed live Discord, 2026-10-15 ~19:03 UK, BEFORE seven-code extension:**
- `!runpy RudraScanner/scan_now\.py --momentum` returned `RUNPY | SUCCESS | Exit: 0`.
- Universe **118**, eligible **101**, both Top 15 rankings, 1-month/3-month comma-separated watchlists plus unique combined list.
- First examples from that sample: 1M `ARHS +42.3%`, `P +34.1%`, `PENG +24.0%`; 3M `QMCO +93.8%`, `P +88.7%`, `FRO +55.4%`. Historical reported daily price snapshots only, **not live stock-price endorsements**.
- Earlier manual attempt to run `momentum_movers.py` directly produced `RUNPY DENIED Script not allowed`; `scan_now.py --momentum` initially failed due to inner argument re-parsing, then was corrected and returned success. Always use the approved `scan_now.py` entrypoint.

**GitHub code committed, live verification still missing as of handoff:**
- Separate `--momentum-1m` / `--momentum-3m` flags added; no user-pasted distinct-command success yet.
- Seven-code `--ibkr-7` scanner, API parameter discovery, status reporting and atomic cache added; **no user-pasted live Gateway result yet** for any seven-code category.
- Auto-enrichment of monthly/quarterly universe by same-day seven-code cache committed; no user result yet proving added universe count above the 118 base.
- GitHub file contents were re-fetched for wiring; **no VPS unit test or live runtime confirmation** of the seven-code path. Do not say all seven worked merely because the code exists.
- Ordinary Chakra scanner historically functioned with four codes. The seven-code add-on is not part of scheduled five-minute scan, SMB Top 5 computation, bot restart, or the DataLake writer.

### 7. Troubleshooting / failure modes

| Symptom | Meaning / next action |
| --- | --- |
| `RUNPY DENIED | Script not allowed` | Use `!runpy RudraScanner/scan_now\.py --ibkr-7` or `--momentum-1m`; never call the separate Python file directly via Discord |
| `unrecognized arguments` | Old Git pull or nested parser mismatch; verify `!gitpull`, latest `!runSCommand version`, and exact flag |
| `GATEWAY NOT READY` | Check existing IBKR Gateway/login/session; avoid launching competing desktop TWS/Notebook client |
| `NOT ADVERTISED` / `API ERROR` on one code | That code may not be available for this IBKR API/version/location. Keep other working codes; inspect status; do not invent fallback rows |
| `TIMEOUT` | Scanner did not finish within 8 s batch window; it cannot be called verified merely from partial rows |
| `SNAPSHOT | NOT SAVED` | No successful nonempty code result, or file write error. Do not assume fresh seven-code enrichment |
| `IBKR SNAPSHOT | UNAVAILABLE OR STALE` | Monthly/quarterly result uses only saved ASJR DataLake symbols |
| `NO ELIGIBLE DATA` | CSV universe/market data missing or price, volume, history gates excluded all symbols |
| `RUNPY | SUCCESS | Exit: 0` on momentum | Only confirms ranking produced output, **not live quotes, IBKR API health or trade readiness** |
| Output clipped in Discord | Run monthly and 3-month commands separately; full lists should be at each report's end. Some bot message limits can still trim very large output |

Never recover with destructive Git resets, new bot processes, changes to external Chakra launcher, or fabricated Yahoo/IBKR signals. The GitHub code and runtime cache are separate. Subsequent manual scans need the broker client-684 connection, which could contend with the existing pipeline.

**Offline tests added 2026-10-15:** `RudraScanner/tests/test_ibkr_seven_scanner.py` checks seven allowlisted choices, simulated per-code 50-row broker callbacks, full seven-code cache, single-code cache immutability, unknown code rejection and `--ibkr-codes` output. Included in the existing `scan_now.py --self-test` suite. These tests still require VPS execution; passing mocked tests cannot prove live IBKR Gateway accepts all seven scan codes.

### 8. Next-agent acceptance checklist (no assumptions)

1. Confirm latest GitHub code reaches VPS via successful `!gitpull`; if refused due live tracked changes, do not force pull.
2. Run **one** `!runpy RudraScanner/scan_now\.py --ibkr-7`. Review `CODE PARAMETERS`, all seven code status/count lines, API errors, `SNAPSHOT | SAVED`, deduplicated symbol count; label code support by observed response. Observe elapsed time and any effect on regular Chakra imports.
3. Run `--momentum-1m` and `--momentum-3m` separately. Confirm both output their own comma-separated WATCHLIST and report how many **new IBKR seven-code tickers** were added to the base universe. Confirm daily quote date/freshness.
4. If any part fails, fix **only** the on-demand scanner/entrypoint after evidence, never `trading_sudarsan_chakra.py`. Verify normal four-code and 5-minute imports remained healthy.
5. Update this doc and the AI/operational handoffs with the actual Discord result and the code commit used. Only after proven correctness may future automatic discovery be considered on explicit user approval.

### 9. File map and change log

| File | Responsibility |
| --- | --- |
| `RudraScanner/scan_now.py` | Stable Discord allowlisted entrypoint and flags |
| `RudraScanner/ibkr_seven_scanner.py` | Seven-code read-only IBKR API + JSON snapshot |
| `RudraScanner/momentum_movers.py` | ASJR+snapshot ticker universe, Yahoo momentum return calculations, ranking and watchlist |
| `RudraScanner/state/ibkr_seven_latest.json` | Generated local on-demand symbol snapshot; optional/ephemeral |
| `RudraScanner/top_in_play.py` | Legacy four-code raw and SMB Top 5 reports |
| `RudraScanner/IBKR_SEVEN_CODE_DISCOVERY.md` | **This authoritative operating guide** |
| `RudraScanner/AI_SESSION_HANDOFF.md` | General AI session handoff (new top link points here) |
| `ASJR_Analyst/OPERATIONAL_HANDOFF.md` | Whole-system operational history (new top summary points here) |

GitHub implementation commits (2026-10-15): initial momentum page `f3ed2db6`; Discord-approved entrypoint and argument fixes through `5c94dd31`; comma-separated watchlists `0c7e6ff3`; distinct 1M/3M flags `a64bf7e7`; seven-code module `ba40bb1d`; on-demand flag `66aee790`; cache enrichment `e7a5a1c`; final seven-code output `d9747353`. **These hashes prove GitHub updates, not broker functionality.**

Source reference: [IBKR TWS API Market Scanner](https://www.interactivebrokers.com/docs/tws-api/doc/market-scanner/introduction).
