"""
Generic IBKR historical OHLCV loader for ASJR research/backtesting.

This module is intentionally separate from the live Chakra/production IBKR
wrapper flow. It uses ib_async directly and is notebook-friendly.

Flow
----
connect -> qualify contract -> request historical bars in conservative chunks
-> normalize UTC OHLCV -> merge/dedupe -> persist canonical CSV -> return DataFrame

Canonical CSV
-------------
Datetime,Open,High,Low,Close,Volume

IBKR uses its own cache root, separate from Yahoo and the live trading pipeline:
Backtesting/BacktestData/IBKR/MarketData/<interval>/<TICKER>_<interval>.csv

The CSV schema remains canonical so strategy code can stay provider-independent.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import pandas as pd


DEFAULT_IBKR_CACHE_ROOT = Path(__file__).resolve().parents[1] / "BacktestData" / "IBKR" / "MarketData"



CANONICAL_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

# Public/user-friendly interval -> IBKR barSizeSetting.
IBKR_BAR_SIZE = {
    "1m": "1 min",
    "2m": "2 mins",
    "3m": "3 mins",
    "5m": "5 mins",
    "10m": "10 mins",
    "15m": "15 mins",
    "20m": "20 mins",
    "30m": "30 mins",
    "1h": "1 hour",
    "2h": "2 hours",
    "3h": "3 hours",
    "4h": "4 hours",
    "8h": "8 hours",
    "1d": "1 day",
}

# Conservative request windows. These are intentionally smaller than some
# IBKR maximums to reduce pacing/timeouts and make long-range looping stable.
# The loader repeatedly walks backward until start is reached.
IBKR_CHUNK_DURATION = {
    "1m": "1 D",
    "2m": "2 D",
    "3m": "2 D",
    "5m": "5 D",
    "10m": "1 W",
    "15m": "1 W",
    "20m": "1 W",
    "30m": "2 W",
    "1h": "1 M",
    "2h": "1 M",
    "3h": "1 M",
    "4h": "1 M",
    "8h": "1 M",
    "1d": "1 Y",
}


def _normalize_interval(interval: str) -> str:
    value = str(interval).strip().lower()
    aliases = {
        "1min": "1m",
        "2min": "2m",
        "3min": "3m",
        "5min": "5m",
        "10min": "10m",
        "15min": "15m",
        "20min": "20m",
        "30min": "30m",
        "60m": "1h",
        "60min": "1h",
        "hour": "1h",
        "hourly": "1h",
        "day": "1d",
        "daily": "1d",
    }
    value = aliases.get(value, value)
    if value not in IBKR_BAR_SIZE:
        raise ValueError(
            f"Unsupported IBKR interval '{interval}'. "
            f"Supported: {sorted(IBKR_BAR_SIZE)}"
        )
    return value


def _as_utc(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts


def _safe_name(ticker: str) -> str:
    return (
        ticker.upper()
        .replace("^", "INDEX_")
        .replace("=", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def _cache_path_for_ibkr(
    ticker: str,
    interval: str,
    cache_root: str | Path = DEFAULT_IBKR_CACHE_ROOT,
) -> Path:
    interval = _normalize_interval(interval)
    root = Path(cache_root)
    return root / interval / f"{_safe_name(ticker)}_{interval}.csv"


def _empty_df() -> pd.DataFrame:
    df = pd.DataFrame(columns=CANONICAL_COLUMNS)
    df.index = pd.DatetimeIndex([], tz="UTC", name="Datetime")
    return df


def _normalize_ibkr_bars(bars) -> pd.DataFrame:
    """Convert ib_async BarData list to canonical UTC OHLCV DataFrame."""
    if not bars:
        return _empty_df()

    rows = []
    for bar in bars:
        rows.append(
            {
                "Datetime": getattr(bar, "date", None),
                "Open": getattr(bar, "open", None),
                "High": getattr(bar, "high", None),
                "Low": getattr(bar, "low", None),
                "Close": getattr(bar, "close", None),
                "Volume": getattr(bar, "volume", 0),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return _empty_df()

    # formatDate=2 requests UTC-aware datetimes for intraday bars.
    # utc=True also safely handles any exchange-time or naive values returned
    # by a particular TWS/Gateway configuration.
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True, errors="coerce")
    df = df.dropna(subset=["Datetime", "Open", "High", "Low", "Close"])
    df = df.set_index("Datetime")

    for col in CANONICAL_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Volume"] = df["Volume"].fillna(0.0)
    df = df[CANONICAL_COLUMNS].sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df.index.name = "Datetime"
    return df


def read_ibkr_cache(
    ticker: str,
    interval: str,
    *,
    cache_root: str | Path = DEFAULT_IBKR_CACHE_ROOT,
) -> pd.DataFrame:
    """Read the shared canonical OHLCV cache."""
    interval = _normalize_interval(interval)
    path = _cache_path_for_ibkr(ticker, interval, cache_root)

    if not path.exists():
        return _empty_df()

    raw = pd.read_csv(path)
    if "Datetime" not in raw.columns:
        return _empty_df()

    raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True, errors="coerce")
    raw = raw.dropna(subset=["Datetime"])
    raw = raw.set_index("Datetime")

    missing = [c for c in CANONICAL_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"Cache {path} missing columns: {missing}")

    out = raw[CANONICAL_COLUMNS].copy()
    out = out.dropna(subset=["Open", "High", "Low", "Close"])
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.index.name = "Datetime"
    return out


def _write_cache(
    ticker: str,
    interval: str,
    df: pd.DataFrame,
    *,
    cache_root: str | Path = DEFAULT_IBKR_CACHE_ROOT,
) -> Path:
    interval = _normalize_interval(interval)
    path = _cache_path_for_ibkr(ticker, interval, cache_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    out = df[CANONICAL_COLUMNS].copy().sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.index.name = "Datetime"

    tmp = path.with_suffix(path.suffix + ".tmp")
    out.to_csv(tmp)
    tmp.replace(path)
    return path


def _merge(*frames: pd.DataFrame) -> pd.DataFrame:
    good = [f for f in frames if f is not None and not f.empty]
    if not good:
        return _empty_df()

    out = pd.concat(good).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out = out[CANONICAL_COLUMNS]
    out.index.name = "Datetime"
    return out


async def download_data_ibkr_prepare_csv_cache(
    ticker: str,
    start,
    end,
    *,
    interval: str = "5m",
    host: str = "127.0.0.1",
    port: int = 4002,
    client_id: int = 31,
    exchange: str = "SMART",
    currency: str = "USD",
    primary_exchange: Optional[str] = None,
    what_to_show: str = "TRADES",
    use_rth: bool = True,
    cache_root: str | Path = DEFAULT_IBKR_CACHE_ROOT,
    refresh: bool = False,
    pacing_sleep_seconds: float = 0.35,
    ib=None,
    disconnect_when_done: Optional[bool] = None,
) -> pd.DataFrame:
    """
    Download IBKR historical OHLCV over a date range and return a DataFrame.

    Designed for VS Code/Jupyter notebooks:
        df = await download_data_ibkr_prepare_csv_cache(...)

    Parameters
    ----------
    ticker:
        US stock ticker, e.g. "MU".
    start, end:
        Requested date/time range. Naive values are treated as UTC.
    interval:
        Friendly interval such as "5m", "30m", "1h", "4h", "1d".
    ib:
        Optional already-connected ib_async.IB instance. If omitted, this
        function creates its own connection.
    disconnect_when_done:
        Defaults to True when this function created the connection and False
        when caller supplied an existing IB instance.

    Notes
    -----
    - IBKR historical requests use endDateTime + durationStr, so this loader
      walks backward in conservative chunks.
    - Existing cache is merged and de-duplicated.
    - Returned DataFrame always uses UTC DatetimeIndex and canonical columns.
    """
    try:
        from ib_async import IB, Stock
    except ImportError as exc:
        raise ImportError("Install ib_async: pip install ib_async") from exc

    ticker = ticker.upper().strip()
    interval = _normalize_interval(interval)
    start_ts = _as_utc(start)
    end_ts = _as_utc(end)

    # Date-only end values should include that full day.
    end_input = pd.Timestamp(end)
    if (
        isinstance(end, str)
        and len(end.strip()) <= 10
        and end_input.hour == 0
        and end_input.minute == 0
        and end_input.second == 0
    ):
        end_ts = end_ts + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    if end_ts <= start_ts:
        raise ValueError("end must be after start")

    cached = _empty_df() if refresh else read_ibkr_cache(
        ticker, interval, cache_root=cache_root
    )

    created_connection = ib is None
    if created_connection:
        ib = IB()

    if disconnect_when_done is None:
        disconnect_when_done = created_connection

    if not ib.isConnected():
        await ib.connectAsync(
            host,
            int(port),
            clientId=int(client_id),
            timeout=15,
        )

    try:
        contract = Stock(
            ticker,
            exchange,
            currency,
            primaryExchange=primary_exchange or "",
        )
        qualified = await ib.qualifyContractsAsync(contract)
        if not qualified:
            raise RuntimeError(f"IBKR could not qualify contract for {ticker}")
        contract = qualified[0]

        frames = []
        cursor_end = end_ts
        previous_earliest = None
        chunk_no = 0

        while cursor_end > start_ts:
            chunk_no += 1

            # IB accepts datetime endDateTime values directly via ib_async.
            bars = await ib.reqHistoricalDataAsync(
                contract,
                endDateTime=cursor_end.to_pydatetime(),
                durationStr=IBKR_CHUNK_DURATION[interval],
                barSizeSetting=IBKR_BAR_SIZE[interval],
                whatToShow=what_to_show,
                useRTH=use_rth,
                formatDate=2,
                keepUpToDate=False,
            )

            df_chunk = _normalize_ibkr_bars(bars)

            if df_chunk.empty:
                print(
                    f"{ticker} {interval} | chunk {chunk_no}: no bars returned "
                    f"ending {cursor_end}"
                )
                break

            earliest = df_chunk.index.min()
            latest = df_chunk.index.max()
            frames.append(df_chunk)

            print(
                f"{ticker} {interval} | chunk {chunk_no:03d} | "
                f"{earliest} -> {latest} | rows={len(df_chunk)}"
            )

            if earliest <= start_ts:
                break

            # Safety against an IBKR response repeating the same window.
            if previous_earliest is not None and earliest >= previous_earliest:
                raise RuntimeError(
                    f"IBKR historical cursor did not move backward for {ticker}. "
                    f"Repeated earliest bar: {earliest}"
                )

            previous_earliest = earliest
            cursor_end = earliest - pd.Timedelta(seconds=1)

            if pacing_sleep_seconds > 0:
                await asyncio.sleep(pacing_sleep_seconds)

        downloaded = _merge(*frames)

        if not downloaded.empty:
            downloaded = downloaded[
                (downloaded.index >= start_ts) & (downloaded.index <= end_ts)
            ]

        merged = _merge(cached, downloaded)
        path = _write_cache(
            ticker,
            interval,
            merged,
            cache_root=cache_root,
        )

        requested = merged[
            (merged.index >= start_ts) & (merged.index <= end_ts)
        ].copy()

        print("=" * 100)
        print(
            f"IBKR CSV CACHE | {ticker} | interval={interval} | "
            f"requested={start_ts} -> {end_ts}"
        )
        if requested.empty:
            print("No bars available in requested range.")
        else:
            print(
                f"rows={len(requested)} | "
                f"{requested.index.min()} -> {requested.index.max()}"
            )
        print(f"CSV: {path}")
        print("=" * 100)

        return requested

    finally:
        if disconnect_when_done and ib.isConnected():
            ib.disconnect()


async def get_ibkr_ohlcv_df(
    ticker: str,
    start,
    end,
    **kwargs,
) -> pd.DataFrame:
    """
    Generic alias for callers that only care about receiving the DataFrame.

    It uses the same cache-producing loader underneath.
    """
    return await download_data_ibkr_prepare_csv_cache(
        ticker=ticker,
        start=start,
        end=end,
        **kwargs,
    )
