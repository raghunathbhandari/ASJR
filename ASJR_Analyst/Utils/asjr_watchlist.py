import pandas as pd
from Utils import asjr_paths as paths

def _clean_watchlist(df, enabled_only=True):
    if enabled_only and "enabled" in df.columns:
        df = df[df["enabled"].astype(str).isin(["1", "True", "true", "YES", "yes"])]
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    return df.reset_index(drop=True)

def load_fixed_watchlist(trade_date=None, enabled_only=True):
    file = paths.config_path("fixed_watchlist.csv", trade_date)
    df = pd.read_csv(file)
    return _clean_watchlist(df, enabled_only=enabled_only)

def fixed_tickers(trade_date=None):
    return load_fixed_watchlist(trade_date)["ticker"].dropna().unique().tolist()

def load_hot_sector_watchlist(enabled_only=True):
    file = paths.master_config_path("hot_sector_watchlist.csv")
    df = pd.read_csv(file)
    return _clean_watchlist(df, enabled_only=enabled_only)

def hot_sector_tickers():
    return load_hot_sector_watchlist()["ticker"].dropna().unique().tolist()
