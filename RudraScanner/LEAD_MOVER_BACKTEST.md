# RudraScanner — Research Backtest: What Happened BEFORE a Strong Move?
**Updated 2026-10-16 | on-demand study, not production trade signals**

## User objective
Find **high-probability candidates early**, rather than adding more real-time data import to Chakra. This study reconstructs historical daily-bar conditions and measures what would have happened afterward. No scheduled scans, IBKR API requests, DataLake mutation, Discord alert, trading order, or changes to `/root/trading/utils/trading_sudarsan_chakra.py`.

## One Discord call
First update the VPS repository:
```text
!gitpull
```
Run offline regression tests (no Yahoo or IBKR network):
```text
!runpy RudraScanner/scan_now\.py --self-test
```
Run the event study (read-only daily Yahoo requests):
```text
!runpy RudraScanner/scan_now\.py --mover-study
```
**Runtime warning:** fetching two years of Yahoo daily history for the latest candidate list can take time. An external Discord `!runpy` timeout is possible and does not imply stock-screening conclusions. In that case report the exact output and evaluate a staged cached/offline workflow separately; do not restart Chakra or make repeated competing broker calls.

## Data provenance and scope
- **Candidates**: current latest ASJR DataLake ticker universe, optionally extended by matching-date, <=24-hour-old IBKR 7-code on-demand ticker cache. Importantly, these are today's surviving candidates, **not point-in-time historical market constituents or historical IBKR scanner memberships**. Therefore selection and survivorship biases mean an apparently high historical hit rate is not a validated live edge.
- **Daily bars**: `yfinance.download`, two years of adjusted open/high/low/close/volume, requests batched by up to 35 symbols. The current ET session's partial bar is omitted entirely. A symbol needs >=252 clean daily records.
- **No live IBKR quote, no earnings/catalyst/fundamental/sector screening in V1**.
- Strategy and results use adjusted historical daily bars; prices are not reliable live intraday quotes.
- Data download stays read-only in memory (no new data import files).

## Test design (non-lookahead, long-only, exploratory)
All signals are calculated at **the close** of a historical daily bar. An entry, if simulated, happens at the **next daily OPEN**. Fixed research parameters, not an approved executable trading strategy:

- Take-profit target: **+10% relative to entry**.
- Stop-loss: **-5% relative to entry**.
- Maximum time: **20 trading sessions including entry day**.
- Exit model: if a future daily OPEN gaps through the stop or target, fill at that OPEN. Otherwise intraday LOW hitting stop is assumed to execute first; if both low/stop and high/target occur in a single day, **count the stop as first** (conservative treatment of unknown intraday order). Target then stop status has no fill/slippage guarantee in reality. Otherwise close at end of day 20. Trading fees, slippage and financing costs excluded.
- A **WIN** in the hit-rate column requires reaching the +10% target before -5% stop within the 20 sessions. Positive partial time exits are not counted as TARGET hits.
- Avoid repeated nearly identical adjacent events: each ticker/setup is on cooldown for **20 sessions** after the previous signal. `BASELINE` also samples a fixed 20-session cadence.
- Each ticker's latest **126 trading sessions** form a chronologically later TEST set; older data form TRAIN. A TRAIN signal whose 20-day outcome would cross into TEST is dropped. Last incomplete 20-day outcome window omitted. The same ticker appears in both datasets, so TRAIN/TEST are not independent stock-universe samples.
- We evaluate **four technical factor sets** plus baseline. This is an exploratory comparison, **not a backtest of the seven broker-native code rankings** (historical membership snapshots do not exist in current saved input).

## Exact condition definitions
Common selection gate on signal date: Yahoo adjusted daily price >=$10, trailing 20-session **mean daily volume >=1 million shares**. Exclude BEAT/ONDS. All calculations use only data at or before the signal bar.

| Study label | Conditions at close |
|---|---|
| `BASELINE` | Any eligible stock sampled each 20 sessions |
| `TREND` | 21-session return >=10%; 63-session return >=20%; close >=EMA20>EMA50; close within 10% of highest close in last 63 sessions |
| `HIGH_13W` | Close within 3% of highest 63-session close; 63-session return >=20%; EMA20>EMA50 |
| `TIGHT_BASE` | TREND plus last-10-session highest HIGH / lowest LOW minus one <=12%, and last-5-session average volume less than 80% of 20-session average |
| `BREAKOUT` | Close strictly exceeds the **previous 20 trading sessions' highest intraday HIGH** (excluding signal date); signal-day volume >=1.5 x last-20 mean; 63-session return >=20%; EMA20>EMA50 |

The `HIGH_13W` condition reconstructs a *daily-bar proxy* for 13-week highs; **it is not an audit of past IBKR `HIGH_VS_13W_HL` scan results**.

## Report interpretation
```text
RUDRA | MOVER STUDY | YYYY-MM-DD HH:MM UK
UNIVERSE | [N] | ASJR [date] + seven-code cache [N]
USABLE | [N] | LATEST COMPLETED DAILY [date]
TRAIN | +10% TARGET / -5% STOP / 20 DAYS
SETUP          N  HIT%   AVG P/L%
...
TEST | +10% TARGET / -5% STOP / 20 DAYS
SETUP          N  HIT%   AVG P/L%
...
RESEARCH CANDIDATES | last completed daily bars
TREND | [symbols...]
HIGH_13W | [symbols...]
TIGHT_BASE | [symbols...]
BREAKOUT | [symbols...]
CAUTION | Today's surviving universe; NOT historical IBKR code backtest
```
Results are **not yet computed or verified on the VPS** as of document creation. Beware small sample sizes, missing Yahoo symbols, correlated events across tickers, company splits, current-universe survivorship bias, and retrospective parameter/data-mining risks. Do not claim a positive expectancy unless TEST trades/sample sizes and stability justify it.

## Testing and acceptance
- New code: `RudraScanner/lead_mover_backtest.py`, accessed via existing Discord allowlisted `scan_now.py --mover-study`.
- New offline tests: `RudraScanner/tests/test_lead_mover_backtest.py`, included in `--self-test` (no actual IBKR or Yahoo network for unit tests); tests synthetic no-lookahead flags, next-session entry, gap-through-stop, simultaneous target-and-stop conservative resolution, and routing.
- **Committed, NOT live-executed by assistant**. Need user's `!gitpull`, offline result, and then first actual `--mover-study` output.
- First research review: inspect TEST sample count, target-before-stop hit rate, average P/L, consistency across setup families and individual stock dependence. If all setups disappoint, document it and do **not** retune blindly to manufacture >=60% wins.
- Before using an investment signal, add historical constituent coverage, corporate-action checks, out-of-universe controls, sector/QQQ/SPY-relative strength, dated catalysts, execution costs, realistic transaction constraints, out-of-sample forward monitoring and a longer time horizon.

## Existing system boundary
- The seven individual `--ibkr-code CODE` commands remain **raw current IBKR scan rankings**, not refined and not historical backtested.
- The separate `--momentum-1m` and `--momentum-3m` commands continue as Yahoo-based **refined** return rankings, not the event study.
- The event study is a separate research tool, without automatic alerts, data-import changes, Chakra startup, or external launcher edits.
