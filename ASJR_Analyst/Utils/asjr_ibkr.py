from __future__ import annotations
import time
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


def _run_scanner(
    app,
    scan_code,
    percent_filter_tag=None,
    percent_filter_value=None,
    wait_time=5,
    AvgVol="1000000",
    PriceAbove="5",
    marketCapAbove="500",
):
    """Run one filtered IBKR US stock scanner and return unique tickers."""
    req_id = _next_req_id(app)

    app.scanner_results[req_id] = []
    app.scanner_done[req_id] = False

    sub = ScannerSubscription()
    sub.instrument = "STK"
    sub.locationCode = "STK.US.MAJOR"
    sub.scanCode = scan_code
    sub.numberOfRows = 50
    # Keep the discovery feed focused on operating companies rather than ETFs.
    sub.stockTypeFilter = "CORP"

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
    ]

    if percent_filter_tag and percent_filter_value is not None:
        filters.append(
            TagValue(
                percent_filter_tag,
                str(percent_filter_value),
            )
        )

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

    app.scanner_results.pop(req_id, None)
    app.scanner_done.pop(req_id, None)

    filter_text = (
        f"{percent_filter_tag}={percent_filter_value}"
        if percent_filter_tag
        else "no percent filter"
    )

    print(
        f"ASJR MOVER | {scan_code} | "
        f"{filter_text} | "
        f"Tickers: {len(tickers)}"
    )

    return tickers


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
    ASJR market-wide percentage-mover scanner.

    AUTO scans BOTH directions in every active session:
      TOP_PERC_GAIN + changePercAbove >= threshold
      TOP_PERC_LOSE + changePercBelow <= -threshold

    This deliberately replaces the old RTH HIGH_OPEN_GAP behavior.
    A stock does not need to gap 4% at the open; if it reaches +/-4%
    versus the prior close during premarket or RTH, it can enter the
    ASJR universe for 5-minute structure/EMA analysis.

    GapUpPcnt is retained as the argument name for caller compatibility;
    it now means the absolute percentage-move threshold.
    """
    threshold = str(GapUpPcnt).strip().lstrip("-")

    if scan_code in (None, "AUTO"):
        gainers = _run_scanner(
            app=app,
            scan_code="TOP_PERC_GAIN",
            percent_filter_tag="changePercAbove",
            percent_filter_value=threshold,
            wait_time=wait_time,
            AvgVol=AvgVol,
            PriceAbove=PriceAbove,
            marketCapAbove=marketCapAbove,
        )

        losers = _run_scanner(
            app=app,
            scan_code="TOP_PERC_LOSE",
            percent_filter_tag="changePercBelow",
            percent_filter_value=f"-{threshold}",
            wait_time=wait_time,
            AvgVol=AvgVol,
            PriceAbove=PriceAbove,
            marketCapAbove=marketCapAbove,
        )

        tickers = list(dict.fromkeys(gainers + losers))

        print(
            f"ASJR MOVER | AUTO | "
            f"|change| >= {threshold}% | "
            f"Gainers: {len(gainers)} | "
            f"Losers: {len(losers)} | "
            f"Unique: {len(tickers)}"
        )

        return tickers

    filter_map = {
        "TOP_PERC_GAIN": ("changePercAbove", threshold),
        "TOP_PERC_LOSE": ("changePercBelow", f"-{threshold}"),
        "HIGH_OPEN_GAP": ("openGapPercAbove", threshold),
        "LOW_OPEN_GAP": ("openGapPercBelow", f"-{threshold}"),
    }

    filter_tag, filter_value = filter_map.get(
        scan_code,
        (None, None),
    )

    return _run_scanner(
        app=app,
        scan_code=scan_code,
        percent_filter_tag=filter_tag,
        percent_filter_value=filter_value,
        wait_time=wait_time,
        AvgVol=AvgVol,
        PriceAbove=PriceAbove,
        marketCapAbove=marketCapAbove,
    )


def get_gapup_tickers(
    app,
    GapUpPcnt="4",
    AvgVol="1000000",
    PriceAbove="5",
    marketCapAbove="500",
    wait_time=5,
):
    """
    Backward-compatible pipeline adapter.

    Despite the legacy function name, this now returns liquid US stocks
    moving at least +/- GapUpPcnt from the prior close, using both
    TOP_PERC_GAIN and TOP_PERC_LOSE. This lets the DataLake discover
    BE/FICO-style intraday movers even when they did not open with a 4% gap.
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
        # A temporary empty HMDS/IBKR response is not a trading alert.
        # Return the empty result normally so the pipeline produces no
        # EMA20/wick events; keep the diagnostic in the local run output.
        print(
            "ASJR IBKR 5M | ZERO ROWS AFTER RETRY | "
            "no EMA20/wick alert generated"
        )
        return result

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
