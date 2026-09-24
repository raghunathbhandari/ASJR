from __future__ import annotations
import time
import pandas as pd
from ibapi.contract import Contract

def _next_req_id(app):
    lock = getattr(app, "id_lock", None)
    if lock:
        with lock:
            req_id = app.nextReqId
            app.nextReqId += 1
            return req_id
    req_id = app.nextReqId
    app.nextReqId += 1
    return req_id

def stock_contract(ticker: str):
    c = Contract()
    c.symbol = str(ticker).strip().upper()
    c.secType = "STK"
    c.exchange = "SMART"
    c.currency = "USD"
    return c

def parse_ibkr_bars(rows):
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    numeric_date = pd.to_numeric(df["Date"], errors="coerce")

    if numeric_date.notna().any():
        df = df.loc[numeric_date.notna()].copy()
        df["Date"] = pd.to_datetime(
            numeric_date.loc[numeric_date.notna()].astype("int64"),
            unit="s",
            utc=True,
        ).dt.tz_convert("America/New_York")
    else:
        parsed = pd.to_datetime(df["Date"], errors="coerce", utc=True)
        df = df.loc[parsed.notna()].copy()
        df["Date"] = parsed.loc[parsed.notna()].dt.tz_convert("America/New_York")

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return (
        df.dropna(subset=["Date", "Open", "High", "Low", "Close"])
        .set_index("Date")
        .sort_index()
    )



def normalize_gapup(df):
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["ticker"])

    out = df.copy()
    out.columns = [str(col).lower().strip() for col in out.columns]

    if "symbol" in out.columns and "ticker" not in out.columns:
        out = out.rename(columns={"symbol": "ticker"})

    if "ticker" not in out.columns:
        raise ValueError("Gap-up data must contain ticker or symbol.")

    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    return out[out["ticker"] != ""].drop_duplicates("ticker").reset_index(drop=True)

def get_gapup_tickers(app):
    """
    Optional adapter for an existing working gap-up scanner on the ready app object.
    We will replace/align this hook with the user's proven scanner method when supplied.
    """
    for name in ("get_gapup_scanner_results", "run_gapup_scanner", "get_gapup_tickers"):
        fn = getattr(app, name, None)
        if callable(fn):
            result = fn()
            if isinstance(result, pd.DataFrame):
                return normalize_gapup(result)
            return normalize_gapup(pd.DataFrame({"ticker": list(result or [])}))

    raise NotImplementedError(
        "Gap-up scanner hook is not connected yet. Pass gapup_df manually or wire the existing scanner method."
    )

def get_ibkr_5m_batch(
    app,
    tickers,
    duration="3 D",
    end_datetime="",
    wait_time=20,
    batch_size=5,
):
    """
    ASJR V5.3 compatible historical 5-minute fetch.

    Uses the existing ready IBKR app wrapper variables:
      app.nextReqId
      app.id_lock
      app.data
      app.hist_done

    Returns:
      dict[ticker] -> DataFrame indexed by America/New_York Date.
    """
    result = {}

    tickers = [
        str(t).strip().upper()
        for t in tickers
        if str(t).strip()
    ]

    for start in range(0, len(tickers), batch_size):
        batch = tickers[start:start + batch_size]
        req_map = {}

        for ticker in batch:
            try:
                req_id = _next_req_id(app)

                app.data[req_id] = []
                app.hist_done[req_id] = False
                req_map[req_id] = ticker

                app.reqHistoricalData(
                    req_id,
                    stock_contract(ticker),
                    end_datetime,
                    duration,
                    "5 mins",
                    "TRADES",
                    0,
                    2,
                    False,
                    [],
                )

            except Exception as exc:
                print(f"ASJR ANALYST IBKR REQUEST ERROR | {ticker} | {exc}")

        start_wait = time.time()

        while req_map and (time.time() - start_wait) < wait_time:
            if all(app.hist_done.get(req_id, False) for req_id in req_map):
                break
            time.sleep(0.10)

        for req_id, ticker in req_map.items():
            try:
                rows = app.data.get(req_id, [])
                result[ticker] = parse_ibkr_bars(rows)
            except Exception as exc:
                print(f"ASJR ANALYST IBKR PARSE ERROR | {ticker} | {exc}")
                result[ticker] = pd.DataFrame()
            finally:
                app.data.pop(req_id, None)
                app.hist_done.pop(req_id, None)

        time.sleep(0.5)

    return result

def completed_bars(df, now_et):
    if df is None or df.empty:
        return pd.DataFrame()
    now_ts = pd.Timestamp(now_et)
    return df[(df.index + pd.Timedelta(minutes=5)) <= now_ts].copy()

def historical_end_datetime(test_date):
    next_day = pd.Timestamp(test_date) + pd.Timedelta(days=1)
    return next_day.strftime("%Y%m%d 00:00:00 US/Eastern")

def combine_5m(result):
    """
    Convert V5.3 dict[ticker] -> DataFrame into one CSV-ready DataFrame.
    """
    frames = []
    for ticker, df in (result or {}).items():
        if df is None or df.empty:
            continue
        x = df.reset_index().copy()
        x.insert(0, "Ticker", str(ticker).upper())
        frames.append(x)

    if not frames:
        return pd.DataFrame(columns=["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"])

    return (
        pd.concat(frames, ignore_index=True)
        .sort_values(["Ticker", "Date"])
        .reset_index(drop=True)
    )
