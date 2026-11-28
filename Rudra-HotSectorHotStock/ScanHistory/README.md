# Rudra-HotSectorHotStock — permanent scan history

Research collection plan, 2026-11-28 UK. No collector implementation or VPS deployment yet.

## Retention
Preserve this entire tree indefinitely, until explicitly authorised manual deletion. It is outside ASJR_Analyst/DataLake and excluded from automatic cleanup. Use stable filenames, never replace past scanner snapshots with later results.

## Proposed collection
Reuse existing Chakra 5-minute schedule and connected IBKR app, independently of DDB V2 alerts. No second gateway or new scheduler. US regular trading sessions only initially, respecting holidays/early closes; first completed interval 09:35 ET. Keep timestamps in UTC and UK, and the ET session date. Bound scan batches and respect IBKR pacing; preserve DDB priority.

Hot sector: record completed 5-minute OHLCV for XLK,XLC,XLY,XLF,XLI,XLV,XLE,XLU,XLP,XLB,XLRE and SPY (benchmark). Rank each sector from actual bar data, not end-of-day data. Log missing/delayed bars. Historical repair must be labelled.

Hot stocks: preserve up to 50 exact native ranked ticker results per scan code per interval, without deduplicating across codes or times. Initial candidate codes: TOP_PERC_GAIN, TOP_PERC_LOSE, HOT_BY_VOLUME, MOST_ACTIVE, HIGH_VS_13W_HL, HIGH_VS_52W_HL, HIGH_LAST_VS_EMA50. Final scope pending user confirmation and live IBKR reqScannerParameters catalogue. Check sector/industry filtering support and whether any direct sector ranking code is advertised and actually accepted. No stock OHLCV collection now; download later as needed.

## Layout
Each ET trading date has a directory with stable names:
- sector_5m.csv: session date, ticker, bar start/end UTC, collected UTC and UK, OHLCV, status/source.
- ibkr_scan_results.csv: session date, scheduled interval, actual scan timestamp UTC and UK, scan code, native rank, ticker, optional conId/exchange.
- scan_rounds.jsonl: scan code, scheduled interval, request/response timestamps, filters, row count, completion/error/timeout status; log empty rounds too.

Append durably; prevent duplicate reprocessing of the same round without discarding actual scans. Never fabricate missing scanner snapshots or treat later results as point-in-time evidence. Publish using safe isolated Git commits (proposed end-of-session batch with retries and local durable retention), not a force push. No orders, no stock OHLCV, no strategy changes, no new Discord trading alerts. Validate one real market session before claiming successful collection.
