import pandas as pd

REQUIRED_5M_COLUMNS = ["ticker", "datetime", "open", "high", "low", "close", "volume"]

def normalize_5m(df):
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=REQUIRED_5M_COLUMNS)
    out = df.copy()
    out.columns = [str(c).lower().strip() for c in out.columns]
    aliases = {"date":"datetime", "time":"datetime", "symbol":"ticker"}
    out = out.rename(columns={k:v for k,v in aliases.items() if k in out.columns})
    missing = [c for c in REQUIRED_5M_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(f"IBKR 5m data missing columns: {missing}")
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["datetime"] = pd.to_datetime(out["datetime"])
    return out[REQUIRED_5M_COLUMNS].sort_values(["ticker", "datetime"]).reset_index(drop=True)

def normalize_gapup(df):
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["ticker"])
    out = df.copy()
    out.columns = [str(c).lower().strip() for c in out.columns]
    if "symbol" in out.columns and "ticker" not in out.columns:
        out = out.rename(columns={"symbol":"ticker"})
    if "ticker" not in out.columns:
        raise ValueError("Gap-up scanner output must contain ticker or symbol.")
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    return out.drop_duplicates("ticker").reset_index(drop=True)

def get_gapup_tickers(app):
    """
    Adapter for the user's existing IBKR wrapper.

    Supported hook names:
      app.get_gapup_scanner_results()
      app.run_gapup_scanner()
      app.get_gapup_tickers()

    Each hook may return a DataFrame or list of tickers.
    """
    for name in ("get_gapup_scanner_results", "run_gapup_scanner", "get_gapup_tickers"):
        fn = getattr(app, name, None)
        if callable(fn):
            result = fn()
            if isinstance(result, pd.DataFrame):
                return normalize_gapup(result)
            return normalize_gapup(pd.DataFrame({"ticker": list(result or [])}))
    raise NotImplementedError(
        "IBKR gap-up adapter not connected yet. Wire your existing scanner method into Utils/asjr_ibkr.py."
    )

def get_intraday_5m(app, tickers, duration="3 D", batch_size=5, wait_time=20):
    """
    Adapter for the user's existing known-good IBKR 5-minute batch method.

    Critical ASJR rule: default duration remains 3 D, never 14 D.
    """
    for name in ("get_ibkr_5m_batch", "get_5m_batch", "get_intraday_5m"):
        fn = getattr(app, name, None)
        if callable(fn):
            try:
                result = fn(tickers, duration=duration, wait_time=wait_time, batch_size=batch_size)
            except TypeError:
                result = fn(tickers, duration=duration)
            return normalize_5m(result)
    raise NotImplementedError(
        "IBKR 5m adapter not connected yet. Wire your existing get_ibkr_5m_batch() into Utils/asjr_ibkr.py."
    )
