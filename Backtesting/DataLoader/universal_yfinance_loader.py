"""
Universal cached Yahoo Finance data loader for ASJR backtesting.

Goals
-----
1. Read local CSV cache first.
2. Download only missing date ranges.
3. Split requests into interval-safe chunks.
4. Use bounded multithreading for faster batch imports.
5. Merge, de-duplicate, sort, and persist normalized OHLCV CSV files.
6. Keep data loading separate from strategy logic.
7. Never silently pretend Yahoo can provide unavailable historical intraday data.

Yahoo history constraints
-------------------------
Yahoo/yfinance currently restricts historical intraday data. In particular,
1h/60m is limited to roughly the most recent 730 days. Smaller intraday
intervals have shorter limits. Chunking can make allowed requests reliable,
but it cannot bypass Yahoo's overall lookback limit.

For a true multi-year 4H backtest, use a provider capable of supplying that
intraday history (for example IBKR) and save it into the same canonical cache
format.

Canonical CSV columns
---------------------
Datetime,Open,High,Low,Close,Volume
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


DEFAULT_CACHE_ROOT = Path(__file__).resolve().parents[1] / "BacktestData" / "MarketData"

# Conservative Yahoo availability rules.
# None means no practical historical lookback restriction for our loader.
# Small safety buffer because Yahoo enforces intraday lookback using exact
# timestamps; the nominal calendar-day boundary can be rejected by hours.
PROVIDER_LIMIT_SAFETY_DAYS = 2

INTERVAL_LIMIT_DAYS = {
    "1m": 7,
    "2m": 60,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "60m": 730,
    "90m": 60,
    "1h": 730,
    "1d": None,
    "5d": None,
    "1wk": None,
    "1mo": None,
    "3mo": None,
}

# Smaller chunks reduce timeout/rate-limit failures.
DEFAULT_CHUNK_DAYS = {
    "1m": 3,
    "2m": 20,
    "5m": 20,
    "15m": 20,
    "30m": 20,
    "60m": 180,
    "90m": 20,
    "1h": 180,
    "1d": 3650,
    "5d": 3650,
    "1wk": 7300,
    "1mo": 15000,
    "3mo": 30000,
}


@dataclass(frozen=True)
class LoadResult:
    ticker: str
    interval: str
    data: pd.DataFrame
    cache_path: Path
    requested_start: pd.Timestamp
    requested_end: pd.Timestamp
    available_start: Optional[pd.Timestamp]
    available_end: Optional[pd.Timestamp]
    from_cache_only: bool
    clipped_by_provider_limit: bool


class ProviderHistoryLimitError(ValueError):
    """Requested range exceeds the provider's supported lookback."""


