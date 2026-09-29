from __future__ import annotations
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from ibapi.contract import Contract
from ibapi.scanner import ScannerSubscription
from ibapi.tag_value import TagValue


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

    df = pd.DataFrame(
        rows,
        columns=["Date", "Open", "High", "Low", "Close", "Volume"],
    )

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
        df["Date"] = parsed.loc[
            parsed.notna()
        ].dt.tz_convert("America/New_York")

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return (
        df.dropna(
            subset=["Date", "Open", "High", "Low", "Close"]
        )
        .set_index("Date")
        .sort_index()
    )


def normalize_gapup(df):
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["ticker"])

    out = df.copy()
    out.columns = [
        str(col).lower().strip()
        for col in out.columns
    ]

    if "symbol" in out.columns and "ticker" not in out.columns:
        out = out.rename(columns={"symbol": "ticker"})

    if "ticker" not in out.columns:
        raise ValueError(
            "Gap-up data must contain ticker or symbol."
        )

    out["ticker"] = (
        out["ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    return (
        out[out["ticker"] != ""]
        .drop_duplicates("ticker")
        .reset_index(drop=True)
    )


def get_api_tickers(
    app,
    scan_code="AUTO",
    wait_time=5,
    AvgVol="1000000",
    PriceAbove="5",
    marketCapAbove="500",
    GapUpPcnt="4",
):
    """
    Working IBKR scanner used by ASJR Analyst.

    Premarket:
      TOP_PERC_GAIN + changePercAbove

    Regular market:
      HIGH_OPEN_GAP + openGapPercAbove

    Default ASJR Analyst gap threshold: 4%.
    """
    now_et = datetime.now(
        ZoneInfo("America/New_York")
    )

    premarket = (
        now_et.hour,
        now_et.minute,
    ) < (9, 30)

    if scan_code in (None, "AUTO"):
        scan_code = (
            "TOP_PERC_GAIN"
            if premarket
            else "HIGH_OPEN_GAP"
        )

    gap_filter = (
        "changePercAbove"
        if premarket
        else "openGapPercAbove"
    )

    req_id = _next_req_id(app)

    app.scanner_results[req_id] = []
    app.scanner_done[req_id] = False

    sub = ScannerSubscription()
    sub.instrument = "STK"
    sub.locationCode = "STK.US.MAJOR"
    sub.scanCode = scan_code
    sub.numberOfRows = 50

    filters = [
        TagValue(
            "marketCapAbove1e6",
            marketCapAbove,
        ),
        TagValue(
            "usdPriceAbove",
            PriceAbove,
        ),
        TagValue(
            "avgVolumeAbove",
            AvgVol,
        ),
        TagValue(
            gap_filter,
            str(GapUpPcnt),
        ),
    ]

    app.reqScannerSubscription(
        req_id,
        sub,
        [],
        filters,
    )

    start = time.time()

    while (
        not app.scanner_done.get(req_id, False)
        and time.time() - start < wait_time
    ):
        time.sleep(0.2)

    app.cancelScannerSubscription(req_id)

    tickers = list(
        dict.fromkeys(
            app.scanner_results.get(req_id, [])
        )
    )

    print(
        f"{'PREMARKET' if premarket else 'MARKET'} | "
        f"{scan_code} | "
        f"Gap >= {GapUpPcnt}% | "
        f"Tickers: {len(tickers)}"
    )

    return tickers


def get_gapup_tickers(
    app,
    GapUpPcnt="4",
    AvgVol="1000000",
    PriceAbove="5",
    marketCapAbove="500",
    wait_time=5,
):
    """
    ASJR Analyst gap-up adapter.

    Calls the proven get_api_tickers() scanner directly and
    returns a normalized DataFrame for the pipeline.
    """
    tickers = get_api_tickers(
        app=app,
        scan_code="AUTO",
        wait_time=wait_time,
        AvgVol=AvgVol,
        PriceAbove=PriceAbove,
        marketCapAbove=marketCapAbove,
        GapUpPcnt=GapUpPcnt,
    )

    return normalize_gapup(
        pd.DataFrame({"ticker": tickers})
    )


def get_ibkr_5m_batch(
    app,
    tickers,
    duration="3 D",
    end_datetime="",
    wait_time=20,
    batch_size=5,
):
    result = {}

    tickers = [
        str(t).strip().upper()
        for t in tickers
        if str(t).strip()
    ]

    def fetch_batch(batch, attempt=1):
        req_map = {}

        print(
            f"ASJR IBKR 5M | Batch start | "
            f"attempt={attempt} | tickers={','.join(batch)}"
        )

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
                print(
                    "ASJR ANALYST IBKR REQUEST ERROR | "
                    f"{ticker} | attempt={attempt} | {exc}"
                )

        start_wait = time.time()

        while req_map and (time.time() - start_wait) < wait_time:
            if all(
                app.hist_done.get(req_id, False)
                for req_id in req_map
            ):
                break

            time.sleep(0.10)

        batch_result = {}
        failed = []

        for req_id, ticker in req_map.items():
            try:
                done = app.hist_done.get(req_id, False)
                rows = app.data.get(req_id, [])

                if not done:
                    print(
                        f"ASJR IBKR 5M | TIMEOUT | "
                        f"{ticker} | reqId={req_id} | "
                        f"rows_received={len(rows)}"
                    )

                    try:
                        app.cancelHistoricalData(req_id)
                    except Exception:
                        pass

                df = parse_ibkr_bars(rows)
                batch_result[ticker] = df

                print(
                    f"ASJR IBKR 5M | RESULT | "
                    f"{ticker} | attempt={attempt} | "
                    f"done={done} | rows={len(df)}"
                )

                if df.empty:
                    failed.append(ticker)

            except Exception as exc:
                print(
                    "ASJR ANALYST IBKR PARSE ERROR | "
                    f"{ticker} | attempt={attempt} | {exc}"
                )
                batch_result[ticker] = pd.DataFrame()
                failed.append(ticker)

            finally:
                app.data.pop(req_id, None)
                app.hist_done.pop(req_id, None)

        return batch_result, failed

    for start in range(0, len(tickers), batch_size):
        batch = tickers[start:start + batch_size]

        batch_result, failed = fetch_batch(
            batch,
            attempt=1,
        )
        result.update(batch_result)

        if failed:
            print(
                "ASJR IBKR 5M | RETRY | "
                f"tickers={','.join(failed)}"
            )
            time.sleep(2)

            retry_result, still_failed = fetch_batch(
                failed,
                attempt=2,
            )
            result.update(retry_result)

            if still_failed:
                print(
                    "ASJR IBKR 5M | FAILED AFTER RETRY | "
                    f"tickers={','.join(still_failed)}"
                )

        time.sleep(0.5)

    total_rows = sum(
        len(df)
        for df in result.values()
        if df is not None
    )

    successful = [
        ticker
        for ticker, df in result.items()
        if df is not None and not df.empty
    ]

    failed = [
        ticker
        for ticker in tickers
        if ticker not in successful
    ]

    print(
        f"ASJR IBKR 5M | COMPLETE | "
        f"tickers={len(tickers)} | "
        f"successful={len(successful)} | "
        f"failed={len(failed)} | "
        f"rows={total_rows}"
    )

    if failed:
        print(
            "ASJR IBKR 5M | MISSING | "
            + ", ".join(failed)
        )

    if tickers and total_rows == 0:
        raise RuntimeError(
            "IBKR 5m fetch returned ZERO rows after retry. "
            "Possible temporary HMDS/IBKR connection state problem."
        )

    return result

def combine_5m(result):
    """
    Convert V5.3 dict[ticker] -> DataFrame
    into one CSV-ready DataFrame.
    """
    frames = []

    for ticker, df in (
        result or {}
    ).items():
        if df is None or df.empty:
            continue

        x = df.reset_index().copy()
        x.insert(
            0,
            "Ticker",
            str(ticker).upper(),
        )

        frames.append(x)

    if not frames:
        return pd.DataFrame(
            columns=[
                "Ticker",
                "Date",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
            ]
        )

    return (
        pd.concat(
            frames,
            ignore_index=True,
        )
        .sort_values(
            ["Ticker", "Date"]
        )
        .reset_index(drop=True)
    )
