import pandas as pd
from Utils import asjr_paths as paths

def load_fixed_watchlist(trade_date=None, enabled_only=True):
    file = paths.config_path("fixed_watchlist.csv", trade_date)
    df = pd.read_csv(file)
    if enabled_only and "enabled" in df.columns:
        df = df[df["enabled"].astype(str).isin(["1", "True", "true", "YES", "yes"])]
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    return df.reset_index(drop=True)

def fixed_tickers(trade_date=None):
    return load_fixed_watchlist(trade_date)["ticker"].dropna().unique().tolist()
