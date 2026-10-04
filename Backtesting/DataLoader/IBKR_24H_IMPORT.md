# SMART plus overnight historical import

The existing `--all-hours` flag requests SMART history with `useRTH=False`.
That is not proof that the separate overnight venue was included. MU's saved
2026-10-02 data had no 08:00 or 08:45 Europe/London bar.

IBKR documents overnight market-data routing using exchange `OVERNIGHT` and
the stock's primary listing exchange:
https://www.interactivebrokers.com/campus/ibkr-quant-news/api-overnight-trading/

Historical request fields are documented here:
https://www.interactivebrokers.com/docs/tws-api/doc/market-data-historical/historical-bars/requesting-historical-bars

The routing guidance does not guarantee one year of overnight historical
bars for every account/stock. A live request is necessary to verify that.

## First live check

From the repository root on the VPS:

```bash
/root/trading/venv_new/bin/python -u IBKR_import.py \
  --24h --tickers MU --interval 5m \
  --start 2026-10-02 --end 2026-10-02 \
  --client-id 71 --concurrency 1 --pacing-sleep 1
```

`--24h` sets `useRTH=False` for both requests. No additional `--all-hours`
flag is required. Both sources are freshly requested; old date-only cache
coverage cannot bypass the overnight request. It downloads OVERNIGHT first
so unsupported historical requests fail promptly. Returned request errors
are raised rather than reported as a successful empty import.

Confirm actual overnight rows and the printed UK 08:00/08:45 checks before
extending to a year with `--years 1 --end 2026-10-02` in place of `--start`.
Absence of an individual bar can mean no trades; the JSON report also lists
session row counts and timestamp gaps for the checked UK date. Never fill
missing historical trades with invented flat candles.

## Files and source handling

Merged OHLCV:
`Backtesting/BacktestData/IBKR/MarketData24h/5m/MU_5m.csv`

Coverage evidence:
`Backtesting/BacktestData/IBKR/MarketData24h/5m/MU_5m.coverage.json`

Raw sources are retained below that root's `sources/SMART` and
`sources/OVERNIGHT` directories.

SMART contributes 04:00-20:00 ET, OVERNIGHT contributes 20:00-04:00 ET.
Timestamps remain UTC; session selection accounts for America/New_York DST.
One source per instant is selected: volumes are not summed and bars are
not fabricated. Existing dates outside the requested interval in the merged
24H cache are retained; the requested period is replaced by real new data.

RTH/extended-hours files under `MarketData` and live Chakra files remain
unchanged. Strategies must explicitly select the new cache root after
validation; they do not silently switch feeds. The script does not push CSVs
to Git or restart the bot.

If a source returns no bars, has no overnight-session rows, or stops moving
backward, the import fails before writing the merged 24H dataset. Inspect the
IBKR error or availability rather than assuming the missing bars are fixed.

Offline validation:
`python Backtesting/Tests/test_ibkr_24h_loader.py`

Live IBKR access is not available in the development workspace; historical
availability and matching to the TradingView feed are not yet verified.
