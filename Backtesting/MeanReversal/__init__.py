"""Mean-reversal backtesting package.

Pure Bollinger Mean Reversion is separate from the ASJR -4% shock strategy.
"""

from .bb_mean_reversal_backtest import BacktestConfig, run_backtest, run_batch

__all__ = ["BacktestConfig", "run_backtest", "run_batch"]
