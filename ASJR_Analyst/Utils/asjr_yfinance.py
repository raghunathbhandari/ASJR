import pandas as pd
import yfinance as yf

def get_daily_ohlcv(tickers, days=30):
    tickers = [t.upper().strip() for t in tickers if str(t).strip()]
    if not tickers:
        return pd.DataFrame()

    data = yf.download(
        tickers=tickers,
        period=f"{max(days + 10, 40)}d",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=True,
    )

    rows = []
    if len(tickers) == 1:
        t = tickers[0]
        df = data.copy().tail(days)
        for idx, r in df.iterrows():
            rows.append({
                "ticker": t,
                "date": idx.date().isoformat(),
                "open": r.get("Open"),
                "high": r.get("High"),
                "low": r.get("Low"),
                "close": r.get("Close"),
                "adj_close": r.get("Adj Close"),
                "volume": r.get("Volume"),
            })
    else:
        for t in tickers:
            if t not in data.columns.get_level_values(0):
                continue
            df = data[t].dropna(how="all").tail(days)
            for idx, r in df.iterrows():
                rows.append({
                    "ticker": t,
                    "date": idx.date().isoformat(),
                    "open": r.get("Open"),
                    "high": r.get("High"),
                    "low": r.get("Low"),
                    "close": r.get("Close"),
                    "adj_close": r.get("Adj Close"),
                    "volume": r.get("Volume"),
                })

    return pd.DataFrame(rows)
