# Rudra-HotSectorHotStock — permanent scan history

Research collection plan, 2026-11-28 UK. No collector implementation or VPS deployment yet.

## Retention
Preserve this entire tree indefinitely, until explicitly authorised manual deletion. It is outside ASJR_Analyst/DataLake and excluded from automatic cleanup. Use stable filenames, never replace past scanner snapshots with later results.

## Proposed collection
Reuse existing Chakra 5-minute schedule and connected IBKR app, independently of DDB V2 alerts. No second gateway or new scheduler. US regular trading sessions only initially, respecting holidays/early closes; first completed interval 09:35 ET. Keep timestamps in UTC and UK, and the ET session date. Bound scan batches and respect IBKR pacing; preserve DDB priority.

Hot sector: record completed 5-minute OHLCV for XLK,XLC,XLY,XLF,XLI,XLV,XLE,XLU,XLP,XLB,XLRE and SPY (benchmark). Rank each sector from actual bar data, not end-of-day data. Log missing/delayed bars. Historical repair must be labelled.

Hot stocks: preserve up to 50 exact native ranked ticker results per scan code per interval, without deduplicating across codes or times. Research scope narrowed by user on 2026-11-28: most active, high volume, gainers/losers, opening gaps and opening momentum, both strong and weak directions. Only the eight selected codes below are candidates for the recurring collector. Validate against live IBKR reqScannerParameters and actual subscriptions; do not treat an advertised code as verified. Check sector/industry filtering support and whether any direct sector ranking code is advertised and actually accepted. No stock OHLCV collection now; download later as needed.

## Layout
Each ET trading date has a directory with stable names:
- sector_5m.csv: session date, ticker, bar start/end UTC, collected UTC and UK, OHLCV, status/source.
- ibkr_scan_results.csv: session date, scheduled interval, actual scan timestamp UTC and UK, scan code, native rank, ticker, optional conId/exchange.
- scan_rounds.jsonl: scan code, scheduled interval, request/response timestamps, filters, row count, completion/error/timeout status; log empty rounds too.

Append durably; prevent duplicate reprocessing of the same round without discarding actual scans. Never fabricate missing scanner snapshots or treat later results as point-in-time evidence. Publish using safe isolated Git commits (proposed end-of-session batch with retries and local durable retention), not a force push. No orders, no stock OHLCV, no strategy changes, no new Discord trading alerts. Validate one real market session before claiming successful collection.

## Selected scan-code catalogue (2026-11-28)

| Category | Strong | Weak |
| --- | --- | --- |
| Most active | MOST_ACTIVE (direction neutral) | Same scan |
| High relative volume | HOT_BY_VOLUME (direction neutral) | Same scan |
| Day momentum | TOP_PERC_GAIN | TOP_PERC_LOSE |
| Opening gap | HIGH_OPEN_GAP | LOW_OPEN_GAP |
| Since-open momentum | TOP_OPEN_PERC_GAIN | TOP_OPEN_PERC_LOSE |

Eight distinct codes only; maximum 400 ranked rows per interval. The day-change scan measures movement relative to previous close, the opening-gap scan measures open relative to previous close, and the since-open scan measures movement relative to today's open; the last is not a rolling five-minute return. Most active and hot volume do not indicate direction. No EMA, multi-week technical, other price/activity, fundamentals or options scans. Existing four-code legacy scanner had successful historical runs; the four additional opening codes require live acceptance. Preserve exact supported codes, parameter XML snapshot/version, request universe, filters, timestamps, native ranks and response state. Do not silently drop raw rows or deduplicate across codes or intervals. No post-scan fundamental or sector filtering; research can apply these later. Do not add unsupported scans to recurring collection.

Target each regular-session completed 5-minute interval, beginning 09:35 ET through the final session interval (early close adjusted). If the final live scan would be after the close, label its actual timing rather than treating it as a pre-close snapshot. Collect all validated codes per interval in bounded batches (maximum 10 active API scans across clients; start with batches of 3); if the collection exceeds the time budget, record missing/late codes and protect the existing DDB alert path. Never relabel a later scan as an earlier snapshot. Initial research horizon: several months, no automatic deletion or stop date imposed. No collector code or VPS activation in this plan update.
