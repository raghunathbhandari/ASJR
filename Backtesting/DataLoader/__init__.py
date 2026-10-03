"""Universal data-loading helpers for ASJR backtesting."""

from .universal_yfinance_loader import (
    DEFAULT_CACHE_ROOT,
    INTERVAL_LIMIT_DAYS,
    LoadResult,
    ProviderHistoryLimitError,
    cache_path_for,
    dataframes_from_results,
    download_data_yfinace_prepare_csv_cache,
    load_many_yfinance_cached,
    load_yfinance_cached,
    provider_earliest_start,
)

__all__ = [
    "DEFAULT_CACHE_ROOT",
    "INTERVAL_LIMIT_DAYS",
    "LoadResult",
    "ProviderHistoryLimitError",
    "cache_path_for",
    "dataframes_from_results",
    "download_data_yfinace_prepare_csv_cache",
    "load_many_yfinance_cached",
    "load_yfinance_cached",
    "provider_earliest_start",
]


from .ibkr_historical_loader import (
    IBKR_BAR_SIZE,
    IBKR_CHUNK_DURATION,
    download_data_ibkr_prepare_csv_cache,
    get_ibkr_ohlcv_df,
    read_ibkr_cache,
)

__all__ += [
    "IBKR_BAR_SIZE",
    "IBKR_CHUNK_DURATION",
    "download_data_ibkr_prepare_csv_cache",
    "get_ibkr_ohlcv_df",
    "read_ibkr_cache",
]
