"""Mean-reversal backtesting package.

Two separate Bollinger Mean Reversion methods are exposed:
1. run_backtest / run_batch = plain BB Mean Reversion
2. run_backtest_adx / run_batch_adx = BB Mean Reversion + ADX filter
"""

from .bb_mean_reversal_backtest import (
    BacktestConfig,
    run_backtest,
    run_batch,
    load_cached_60m_csv,
    run_backtest_from_csv,
    run_batch_from_csv,
)
from .bb_mean_reversal_adx_backtest import (
    ADXBacktestConfig,
    DEFAULT_14_TICKERS,
    run_backtest_adx,
    run_batch_adx,
    compare_plain_vs_adx,
)

__all__ = [
    "BacktestConfig",
    "ADXBacktestConfig",
    "DEFAULT_14_TICKERS",
    "run_backtest",
    "run_batch",
    "load_cached_60m_csv",
    "run_backtest_from_csv",
    "run_batch_from_csv",
    "run_backtest_adx",
    "run_batch_adx",
    "compare_plain_vs_adx",
]
