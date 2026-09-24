# ASJR Analyst

Decision-support data lake for manual US-stock trading.

## Workflow
1. Fixed watchlist is prepared one day before.
2. IBKR supplies the live gap-up list and 5-minute OHLCV.
3. yfinance supplies 30-day daily OHLCV.
4. Public sources supply sector / market / analyst context.
5. Processed files are written to the daily DataLake folder.
6. ASJR Analyst reads the snapshot and returns a compact trading report with TradingView links.

## Folder layout
```
ASJR_Analyst/
  Utils/
  Tests/
  DataLake/
    YYYY-MM-DD/
      config/
      raw/
      processed/
      reports/
```

Raw data is never edited after collection. Derived values belong in processed/.