def _as_day(value: str | date | datetime | pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts.normalize()


def _normalize_interval(interval: str) -> str:
    value = str(interval).strip().lower()
    aliases = {
        "60min": "60m",
        "60minute": "60m",
        "hour": "1h",
        "hourly": "1h",
        "day": "1d",
        "daily": "1d",
    }
    value = aliases.get(value, value)
    if value not in INTERVAL_LIMIT_DAYS:
        raise ValueError(
            f"Unsupported interval '{interval}'. "
            f"Supported: {sorted(INTERVAL_LIMIT_DAYS)}"
        )
    return value


def _safe_name(ticker: str) -> str:
    return (
        ticker.upper()
        .replace("^", "INDEX_")
        .replace("=", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def cache_path_for(
    ticker: str,
    interval: str,
    cache_root: str | Path = DEFAULT_CACHE_ROOT,
) -> Path:
    interval = _normalize_interval(interval)
    root = Path(cache_root)
    return root / interval / f"{_safe_name(ticker)}_{interval}.csv"


def _normalize_yf_columns(
    df: pd.DataFrame,
    ticker: Optional[str] = None,
) -> pd.DataFrame:
    """
    Normalize yfinance output to a single-ticker OHLCV dataframe.

    yfinance may return:
    - ordinary single-level OHLCV columns;
    - MultiIndex columns such as (Price, Ticker);
    - occasionally duplicate labels when several concurrent downloads finish
      near the same time.

    Select columns positionally so a duplicate label can never turn one field
    into a 2-D dataframe.
    """
    canonical = ["Open", "High", "Low", "Close", "Volume"]

    if df is None or df.empty:
        return pd.DataFrame(columns=canonical)

    out = df.copy()
    wanted = set(canonical)
    ticker_upper = ticker.upper() if ticker else None
    selected: dict[str, pd.Series] = {}

    if isinstance(out.columns, pd.MultiIndex):
        # Prefer a column tuple that explicitly contains the requested ticker.
        for field in canonical:
            candidates: list[int] = []

            for pos, col in enumerate(out.columns):
                parts = [str(x).strip() for x in col]
                parts_upper = [x.upper() for x in parts]

                if field.upper() not in parts_upper:
                    continue

                if ticker_upper is not None and ticker_upper not in parts_upper:
                    continue

                candidates.append(pos)

            # Fallback for a genuine single-ticker MultiIndex where ticker
            # text is absent/unexpected but the OHLCV field is unambiguous.
            if not candidates:
                for pos, col in enumerate(out.columns):
                    parts_upper = [str(x).strip().upper() for x in col]
                    if field.upper() in parts_upper:
                        candidates.append(pos)

            if candidates:
                selected[field] = out.iloc[:, candidates[0]]

    else:
        # Select by POSITION, not out[label], because duplicate labels make
        # pandas return a dataframe rather than a Series.
        for field in canonical:
            for pos, col in enumerate(out.columns):
                if str(col).strip().title() == field:
                    selected[field] = out.iloc[:, pos]
                    break

    normalized = pd.DataFrame(selected, index=out.index)

    required = ["Open", "High", "Low", "Close"]
    if not all(col in normalized.columns for col in required):
        return pd.DataFrame(columns=canonical)

    if "Volume" not in normalized.columns:
        normalized["Volume"] = 0.0

    normalized = normalized[canonical]
    normalized = normalized.dropna(subset=required)
    normalized.index = pd.DatetimeIndex(normalized.index)
    normalized.index.name = "Datetime"
    return normalized.sort_index()


def _read_cache(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    try:
        df = pd.read_csv(path, parse_dates=["Datetime"], index_col="Datetime")
    except Exception:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    return _normalize_yf_columns(df)


def _write_cache(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")

    out = df.copy().sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.index.name = "Datetime"
    out.to_csv(tmp)
    tmp.replace(path)


def provider_earliest_start(
    interval: str,
    *,
    now: Optional[pd.Timestamp] = None,
) -> Optional[pd.Timestamp]:
    interval = _normalize_interval(interval)
    limit = INTERVAL_LIMIT_DAYS[interval]
    if limit is None:
        return None

    current = now or pd.Timestamp.now(tz="UTC")
    if current.tzinfo is not None:
        current = current.tz_localize(None)

    return (
        current.normalize()
        - pd.Timedelta(days=limit)
        + pd.Timedelta(days=PROVIDER_LIMIT_SAFETY_DAYS)
    )


def validate_requested_range(
    start,
    end,
    interval: str,
    *,
    strict: bool = True,
) -> tuple[pd.Timestamp, pd.Timestamp, bool]:
    start_ts = _as_day(start)
    end_ts = _as_day(end)

    if end_ts < start_ts:
        raise ValueError("end must be on or after start")

    earliest = provider_earliest_start(interval)
    clipped = False

    if earliest is not None and start_ts < earliest:
        if strict:
            raise ProviderHistoryLimitError(
                f"Yahoo {interval} data is limited to roughly the latest "
                f"{INTERVAL_LIMIT_DAYS[_normalize_interval(interval)]} days. "
                f"Requested start {start_ts.date()} is older than approximately "
                f"{earliest.date()}. Chunking/looping cannot bypass this provider "
                "lookback limit. Use a longer-history intraday provider such as "
                "IBKR, or explicitly request a coarser supported interval."
            )
        start_ts = earliest
        clipped = True

    return start_ts, end_ts, clipped


def _date_chunks(
    start: pd.Timestamp,
    end: pd.Timestamp,
    interval: str,
    chunk_days: Optional[int] = None,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    interval = _normalize_interval(interval)
    days = int(chunk_days or DEFAULT_CHUNK_DAYS[interval])
    if days < 1:
        raise ValueError("chunk_days must be >= 1")

    chunks: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    cursor = start

    # yfinance end is exclusive, so use end + one day for final coverage.
    exclusive_end = end + pd.Timedelta(days=1)

    while cursor < exclusive_end:
        chunk_end = min(cursor + pd.Timedelta(days=days), exclusive_end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end

    return chunks


def _download_chunk(
    ticker: str,
    interval: str,
    start: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    *,
    auto_adjust: bool,
    prepost: bool,
) -> pd.DataFrame:
    """
    Download one ticker/date chunk.

    Use Ticker.history() instead of yf.download() because concurrent
    yf.download() calls can intermittently fail inside yfinance with errors
    such as "No objects to concatenate". Each thread gets its own Ticker
    object and request path.
    """
    try:
        import time
        import yfinance as yf
    except ImportError as exc:
        raise ImportError("Install yfinance: pip install yfinance") from exc

    last_exc = None

    for attempt in range(3):
        try:
            tk = yf.Ticker(ticker.upper())
            raw = tk.history(
                start=start.strftime("%Y-%m-%d"),
                end=end_exclusive.strftime("%Y-%m-%d"),
                interval=interval,
                auto_adjust=auto_adjust,
                prepost=prepost,
                actions=False,
                repair=False,
            )

            normalized = _normalize_yf_columns(raw, ticker=ticker)

            # Empty can be legitimate for a holiday-only chunk, but for our
            # multi-month chunks it usually means Yahoo returned no data.
            if normalized.empty:
                if attempt < 2:
                    time.sleep(1.0 + attempt)
                    continue

            return normalized

        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1.0 + attempt)
                continue

    if last_exc is not None:
        raise RuntimeError(
            f"Ticker.history failed after retries for {ticker} {interval} "
            f"{start.date()} -> {end_exclusive.date()}: {last_exc}"
        ) from last_exc

    return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])


def _merge_frames(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    good = [f for f in frames if f is not None and not f.empty]
    if not good:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    out = pd.concat(good).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.index.name = "Datetime"
    return out[["Open", "High", "Low", "Close", "Volume"]]


def _missing_segments(
    cached: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """
    Return only leading/trailing date gaps.

    This deliberately does not attempt to fill weekends/holidays or detect
    every intraday missing bar. It avoids unnecessary provider calls while
    supporting incremental cache extension.
    """
    if cached.empty:
        return [(start, end)]

    idx = pd.DatetimeIndex(cached.index)
    idx_naive = idx.tz_localize(None) if idx.tz is not None else idx

    cache_start = pd.Timestamp(idx_naive.min()).normalize()
    cache_end = pd.Timestamp(idx_naive.max()).normalize()

    segments = []

    if start < cache_start:
        segments.append((start, min(end, cache_start)))

    if end > cache_end:
        segments.append((max(start, cache_end), end))

    return [(a, b) for a, b in segments if b >= a]


def load_yfinance_cached(
    ticker: str,
    start,
    end,
    *,
    interval: str = "1d",
    cache_root: str | Path = DEFAULT_CACHE_ROOT,
    refresh: bool = False,
    strict_history: bool = True,
    chunk_days: Optional[int] = None,
    max_workers: int = 4,
    auto_adjust: bool = False,
    prepost: bool = False,
) -> LoadResult:
    """
    Load one ticker from cache, downloading only missing date ranges.

    Parameters
    ----------
    strict_history:
        True (default): fail if requested intraday history exceeds Yahoo's
        lookback limit. This prevents accidental partial backtests.
        False: clip to Yahoo's earliest available date and mark the result.
    """
    ticker = ticker.upper()
    interval = _normalize_interval(interval)

    effective_start, end_ts, clipped = validate_requested_range(
        start,
        end,
        interval,
        strict=strict_history,
    )
    requested_start = _as_day(start)
    requested_end = _as_day(end)

    path = cache_path_for(ticker, interval, cache_root)
    cached = _read_cache(path)

    if refresh:
        missing = [(effective_start, end_ts)]
    else:
        missing = _missing_segments(cached, effective_start, end_ts)

    jobs = []
    for seg_start, seg_end in missing:
        jobs.extend(
            _date_chunks(
                seg_start,
                seg_end,
                interval,
                chunk_days=chunk_days,
            )
        )

    downloaded: list[pd.DataFrame] = []

    if jobs:
        worker_count = max(1, min(int(max_workers), len(jobs)))

        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures = {
                pool.submit(
                    _download_chunk,
                    ticker,
                    interval,
                    chunk_start,
                    chunk_end,
                    auto_adjust=auto_adjust,
                    prepost=prepost,
                ): (chunk_start, chunk_end)
                for chunk_start, chunk_end in jobs
            }

            for future in as_completed(futures):
                chunk_start, chunk_end = futures[future]
                try:
                    downloaded.append(future.result())
                except Exception as exc:
                    raise RuntimeError(
                        f"Yahoo download failed for {ticker} {interval} "
                        f"{chunk_start.date()} -> {chunk_end.date()}: {exc}"
                    ) from exc

    merged = _merge_frames([cached, *downloaded])

    if not merged.empty:
        _write_cache(path, merged)

    # Slice after merge so the cache can contain broader history.
    data = merged.copy()
    if not data.empty:
        idx = pd.DatetimeIndex(data.index)
        idx_naive = idx.tz_localize(None) if idx.tz is not None else idx
        mask = (
            (idx_naive >= effective_start)
            & (idx_naive < end_ts + pd.Timedelta(days=1))
        )
        data = data.loc[mask]

    available_start = None
    available_end = None
    if not data.empty:
        idx = pd.DatetimeIndex(data.index)
        idx_naive = idx.tz_localize(None) if idx.tz is not None else idx
        available_start = pd.Timestamp(idx_naive.min())
        available_end = pd.Timestamp(idx_naive.max())

    return LoadResult(
        ticker=ticker,
        interval=interval,
        data=data,
        cache_path=path,
        requested_start=requested_start,
        requested_end=requested_end,
        available_start=available_start,
        available_end=available_end,
        from_cache_only=(len(jobs) == 0),
        clipped_by_provider_limit=clipped,
    )


def load_many_yfinance_cached(
    tickers: Iterable[str],
    start,
    end,
    *,
    interval: str = "1d",
    cache_root: str | Path = DEFAULT_CACHE_ROOT,
    refresh: bool = False,
    strict_history: bool = True,
    ticker_workers: int = 4,
    chunk_workers_per_ticker: int = 2,
    auto_adjust: bool = False,
    prepost: bool = False,
) -> dict[str, LoadResult]:
    """
    Load many tickers concurrently.

    Concurrency is intentionally bounded at two levels:
    - ticker_workers: parallel symbols
    - chunk_workers_per_ticker: parallel date chunks per symbol

    Keep these modest to reduce Yahoo throttling.
    """
    names = list(dict.fromkeys(str(t).upper() for t in tickers))
    if not names:
        return {}

    results: dict[str, LoadResult] = {}
    worker_count = max(1, min(int(ticker_workers), len(names)))

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {
            pool.submit(
                load_yfinance_cached,
                ticker,
                start,
                end,
                interval=interval,
                cache_root=cache_root,
                refresh=refresh,
                strict_history=strict_history,
                max_workers=chunk_workers_per_ticker,
                auto_adjust=auto_adjust,
                prepost=prepost,
            ): ticker
            for ticker in names
        }

        for future in as_completed(futures):
            ticker = futures[future]
            results[ticker] = future.result()

    return results


def download_data_yfinace_prepare_csv_cache(
    tickers: Iterable[str],
    start,
    end,
    *,
    interval: str = "60m",
    cache_root: str | Path = DEFAULT_CACHE_ROOT,
    refresh: bool = False,
    strict_history: bool = False,
    ticker_workers: int = 4,
    chunk_workers_per_ticker: int = 2,
    auto_adjust: bool = False,
    prepost: bool = False,
) -> dict[str, LoadResult]:
    """
    User-facing universal Yahoo loader for backtesting.

    Typical use
    -----------
    results = download_data_yfinace_prepare_csv_cache(
        tickers=["LRCX", "MU", "AMAT", "INTC", "PLTR", "XOM"],
        start="2025-10-02",
        end="2026-10-02",
        interval="60m",
    )

    Behaviour
    ---------
    - accepts multiple tickers;
    - downloads tickers concurrently;
    - splits each ticker's request into safe date chunks;
    - downloads chunks concurrently;
    - reads existing per-ticker CSV cache first;
    - downloads only leading/trailing missing ranges unless refresh=True;
    - merges, sorts and de-duplicates returned bars;
    - saves the merged data back to CSV;
    - returns a dict[ticker, LoadResult].

    Notes
    -----
    strict_history defaults to False for this convenience method. If the
    requested intraday start is older than Yahoo currently serves, the loader
    clips the provider request to Yahoo's supported window and sets
    result.clipped_by_provider_limit=True. Existing older cached data is never
    deleted by this behaviour.

    Re-running other date ranges is safe: new returned data is merged into the
    same ticker/interval CSV cache.
    """
    results = load_many_yfinance_cached(
        tickers=tickers,
        start=start,
        end=end,
        interval=interval,
        cache_root=cache_root,
        refresh=refresh,
        strict_history=strict_history,
        ticker_workers=ticker_workers,
        chunk_workers_per_ticker=chunk_workers_per_ticker,
        auto_adjust=auto_adjust,
        prepost=prepost,
    )

    print("\n" + "=" * 112)
    print(
        f"YFINANCE CSV CACHE | interval={_normalize_interval(interval)} | "
        f"requested={_as_day(start).date()} -> {_as_day(end).date()}"
    )
    print("=" * 112)

    for ticker in [str(t).upper() for t in tickers]:
        result = results.get(ticker)
        if result is None:
            continue

        actual_start = (
            str(result.available_start)
            if result.available_start is not None
            else "NO DATA"
        )
        actual_end = (
            str(result.available_end)
            if result.available_end is not None
            else "NO DATA"
        )
        source = "CACHE" if result.from_cache_only else "DOWNLOADED+MERGED"
        clipped = " | PROVIDER_LIMIT_CLIPPED" if result.clipped_by_provider_limit else ""

        print(
            f"{ticker:7s} | rows={len(result.data):7d} | "
            f"{actual_start} -> {actual_end} | {source}{clipped}"
        )
        print(f"         CSV: {result.cache_path}")

    print("=" * 112)
    return results


def dataframes_from_results(
    results: dict[str, LoadResult],
) -> dict[str, pd.DataFrame]:
    """Convenience helper for strategy code."""
    return {ticker: result.data for ticker, result in results.items()}


if __name__ == "__main__":
    # Small smoke example: cache one year of 60m data for the six BB names.
    names = ["LRCX", "MU", "AMAT", "INTC", "PLTR", "XOM"]

    loaded = load_many_yfinance_cached(
        names,
        start=(pd.Timestamp.today() - pd.Timedelta(days=365)).strftime("%Y-%m-%d"),
        end=pd.Timestamp.today().strftime("%Y-%m-%d"),
        interval="60m",
        ticker_workers=3,
        chunk_workers_per_ticker=2,
    )

    for ticker, result in loaded.items():
        print(
            ticker,
            len(result.data),
            result.available_start,
            result.available_end,
            result.cache_path,
            "CACHE" if result.from_cache_only else "DOWNLOADED",
        )
