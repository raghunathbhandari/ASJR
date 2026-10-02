import os
from pathlib import Path
import pandas as pd
import yfinance as yf

TICKERS = ["QQQ","MSFT","NVDA","GOOG","INTC","MU","AMAT","QCOM","LRCX","WDC"]
START = "2025-10-01"
END = "2026-10-02"
OUT = Path("ASJR_Analyst/BacktestData/daily_1y_10_tickers.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

frames = []
for ticker in TICKERS:
    df = yf.download(
        ticker,
        start=START,
        end=END,
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    if df.empty:
        raise RuntimeError(f"No data returned for {ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.reset_index()
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    rename = {"date":"date","open":"open","high":"high","low":"low","close":"close",
              "adj_close":"adj_close","volume":"volume"}
    keep = ["date","open","high","low","close","adj_close","volume"]
    df = df[keep]
    df.insert(0, "ticker", ticker)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    frames.append(df)

out = pd.concat(frames, ignore_index=True)
out = out.sort_values(["ticker","date"]).reset_index(drop=True)

# Sanity checks: roughly one US trading year per ticker.
counts = out.groupby("ticker").size()
if (counts < 240).any():
    raise RuntimeError(f"Unexpectedly low row count: {counts.to_dict()}")

out.to_csv(OUT, index=False)
print(f"Wrote {OUT} with {len(out)} rows")
print(counts.to_string())
