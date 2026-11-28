# Live scan history — permanent research data

Collector: [live_scan_collector.py](../../live_scan_collector.py). Uses existing Chakra five-minute DDB cycle, same connected IBKR app, no orders or new scheduler. Existing historical files in data/ remain untouched. Permanent retention; manual deletion only.

Each session date (ET) contains one immutable folder per completed 5-minute interval, e.g. 2026-11-30/0935_ET/. Stable files inside:
- sector_5m.csv: 11 sector ETFs + SPY, only exact completed RTH 5m target OHLCV.
- ibkr_scan_results.csv: native rank, ticker, conId, exchange, actual request/response time, scan code, status. No stock OHLCV. No cross-code deduplication or extra filters.
- scan_rounds.jsonl: one record per scan/sector, parameters, errors, missing, empty or timeout results.
- errors.log: timestamped issues; also written when collection is partial or fails.
- scanner_parameters.xml: actual live IBKR catalogue once per session when received.
Eight scan codes: MOST_ACTIVE, HOT_BY_VOLUME, TOP_PERC_GAIN, TOP_PERC_LOSE, HIGH_OPEN_GAP, LOW_OPEN_GAP, TOP_OPEN_PERC_GAIN, TOP_OPEN_PERC_LOSE. Query live catalogue; not-advertised codes are logged; unknown catalogue is labelled and subscriptions tested. Up to 50 native results per code, sequential batches up to three. Sector requests are bounded batches of four.
UK and UTC times retained; exchange session date and interval names ET. Regular session 09:35–16:00 ET, early-close adjusted, holidays skipped (NYSE published 2026/27 calendar; update before 2028). Final scan may occur after close and is flagged. DDB calculation runs first; collection can be late/skipped if DDB uses the interval budget, with exact timing recorded. No claim of exact five-minute stock returns from opening/day scans.

Local durable spool: /root/trading/ASJR_research_logs/hot_sector/live_scan_history/rounds/. Existing production checkout is not modified by publication. Each cycle immediately attempts a fast-forward-only Git push via separate bare repository; immutable files never replaced, no force push. A failed push remains queued with separate publish_errors/ records for the next successful push. Network outage cannot be reported on GitHub until connectivity is restored. No automatic deletion of spool or remote archive. Existing DDB alert return/format is preserved, but synchronous collection/publishing adds bounded latency. Verify actual callback compatibility, timing, Git credentials, and successful collection on VPS before relying on the data.
