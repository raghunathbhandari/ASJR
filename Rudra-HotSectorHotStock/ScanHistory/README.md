# Rudra-HotSectorHotStock — permanent scan history

Research collection plan, 2026-11-28 UK. No collector implementation or VPS deployment yet.

## Retention
Preserve this entire tree indefinitely, until explicitly authorised manual deletion. It is outside ASJR_Analyst/DataLake and excluded from automatic cleanup. Use stable filenames, never replace past scanner snapshots with later results.

## Proposed collection
Reuse existing Chakra 5-minute schedule and connected IBKR app, independently of DDB V2 alerts. No second gateway or new scheduler. US regular trading sessions only initially, respecting holidays/early closes; first completed interval 09:35 ET. Keep timestamps in UTC and UK, and the ET session date. Bound scan batches and respect IBKR pacing; preserve DDB priority.

Hot sector: record completed 5-minute OHLCV for XLK,XLC,XLY,XLF,XLI,XLV,XLE,XLU,XLP,XLB,XLRE and SPY (benchmark). Rank each sector from actual bar data, not end-of-day data. Log missing/delayed bars. Historical repair must be labelled.

Hot stocks: preserve up to 50 exact native ranked ticker results per scan code per interval, without deduplicating across codes or times. Research scope: US stock momentum, price action, volume/activity and technical strength only. Exclude fundamental, dividend, earnings-event, options and bonds scans. Start with the existing seven-code candidates and validate the extended candidate list below against live IBKR reqScannerParameters and actual subscriptions; do not treat an advertised code as verified. Check sector/industry filtering support and whether any direct sector ranking code is advertised and actually accepted. No stock OHLCV collection now; download later as needed.

## Layout
Each ET trading date has a directory with stable names:
- sector_5m.csv: session date, ticker, bar start/end UTC, collected UTC and UK, OHLCV, status/source.
- ibkr_scan_results.csv: session date, scheduled interval, actual scan timestamp UTC and UK, scan code, native rank, ticker, optional conId/exchange.
- scan_rounds.jsonl: scan code, scheduled interval, request/response timestamps, filters, row count, completion/error/timeout status; log empty rounds too.

Append durably; prevent duplicate reprocessing of the same round without discarding actual scans. Never fabricate missing scanner snapshots or treat later results as point-in-time evidence. Publish using safe isolated Git commits (proposed end-of-session batch with retries and local durable retention), not a force push. No orders, no stock OHLCV, no strategy changes, no new Discord trading alerts. Validate one real market session before claiming successful collection.

## Candidate scan-code catalogue (2026-11-28)

| Group | Candidate scan codes |
| --- | --- |
| Momentum / open | TOP_PERC_GAIN, TOP_PERC_LOSE, TOP_OPEN_PERC_GAIN, TOP_OPEN_PERC_LOSE, HIGH_OPEN_GAP, LOW_OPEN_GAP |
| Price activity | HOT_BY_PRICE, HOT_BY_PRICE_RANGE, TOP_PRICE_RANGE |
| Volume / trade activity | HOT_BY_VOLUME, MOST_ACTIVE, MOST_ACTIVE_USD, TOP_VOLUME_RATE, TOP_TRADE_RATE, TOP_TRADE_COUNT |
| Technical strength / weakness | HIGH_VS_13W_HL, LOW_VS_13W_HL, HIGH_VS_26W_HL, LOW_VS_26W_HL, HIGH_VS_52W_HL, LOW_VS_52W_HL, HIGH_LAST_VS_EMA50, LOW_LAST_VS_EMA50 |

These 23 names are candidates, not verified live entitlements. Preserve the exact supported scan codes and parameter XML snapshot/version, request universe, filters, timestamps, native ranks and response state. Do not silently drop raw rows, even if a ticker is excluded from an actual trading watchlist. No post-scan fundamental or sector filtering; research can apply these later. Existing four-code legacy scanner had successful historical runs; other candidates require individual live acceptance (EMA50 high had a historical successful result with warnings). Do not add unsupported scans to recurring collection.

Target each regular-session completed 5-minute interval, beginning 09:35 ET through the final session interval (early close adjusted). If the final live scan would be after the close, label its actual timing rather than treating it as a pre-close snapshot. Collect all validated codes per interval in bounded batches (maximum 10 active API scans across clients; start with batches of 3); if the collection exceeds the time budget, record missing/late codes and protect the existing DDB alert path. Never relabel a later scan as an earlier snapshot. Initial research horizon: several months, no automatic deletion or stop date imposed. No collector code or VPS activation in this plan update.
