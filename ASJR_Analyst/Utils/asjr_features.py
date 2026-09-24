import pandas as pd

def add_ema20(df):
    out = df.copy()
    out["ema20"] = out.groupby("ticker")["close"].transform(
        lambda s: s.ewm(span=20, adjust=False).mean()
    )
    out["dist_ema20_pct"] = ((out["close"] / out["ema20"]) - 1.0) * 100.0
    return out

def add_daily_atr14(df):
    out = df.sort_values(["ticker", "date"]).copy()
    prev_close = out.groupby("ticker")["close"].shift(1)
    tr = pd.concat([
        out["high"] - out["low"],
        (out["high"] - prev_close).abs(),
        (out["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    out["atr14"] = tr.groupby(out["ticker"]).transform(
        lambda s: s.rolling(14, min_periods=3).mean()
    )
    return out

def latest_daily_summary(df):
    if df.empty:
        return df.copy()
    out = df.sort_values(["ticker", "date"]).groupby("ticker", as_index=False).tail(1)
    return out.reset_index(drop=True)
