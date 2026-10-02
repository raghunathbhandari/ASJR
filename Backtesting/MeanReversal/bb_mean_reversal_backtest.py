"""
Pure Bollinger Band Mean Reversion backtest.

This strategy is intentionally separate from the ASJR -4% shock strategy.

Default rules
-------------
- Data: Yahoo Finance 60m bars, aggregated into 4H-style regular-session candles.
- Bollinger Bands: 20-period SMA +/- 2 standard deviations.
- BUY: enter long when a completed 4H candle CLOSES BELOW the lower band.
  A wick below the lower band is NOT enough.
- EXIT: close the long position when a later completed 4H candle
  CLOSES ABOVE the upper band.
- BUY only.
- No -4% shock condition.
- No fixed stop-loss or fixed take-profit in this TradingView-style version.

The public function run_backtest(...) stays stable so the VS Code notebook
cell does not need to change when strategy internals evolve.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    bb_window: int = 20
    bb_std: float = 2.0


def _as_timestamp(value: str | date | datetime) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts.normalize()


def _normalize_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        wanted = {"Open", "High", "Low", "Close", "Volume"}
        lvl0 = set(map(str, out.columns.get_level_values(0)))
        out.columns = (
            out.columns.get_level_values(0)
            if wanted.intersection(lvl0)
            else out.columns.get_level_values(-1)
        )

    rename = {str(c).strip().title(): c for c in out.columns}
    selected = {}
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in rename:
            selected[col] = out[rename[col]]

    result = pd.DataFrame(selected, index=out.index)
    result = result.dropna(subset=["Open", "High", "Low", "Close"])
    if "Volume" not in result:
        result["Volume"] = 0.0
    return result.sort_index()


def download_hourly(
    ticker: str,
    start: str | date | datetime,
    end: str | date | datetime,
    warmup_calendar_days: int = 90,
) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError(
            "Install dependencies: pip install yfinance pandas numpy matplotlib mplfinance"
        ) from exc

    start_ts = _as_timestamp(start)
    end_ts = _as_timestamp(end)
    if end_ts < start_ts:
        raise ValueError("end must be on or after start")

    fetch_start = start_ts - pd.Timedelta(days=warmup_calendar_days)
    fetch_end = end_ts + pd.Timedelta(days=1)

    hourly = _normalize_yf_columns(
        yf.download(
            tickers=ticker.upper(),
            start=fetch_start.strftime("%Y-%m-%d"),
            end=fetch_end.strftime("%Y-%m-%d"),
            interval="60m",
            auto_adjust=False,
            progress=False,
            threads=False,
            prepost=False,
        )
    )

    if hourly.empty:
        raise RuntimeError(
            f"No Yahoo 60m data returned for {ticker}. "
            "Yahoo intraday history limits may restrict the requested period."
        )
    return hourly


def build_4h_candles(hourly: pd.DataFrame) -> pd.DataFrame:
    """Aggregate regular US-session 60m bars into 4H-style candles."""
    if hourly.empty:
        return hourly.copy()

    df = hourly.copy()
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is None:
        idx = idx.tz_localize("America/New_York")
    else:
        idx = idx.tz_convert("America/New_York")
    df.index = idx

    start_t = pd.Timestamp("09:30").time()
    end_t = pd.Timestamp("16:00").time()
    mask = [(t >= start_t and t < end_t) for t in df.index.time]
    df = df.loc[mask]

    pieces = []
    for _, day_df in df.groupby(df.index.date):
        day_df = day_df.sort_index()
        if day_df.empty:
            continue

        bucket = np.arange(len(day_df)) // 4
        grouped = day_df.groupby(bucket)
        agg = grouped.agg(
            Open=("Open", "first"),
            High=("High", "max"),
            Low=("Low", "min"),
            Close=("Close", "last"),
            Volume=("Volume", "sum"),
        )
        agg.index = pd.DatetimeIndex(grouped.apply(lambda x: x.index[0]).values)
        pieces.append(agg)

    if not pieces:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    out = pd.concat(pieces).sort_index()
    out.index.name = "Datetime"
    return out


def add_bollinger_bands(
    bars_4h: pd.DataFrame,
    window: int = 20,
    std_mult: float = 2.0,
) -> pd.DataFrame:
    out = bars_4h.copy()
    out["BB_MID"] = out["Close"].rolling(window, min_periods=window).mean()
    sigma = out["Close"].rolling(window, min_periods=window).std(ddof=0)
    out["BB_UPPER"] = out["BB_MID"] + std_mult * sigma
    out["BB_LOWER"] = out["BB_MID"] - std_mult * sigma
    out["BB_Z"] = (out["Close"] - out["BB_MID"]) / sigma.replace(0, np.nan)
    return out


def backtest_mean_reversal(
    bars_4h: pd.DataFrame,
    start,
    end,
    config: BacktestConfig,
) -> pd.DataFrame:
    """
    BUY-only Bollinger mean reversion.

    Entry:
        completed 4H candle close < lower BB
    Exit:
        later completed 4H candle close > upper BB

    One long position at a time.
    """
    if bars_4h.empty:
        return pd.DataFrame()

    start_ts = _as_timestamp(start)
    end_ts = _as_timestamp(end) + pd.Timedelta(days=1)

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

    for i in range(max(config.bb_window - 1, 1), len(bars_4h)):
        if naive_idx[i] < start_ts or naive_idx[i] >= end_ts:
            continue

        bar = bars_4h.iloc[i]
        if pd.isna(bar["BB_LOWER"]) or pd.isna(bar["BB_UPPER"]):
            continue

        if not in_position:
            # IMPORTANT: CLOSE must be below lower band; wick-only breaks do not qualify.
            if float(bar["Close"]) < float(bar["BB_LOWER"]):
                in_position = True
                entry_loc = i
                entry_time = bars_4h.index[i]
                entry_price = float(bar["Close"])
                entry_bb_lower = float(bar["BB_LOWER"])
                entry_bb_z = float(bar["BB_Z"]) if pd.notna(bar["BB_Z"]) else np.nan
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
                    "exit_time": exit_time,
                    "exit_price": exit_price,
                    "exit_bb_upper": float(bar["BB_UPPER"]),
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

    # Keep unfinished final trade visible for analysis, but mark it separately.
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
                "exit_time": last_time,
                "exit_price": last_price,
                "exit_bb_upper": float(bars_4h.iloc[last_loc]["BB_UPPER"])
                if pd.notna(bars_4h.iloc[last_loc]["BB_UPPER"])
                else np.nan,
                "exit_reason": "DATA_END",
                "return_pct": (last_price / entry_price - 1.0) * 100.0,
                "bars_held": int(last_loc - entry_loc),
            }
        )

    return pd.DataFrame(trades)


def summarize_trades(trades: pd.DataFrame) -> dict:
    if trades is None or trades.empty:
        return {
            "trades": 0,
            "closed_upper_bb": 0,
            "data_end": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "avg_return_pct": 0.0,
            "median_return_pct": 0.0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "compounded_return_pct": 0.0,
            "profit_factor": 0.0,
            "max_trade_equity_drawdown_pct": 0.0,
            "avg_bars_held": 0.0,
        }

    closed = trades[trades["exit_reason"] == "UPPER_BB_CLOSE"].copy()
    closed_rets = closed["return_pct"].astype(float)

    # Compounding includes only completed upper-band exits.
    if closed.empty:
        compounded = 0.0
        max_dd = 0.0
    else:
        equity = (1.0 + closed_rets / 100.0).cumprod()
        compounded = float((equity.iloc[-1] - 1.0) * 100.0)
        max_dd = float((equity / equity.cummax() - 1.0).min() * 100.0)

    wins = closed_rets[closed_rets > 0]
    losses = closed_rets[closed_rets <= 0]
    gross_profit = float(wins.sum())
    gross_loss = float(abs(losses.sum()))

    return {
        "trades": int(len(trades)),
        "closed_upper_bb": int(len(closed)),
        "data_end": int(trades["exit_reason"].eq("DATA_END").sum()),
        "wins": int((closed_rets > 0).sum()),
        "losses": int((closed_rets <= 0).sum()),
        "win_rate_pct": float((closed_rets > 0).mean() * 100.0) if len(closed_rets) else 0.0,
        "avg_return_pct": float(closed_rets.mean()) if len(closed_rets) else 0.0,
        "median_return_pct": float(closed_rets.median()) if len(closed_rets) else 0.0,
        "best_trade_pct": float(closed_rets.max()) if len(closed_rets) else 0.0,
        "worst_trade_pct": float(closed_rets.min()) if len(closed_rets) else 0.0,
        "compounded_return_pct": compounded,
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        "max_trade_equity_drawdown_pct": max_dd,
        "avg_bars_held": float(closed["bars_held"].mean()) if len(closed) else 0.0,
    }


def print_summary(
    ticker: str,
    start,
    end,
    config: BacktestConfig,
    trades: pd.DataFrame,
) -> dict:
    summary = summarize_trades(trades)

    print("=" * 80)
    print(f"PURE BB MEAN REVERSION | {ticker.upper()} | {start} -> {end}")
    print(
        f"BB({config.bb_window},{config.bb_std}) | "
        "BUY: close < Lower BB | EXIT: close > Upper BB"
    )
    print("-" * 80)

    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key:36s}: {value:10.2f}")
        else:
            print(f"{key:36s}: {value}")

    print("=" * 80)

    if trades is not None and not trades.empty:
        cols = [
            "entry_time",
            "entry_price",
            "entry_bb_lower",
            "entry_bb_z",
            "exit_time",
            "exit_price",
            "exit_bb_upper",
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
    try:
        import mplfinance as mpf
    except ImportError as exc:
        raise ImportError("Install mplfinance: pip install mplfinance matplotlib") from exc

    start_ts = _as_timestamp(start)
    end_ts = _as_timestamp(end) + pd.Timedelta(days=1)

    plot_df = bars_4h.copy()
    idx = plot_df.index
    if idx.tz is not None:
        idx = idx.tz_convert("America/New_York").tz_localize(None)
    plot_df.index = idx
    plot_df = plot_df[(plot_df.index >= start_ts) & (plot_df.index < end_ts)]

    if plot_df.empty:
        print("No 4H bars available in requested plotting range.")
        return None

    addplots = [
        mpf.make_addplot(plot_df["BB_UPPER"], width=0.8),
        mpf.make_addplot(plot_df["BB_MID"], width=0.8),
        mpf.make_addplot(plot_df["BB_LOWER"], width=0.8),
    ]

    if trades is not None and not trades.empty:
        buy = pd.Series(np.nan, index=plot_df.index)
        sell = pd.Series(np.nan, index=plot_df.index)

        for _, trade in trades.iterrows():
            et = pd.Timestamp(trade["entry_time"])
            xt = pd.Timestamp(trade["exit_time"])

            if et.tzinfo is not None:
                et = et.tz_convert("America/New_York").tz_localize(None)
            if xt.tzinfo is not None:
                xt = xt.tz_convert("America/New_York").tz_localize(None)

            if et in buy.index:
                buy.loc[et] = float(trade["entry_price"])

            if trade["exit_reason"] == "UPPER_BB_CLOSE" and xt in sell.index:
                sell.loc[xt] = float(trade["exit_price"])

        if buy.notna().any():
            addplots.append(
                mpf.make_addplot(
                    buy,
                    type="scatter",
                    marker="^",
                    markersize=120,
                )
            )

        if sell.notna().any():
            addplots.append(
                mpf.make_addplot(
                    sell,
                    type="scatter",
                    marker="v",
                    markersize=120,
                )
            )

    fig, _ = mpf.plot(
        plot_df,
        type="candle",
        volume=True,
        addplot=addplots,
        title=f"{ticker.upper()} 4H | Pure Bollinger Mean Reversion",
        ylabel="Price",
        ylabel_lower="Volume",
        figsize=(28, 12),
        xrotation=20,
        tight_layout=True,
        warn_too_much_data=5000,
        returnfig=True,
    )

    if save_path:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"Saved chart: {path}")

    if show:
        import matplotlib.pyplot as plt
        plt.show()

    return fig


def run_backtest(
    ticker: str,
    start,
    end,
    *,
    bb_window: int = 20,
    bb_std: float = 2.0,
    stop_pct: Optional[float] = None,
    target_pct: Optional[float] = None,
    max_entry_wait_4h_bars: Optional[int] = None,
    plot: bool = True,
    save_chart: Optional[str | Path] = None,
    save_trades_csv: Optional[str | Path] = None,
) -> dict:
    """
    Stable notebook entry point.

    stop_pct, target_pct and max_entry_wait_4h_bars are accepted only for
    backward compatibility with the earlier notebook cell. They are ignored
    by the current pure BB strategy.
    """
    config = BacktestConfig(
        bb_window=bb_window,
        bb_std=bb_std,
    )

    hourly = download_hourly(ticker, start, end)
    bars_4h = add_bollinger_bands(
        build_4h_candles(hourly),
        window=config.bb_window,
        std_mult=config.bb_std,
    )

    trades = backtest_mean_reversal(bars_4h, start, end, config)
    summary = print_summary(ticker, start, end, config, trades)

    if save_trades_csv:
        csv_path = Path(save_trades_csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        trades.to_csv(csv_path, index=False)
        print(f"Saved trades: {csv_path}")

    if plot:
        plot_candles_with_trades(
            ticker,
            bars_4h,
            trades,
            start,
            end,
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


def run_batch(
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
            result = run_backtest(ticker, start, end, **local_kwargs)
            rows.append({"ticker": ticker.upper(), **result["summary"]})
        except Exception as exc:
            rows.append({"ticker": ticker.upper(), "error": str(exc)})

    summary_df = pd.DataFrame(rows)
    print("\nBATCH SUMMARY")
    print(summary_df.to_string(index=False))
    return summary_df


if __name__ == "__main__":
    run_backtest(
        ticker="INTC",
        start=(pd.Timestamp.today() - pd.Timedelta(days=365)).strftime("%Y-%m-%d"),
        end=pd.Timestamp.today().strftime("%Y-%m-%d"),
        plot=True,
    )
