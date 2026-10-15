# RudraScanner: IBKR seven-code on-demand discovery

## Purpose
Discover U.S. stock tickers across seven IBKR Market Scanner categories without modifying the scheduled Chakra job, its external VPS integration hook, existing four-code IBKR scanner, or order management.

## Seven requested IBKR scanner codes

1. `TOP_PERC_GAIN` — today's percentage gainers
2. `TOP_PERC_LOSE` — today's percentage losers
3. `HOT_BY_VOLUME` — volume activity
4. `MOST_ACTIVE` — actively traded stocks
5. `HIGH_VS_13W_HL` — strength near 13-week highs
6. `HIGH_VS_52W_HL` — strength near 52-week highs
7. `HIGH_LAST_VS_EMA50` — strength versus the 50-day EMA

These are **discovery categories**, not direct 1-month or 3-month return scanners. Support depends on IBKR Gateway's advertised parameters and the API/location. Unsupported codes and API errors are reported clearly.

## Discord usage (on-demand only)
Pull first:

```
!gitpull
```

Fetch all seven IBKR categories via a short-lived independent Gateway connection:

```
!runpy RudraScanner/scan_now\.py --ibkr-7
```

Then rank the expanded on-demand universe from Yahoo Finance adjusted daily closes:

```
!runpy RudraScanner/scan_now\.py --momentum-1m
!runpy RudraScanner/scan_now\.py --momentum-3m
```

The previous combined command `!runpy RudraScanner/scan_now\.py --momentum` still works.

## Data sources & flow
- IBKR on-demand: read-only `reqScannerParameters` / `reqScannerSubscription` / `cancelScannerSubscription`. IP localhost, Gateway port 4002, client ID 684. Scan in groups of three; IBKR's limit is 10 active API scanners per Gateway, and Chakra has its own four scans.
- Max 50 ranked tickers per code. The full results from successful scans (deduplicated) are atomically cached in `RudraScanner/state/ibkr_seven_latest.json`; only a 30-symbol preview is displayed for Discord character limits.
- Cache is accepted by the momentum scanner only on the matching U.S. market date and when at most 24 hours old; otherwise its universe remains the existing ASJR DataLake tickers.
- One- and three-month percentage returns are calculated from Yahoo Finance adjusted daily close over 21 and 63 trading sessions. Basic final eligibility is $10 minimum share price and 20-session average daily volume of at least 1 million shares; BEAT and ONDS excluded.
- Each momentum output prints its own full Top 15 comma-separated watchlist.

## Safety & limitations
- Running the command explicitly makes a **separate short-lived IBKR API connection** and may fail if the Gateway is disconnected or the active TWS session is using another IP. No connection is made by the Yahoo-only momentum calls.
- No orders, no scheduled job additions, no discord alerts, no writes to Chakra's DataLake.
- Data are derived from current IBKR scanner output plus potentially delayed Yahoo daily candles; this is not live price/entry execution and no fundamental-quality screen.
- Never edit `/root/trading/utils/trading_sudarsan_chakra.py` for this feature.
- This feature requires a first live Discord test for code support and timings. It has not been verified against the user's Gateway yet.

## Reference
IBKR TWS API market scanner documentation: https://www.interactivebrokers.com/docs/tws-api/doc/market-scanner/introduction
