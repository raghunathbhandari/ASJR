"""
Bollinger Band Mean Reversion + ADX filter.

This module is separate from the plain BB strategy.
The plain strategy in bb_mean_reversal_backtest.py is intentionally unchanged.

Rules
-----
- Data: Yahoo Finance 60m bars aggregated into 4H-style candles.
- Bollinger Bands: 20-period SMA +/- 2 standard deviations.
- ADX: Wilder ADX, default period 14.
- BUY: completed 4H candle CLOSES BELOW lower BB AND ADX(14) < threshold.
- EXIT: later completed 4H candle CLOSES ABOVE upper BB.
- BUY only.
- No -4% shock condition.
- No fixed SL/TP in the base ADX version.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from . import bb_mean_reversal_backtest as plain


DEFAULT_14_TICKERS = [
    "MU", "AMAT", "LRCX", "INTC",
    "PLTR", "CRWD", "TSLA", "NKE",
    "JPM", "COIN", "CAT", "UBER",
    "FSLR", "XOM",
]


@dataclass(frozen=True)
class ADXBacktestConfig:
    bb_window: int = 20
    bb_std: float = 2.0
    adx_period: int = 14
    adx_max: float = 25.0


def add_adx(
    bars_4h: pd.DataFrame,
    period: int = 14,
) -> pd.DataFrame:
    """
    Add Wilder-style ADX, +DI and -DI.

    Uses exponential smoothing with alpha=1/period, equivalent to Wilder's
    recursive smoothing after initialization.
    """
    out = bars_4h.copy()

    high = out["High"].astype(float)
    low = out["Low"].astype(float)
    close = out["Close"].astype(float)

    prev_close = close.shift(1)
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=out.index,
        dtype=float,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=out.index,
        dtype=float,
    )

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    alpha = 1.0 / float(period)
    atr = tr.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    plus_smoothed = plus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    minus_smoothed = minus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean()

    plus_di = 100.0 * plus_smoothed / atr.replace(0, np.nan)
    minus_di = 100.0 * minus_smoothed / atr.replace(0, np.nan)

    denom = (plus_di + minus_di).replace(0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / denom
    adx = dx.ewm(alpha=alpha, adjust=False, min_periods=period).mean()

    out["PLUS_DI"] = plus_di
    out["MINUS_DI"] = minus_di
    out["ADX"] = adx
    return out


def backtest_mean_reversal_adx(
    bars_4h: pd.DataFrame,
    start,
    end,
    config: ADXBacktestConfig,
) -> pd.DataFrame:
    """
    BB Mean Reversion with ADX regime filter.

    Entry:
        Close < Lower BB
        AND ADX < adx_max

    Exit:
        Later Close > Upper BB
    """
    if bars_4h.empty:
        return pd.DataFrame()

    start_ts = plain._as_timestamp(start)
    end_ts = plain._as_timestamp(end) + pd.Timedelta(days=1)

    idx = bars_4h.index
    if idx.tz is not None:
        naive_idx = idx.tz_convert("America/New_York").tz_localize(None)
    else:
        naive_idx = idx

    trades = []
    in_position = False

    entry_loc = None
    entry_time = None
    entry_price = None
    entry_bb_lower = None
    entry_bb_z = None
    entry_adx = None

    first_valid = max(config.bb_window - 1, config.adx_period * 2 - 1, 1)

    for i in range(first_valid, len(bars_4h)):
        if naive_idx[i] < start_ts or naive_idx[i] >= end_ts:
            continue

        bar = bars_4h.iloc[i]

        if (
            pd.isna(bar["BB_LOWER"])
            or pd.isna(bar["BB_UPPER"])
            or pd.isna(bar["ADX"])
        ):
            continue

        if not in_position:
            if (
                float(bar["Close"]) < float(bar["BB_LOWER"])
                and float(bar["ADX"]) < float(config.adx_max)
            ):
                in_position = True
                entry_loc = i
                entry_time = bars_4h.index[i]
                entry_price = float(bar["Close"])
                entry_bb_lower = float(bar["BB_LOWER"])
                entry_bb_z = float(bar["BB_Z"]) if pd.notna(bar["BB_Z"]) else np.nan
                entry_adx = float(bar["ADX"])
            continue

        if float(bar["Close"]) > float(bar["BB_UPPER"]):
            exit_loc = i
            exit_time = bars_4h.index[i]
            exit_price = float(bar["Close"])

            trades.append(
                {
                    "entry_time": entry_time,
                    "entry_price": entry_price,
                    "entry_bb_lower": entry_bb_lower,
                    "entry_bb_z": entry_bb_z,
                    "entry_adx": entry_adx,
                    "exit_time": exit_time,
                    "exit_price": exit_price,
                    "exit_bb_upper": float(bar["BB_UPPER"]),
                    "exit_adx": float(bar["ADX"]) if pd.notna(bar["ADX"]) else np.nan,
                    "exit_reason": "UPPER_BB_CLOSE",
                    "return_pct": (exit_price / entry_price - 1.0) * 100.0,
                    "bars_held": int(exit_loc - entry_loc),
                }
            )

            in_position = False
            entry_loc = None
            entry_time = None
            entry_price = None
            entry_bb_lower = None
            entry_bb_z = None
            entry_adx = None

    if in_position and entry_time is not None:
        last_loc = len(bars_4h) - 1
        last_time = bars_4h.index[last_loc]
        last_price = float(bars_4h.iloc[last_loc]["Close"])

        trades.append(
            {
                "entry_time": entry_time,
                "entry_price": entry_price,
                "entry_bb_lower": entry_bb_lower,
                "entry_bb_z": entry_bb_z,
                "entry_adx": entry_adx,
                "exit_time": last_time,
                "exit_price": last_price,
                "exit_bb_upper": float(bars_4h.iloc[last_loc]["BB_UPPER"])
                if pd.notna(bars_4h.iloc[last_loc]["BB_UPPER"])
                else np.nan,
                "exit_adx": float(bars_4h.iloc[last_loc]["ADX"])
                if pd.notna(bars_4h.iloc[last_loc]["ADX"])
                else np.nan,
                "exit_reason": "DATA_END",
                "return_pct": (last_price / entry_price - 1.0) * 100.0,
                "bars_held": int(last_loc - entry_loc),
            }
        )

    return pd.DataFrame(trades)


def summarize_trades(trades: pd.DataFrame) -> dict:
    return plain.summarize_trades(trades)


def print_summary(
    ticker: str,
    start,
    end,
    config: ADXBacktestConfig,
    trades: pd.DataFrame,
) -> dict:
    summary = summarize_trades(trades)

    print("=" * 84)
    print(f"BB MEAN REVERSION + ADX | {ticker.upper()} | {start} -> {end}")
    print(
        f"BB({config.bb_window},{config.bb_std}) | "
        f"ADX({config.adx_period}) < {config.adx_max:g} | "
        "BUY: close < Lower BB | EXIT: close > Upper BB"
    )
    print("-" * 84)

    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key:36s}: {value:10.2f}")
        else:
            print(f"{key:36s}: {value}")

    print("=" * 84)

    if trades is not None and not trades.empty:
        cols = [
            "entry_time",
            "entry_price",
            "entry_bb_lower",
            "entry_bb_z",
            "entry_adx",
            "exit_time",
            "exit_price",
            "exit_reason",
            "return_pct",
            "bars_held",
        ]
        print(trades[cols].to_string(index=False))

    return summary


def plot_candles_with_trades(
    ticker: str,
    bars_4h: pd.DataFrame,
    trades: pd.DataFrame,
    start,
    end,
    *,
    save_path: Optional[str | Path] = None,
    show: bool = True,
):
    """
    Reuse the same large candlestick/Bollinger chart as the plain method.
    Buy/sell markers reflect ADX-filtered trades only.
    """
    return plain.plot_candles_with_trades(
        ticker=ticker,
        bars_4h=bars_4h,
        trades=trades,
        start=start,
        end=end,
        save_path=save_path,
        show=show,
    )


def run_backtest_adx(
    ticker: str,
    start,
    end,
    *,
    bb_window: int = 20,
    bb_std: float = 2.0,
    adx_period: int = 14,
    adx_max: float = 25.0,
    plot: bool = True,
    save_chart: Optional[str | Path] = None,
    save_trades_csv: Optional[str | Path] = None,
) -> dict:
    config = ADXBacktestConfig(
        bb_window=bb_window,
        bb_std=bb_std,
        adx_period=adx_period,
        adx_max=adx_max,
    )

    hourly = plain.download_hourly(ticker, start, end)
    bars_4h = plain.build_4h_candles(hourly)
    bars_4h = plain.add_bollinger_bands(
        bars_4h,
        window=config.bb_window,
        std_mult=config.bb_std,
    )
    bars_4h = add_adx(
        bars_4h,
        period=config.adx_period,
    )

    trades = backtest_mean_reversal_adx(
        bars_4h,
        start=start,
        end=end,
        config=config,
    )
    summary = print_summary(
        ticker=ticker,
        start=start,
        end=end,
        config=config,
        trades=trades,
    )

    if save_trades_csv:
        csv_path = Path(save_trades_csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        trades.to_csv(csv_path, index=False)
        print(f"Saved trades: {csv_path}")

    if plot:
        plot_candles_with_trades(
            ticker=ticker,
            bars_4h=bars_4h,
            trades=trades,
            start=start,
            end=end,
            save_path=save_chart,
            show=True,
        )

    return {
        "ticker": ticker.upper(),
        "config": config,
        "bars_4h": bars_4h,
        "trades": trades,
        "summary": summary,
    }


def run_batch_adx(
    tickers: Iterable[str],
    start,
    end,
    **kwargs,
) -> pd.DataFrame:
    rows = []
    local_kwargs = dict(kwargs)
    local_kwargs["plot"] = False

    for ticker in tickers:
        try:
            result = run_backtest_adx(
                ticker=ticker,
                start=start,
                end=end,
                **local_kwargs,
            )
            rows.append(
                {
                    "ticker": ticker.upper(),
                    **result["summary"],
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "ticker": ticker.upper(),
                    "error": str(exc),
                }
            )

    summary_df = pd.DataFrame(rows)
    print("\nBB + ADX BATCH SUMMARY")
    print(summary_df.to_string(index=False))
    return summary_df


def compare_plain_vs_adx(
    tickers: Iterable[str] = DEFAULT_14_TICKERS,
    start=None,
    end=None,
    *,
    bb_window: int = 20,
    bb_std: float = 2.0,
    adx_period: int = 14,
    adx_max: float = 25.0,
) -> pd.DataFrame:
    """
    Run both strategies on the same ticker/date universe and return
    a side-by-side comparison.
    """
    if start is None or end is None:
        raise ValueError("start and end are required")

    rows = []

    for ticker in tickers:
        row = {"ticker": ticker.upper()}

        try:
            plain_result = plain.run_backtest(
                ticker=ticker,
                start=start,
                end=end,
                bb_window=bb_window,
                bb_std=bb_std,
                plot=False,
            )
            ps = plain_result["summary"]
            row.update(
                {
                    "plain_trades": ps.get("closed_upper_bb", 0),
                    "plain_win_rate_pct": ps.get("win_rate_pct", 0.0),
                    "plain_avg_return_pct": ps.get("avg_return_pct", 0.0),
                    "plain_compounded_return_pct": ps.get("compounded_return_pct", 0.0),
                    "plain_max_drawdown_pct": ps.get("max_trade_equity_drawdown_pct", 0.0),
                    "plain_profit_factor": ps.get("profit_factor", 0.0),
                }
            )
        except Exception as exc:
            row["plain_error"] = str(exc)

        try:
            adx_result = run_backtest_adx(
                ticker=ticker,
                start=start,
                end=end,
                bb_window=bb_window,
                bb_std=bb_std,
                adx_period=adx_period,
                adx_max=adx_max,
                plot=False,
            )
            ads = adx_result["summary"]
            row.update(
                {
                    "adx_trades": ads.get("closed_upper_bb", 0),
                    "adx_win_rate_pct": ads.get("win_rate_pct", 0.0),
                    "adx_avg_return_pct": ads.get("avg_return_pct", 0.0),
                    "adx_compounded_return_pct": ads.get("compounded_return_pct", 0.0),
                    "adx_max_drawdown_pct": ads.get("max_trade_equity_drawdown_pct", 0.0),
                    "adx_profit_factor": ads.get("profit_factor", 0.0),
                }
            )
        except Exception as exc:
            row["adx_error"] = str(exc)

        if (
            "plain_compounded_return_pct" in row
            and "adx_compounded_return_pct" in row
        ):
            row["adx_minus_plain_return_pct"] = (
                row["adx_compounded_return_pct"]
                - row["plain_compounded_return_pct"]
            )

        rows.append(row)

    result = pd.DataFrame(rows)

    preferred = [
        "ticker",
        "plain_trades",
        "adx_trades",
        "plain_win_rate_pct",
        "adx_win_rate_pct",
        "plain_compounded_return_pct",
        "adx_compounded_return_pct",
        "adx_minus_plain_return_pct",
        "plain_max_drawdown_pct",
        "adx_max_drawdown_pct",
        "plain_profit_factor",
        "adx_profit_factor",
        "plain_avg_return_pct",
        "adx_avg_return_pct",
    ]
    cols = [c for c in preferred if c in result.columns] + [
        c for c in result.columns if c not in preferred
    ]
    result = result[cols]

    print("\nPLAIN BB vs BB + ADX COMPARISON")
    print(result.to_string(index=False))
    return result


if __name__ == "__main__":
    compare_plain_vs_adx(
        tickers=DEFAULT_14_TICKERS,
        start=(pd.Timestamp.today() - pd.Timedelta(days=365)).strftime("%Y-%m-%d"),
        end=pd.Timestamp.today().strftime("%Y-%m-%d"),
    )
