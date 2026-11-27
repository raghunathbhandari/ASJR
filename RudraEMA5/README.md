# RudraEMA5 — COHR 5-minute research

**Status:** Data acquisition requested; trading rules pending user instructions. Do not run a backtest or infer buy/sell rules yet.

## Dataset request
- Symbol: COHR (US stock, SMART/USD)
- Source: IBKR Gateway via the existing ASJR ResearchBridge `ibkr_range_download` operation
- Bar interval: 5 minutes, TRADES, `useRTH=False` (available premarket/RTH/after-hours)
- Requested period: 2026-11-01 through 2026-11-27 at 18:00 Europe/London (UTC, UK winter time)
- Download job requests whole inclusive dates because the existing bridge only supports date boundaries; **filter any bars later than 2026-11-27 18:00 UTC before backtesting**.
- Keep raw timestamp fields in UTC; display logs in UK time.
- Source data and result should be inspected for coverage, duplicates, missing intervals, candle integrity and actual first/last bar; do not fill market closures.

## Backtest rules
**BUY:** To be provided by user.

**SELL/exit/SL/TP:** To be provided by user.

No automated trading or order submission. Preserve source data unchanged.

## Acquisition
Bridge request: `RudraScanner/ResearchBridge/requests/research-1795805412345.json`
Expected raw export (if successful): `three_candle/data/ibkr_bridge/research-1795805412345/` (verify exact returned path and manifest).
