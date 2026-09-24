import pandas as pd
import yfinance as yf

SECTOR_ETFS = {
    "Technology": "XLK",
    "Semiconductors": "SMH",
    "Communication Services": "XLC",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Clean Energy": "ICLN",
}

BENCHMARKS = ["SPY", "QQQ"]

def _download_daily(tickers, period="10d"):
    return yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=True,
    )

def get_market_sector_daily():
    symbol_to_name = {v:k for k,v in SECTOR_ETFS.items()}
    for b in BENCHMARKS:
        symbol_to_name[b] = b

    tickers = list(symbol_to_name)
    data = _download_daily(tickers)
    rows = []

    for ticker in tickers:
        try:
            df = data[ticker].dropna(how="all").copy()
        except Exception:
            continue
        if len(df) < 2:
            continue

        close = df["Close"].astype(float)
        volume = df["Volume"].astype(float)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) >= 3 else prev

        today_pct = (float(last["Close"]) / float(prev["Close"]) - 1) * 100
        yesterday_pct = (float(prev["Close"]) / float(prev2["Close"]) - 1) * 100 if len(df) >= 3 else None
        avg_vol = float(volume.tail(20).mean()) if len(volume) else None
        rvol = float(last["Volume"]) / avg_vol if avg_vol else None

        rows.append({
            "name": symbol_to_name[ticker],
            "ticker": ticker,
            "date": df.index[-1].date().isoformat(),
            "close": float(last["Close"]),
            "today_pct": today_pct,
            "yesterday_pct": yesterday_pct,
            "volume": float(last["Volume"]),
            "avg_volume": avg_vol,
            "rvol": rvol,
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    spy_row = out[out["ticker"] == "SPY"]
    spy_pct = float(spy_row.iloc[0]["today_pct"]) if not spy_row.empty else 0.0
    out["relative_to_spy_pct"] = out["today_pct"] - spy_pct

    def status(r):
        t, y = r["today_pct"], r["yesterday_pct"]
        if pd.notna(y) and t > 0 and y > 0:
            return "STRONG_BOTH"
        if t > 0 and (pd.isna(y) or y <= 0):
            return "IMPROVING"
        if t < 0 and pd.notna(y) and y > 0:
            return "WEAKENING"
        return "WEAK"

    out["status"] = out.apply(status, axis=1)
    return out.sort_values(["today_pct", "relative_to_spy_pct"], ascending=False).reset_index(drop=True)
