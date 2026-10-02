"""
Pure Bollinger Band Mean Reversion backtest.

This strategy is intentionally separate from the ASJR -4% shock strategy.

Default rules
-------------
- Data: Yahoo Finance 60m bars, aggregated into 4H-style regular-session candles.
- Bollinger Bands: 20-period SMA +/- 2 standard deviations.
- BUY setup: 4H close <= lower Bollinger Band.
- BUY trigger: first later 4H close back above the lower Bollinger Band.
- Stop loss: 1%.
- Target: 3.5%.
- If SL and TP are both touched in the same 4H bar, assume SL first.

The public function run_backtest(...) is intended to remain stable so the
VS Code notebook cell does not need to change when strategy internals evolve.
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
    stop_pct: float = 1.0
    target_pct: float = 3.5
    max_entry_wait_4h_bars: int = 6
    conservative_same_bar_exit: bool = True


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
    Pure BUY-only Bollinger mean reversion.

    Setup: candle closes at/below lower BB.
    Entry: first later candle that closes back above lower BB.
    """
    if bars_4h.empty:
        return pd.DataFrame()

    start_ts = _as_timestamp(start)
    end_ts = _as_timestamp(end) + pd.Timedelta(days=1)

    naive_index = bars_4h.index
    if naive_index.tz is not None:
        naive_index = naive_index.tz_convert("America/New_York").tz_localize(None)

    in_test = (naive_index >= start_ts) & (naive_index < end_ts)

    trades = []
    last_exit_loc = -1
    i = max(config.bb_window - 1, 1)

    while i < len(bars_4h):
        if i <= last_exit_loc or not in_test[i]:
            i += 1
            continue

        setup_bar = bars_4h.iloc[i]
        if pd.isna(setup_bar["BB_LOWER"]) or setup_bar["Close"] > setup_bar["BB_LOWER"]:
            i += 1
            continue

        setup_time = bars_4h.index[i]
        entry_loc = None
        max_j = min(len(bars_4h), i + 1 + config.max_entry_wait_4h_bars)

        for j in range(i + 1, max_j):
            bar = bars_4h.iloc[j]
            if pd.notna(bar["BB_LOWER"]) and bar["Close"] > bar["BB_LOWER"]:
                entry_loc = j
                break

        if entry_loc is None:
            i += 1
            continue

        entry_bar = bars_4h.iloc[entry_loc]
        entry_time = bars_4h.index[entry_loc]
        entry_price = float(entry_bar["Close"])
        stop_price = entry_price * (1 - config.stop_pct / 100.0)
        target_price = entry_price * (1 + config.target_pct / 100.0)

        exit_loc = None
        exit_time = None
        exit_price = None
        exit_reason = None

        for j in range(entry_loc + 1, len(bars_4h)):
            bar = bars_4h.iloc[j]
            hit_stop = float(bar["Low"]) <= stop_price
            hit_target = float(bar["High"]) >= target_price

            if hit_stop and hit_target:
                exit_reason = "SL" if config.conservative_same_bar_exit else "TP"
                exit_price = stop_price if exit_reason == "SL" else target_price
                exit_loc = j
                exit_time = bars_4h.index[j]
                break
            if hit_stop:
                exit_reason = "SL"
                exit_price = stop_price
                exit_loc = j
                exit_time = bars_4h.index[j]
                break
            if hit_target:
                exit_reason = "TP"
                exit_price = target_price
                exit_loc = j
                exit_time = bars_4h.index[j]
                break

        if exit_loc is None:
            exit_loc = len(bars_4h) - 1
            exit_time = bars_4h.index[exit_loc]
            exit_price = float(bars_4h.iloc[exit_loc]["Close"])
            exit_reason = "DATA_END"

        trades.append(
            {
                "setup_time": setup_time,
                "setup_close": float(setup_bar["Close"]),
                "setup_bb_lower": float(setup_bar["BB_LOWER"]),
                "setup_bb_z": float(setup_bar["BB_Z"]) if pd.notna(setup_bar["BB_Z"]) else np.nan,
                "entry_time": entry_time,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "target_price": target_price,
                "exit_time": exit_time,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "return_pct": (exit_price / entry_price - 1.0) * 100.0,
                "bars_held": int(exit_loc - entry_loc),
            }
        )

        last_exit_loc = exit_loc
        i = exit_loc + 1

    return pd.DataFrame(trades)


def summarize_trades(trades: pd.DataFrame) -> dict:
    if trades is None or trades.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "avg_return_pct": 0.0,
            "median_return_pct": 0.0,
            "compounded_return_pct": 0.0,
            "profit_factor": 0.0,
            "max_trade_equity_drawdown_pct": 0.0,
            "avg_bars_held": 0.0,
        }

    rets = trades["return_pct"].astype(float)
    tp = trades["exit_reason"].eq("TP")
    sl = trades["exit_reason"].eq("SL")

    equity = (1.0 + rets / 100.0).cumprod()
    drawdown = (equity / equity.cummax() - 1.0) * 100.0

    gross_profit = rets[rets > 0].sum()
    gross_loss = abs(rets[rets < 0].sum())

    return {
        "trades": int(len(trades)),
        "wins": int(tp.sum()),
        "losses": int(sl.sum()),
        "data_end": int(trades["exit_reason"].eq("DATA_END").sum()),
        "win_rate_pct": float(tp.mean() * 100.0),
        "avg_return_pct": float(rets.mean()),
        "median_return_pct": float(rets.median()),
        "best_trade_pct": float(rets.max()),
        "worst_trade_pct": float(rets.min()),
        "compounded_return_pct": float((equity.iloc[-1] - 1.0) * 100.0),
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        "max_trade_equity_drawdown_pct": float(drawdown.min()),
        "avg_bars_held": float(trades["bars_held"].mean()),
    }


def print_summary(ticker: str, start, end, config: BacktestConfig, trades: pd.DataFrame) -> dict:
    summary = summarize_trades(trades)
    print("=" * 72)
    print(f"PURE BB MEAN REVERSION | {ticker.upper()} | {start} -> {end}")
    print(
        f"BB({config.bb_window},{config.bb_std}) | "
        f"SL {config.stop_pct:.2f}% | TP {config.target_pct:.2f}%"
    )
    print("-" * 72)
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key:36s}: {value:10.2f}")
        else:
            print(f"{key:36s}: {value}")
    print("=" * 72)

    if trades is not None and not trades.empty:
        cols = [
            "setup_time", "setup_close", "setup_bb_z",
            "entry_time", "entry_price",
            "exit_time", "exit_price", "exit_reason",
            "return_pct", "bars_held",
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

    addplots = [
        mpf.make_addplot(plot_df["BB_UPPER"]),
        mpf.make_addplot(plot_df["BB_MID"]),
        mpf.make_addplot(plot_df["BB_LOWER"]),
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
            if xt in sell.index:
                sell.loc[xt] = float(trade["exit_price"])

        if buy.notna().any():
            addplots.append(mpf.make_addplot(buy, type="scatter", marker="^", markersize=100))
        if sell.notna().any():
            addplots.append(mpf.make_addplot(sell, type="scatter", marker="v", markersize=100))

    fig, _ = mpf.plot(
        plot_df,
        type="candle",
        volume=True,
        addplot=addplots,
        title=f"{ticker.upper()} 4H | Pure Bollinger Mean Reversion",
        ylabel="Price",
        ylabel_lower="Volume",
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
    stop_pct: float = 1.0,
    target_pct: float = 3.5,
    max_entry_wait_4h_bars: int = 6,
    plot: bool = True,
    save_chart: Optional[str | Path] = None,
    save_trades_csv: Optional[str | Path] = None,
) -> dict:
    config = BacktestConfig(
        bb_window=bb_window,
        bb_std=bb_std,
        stop_pct=stop_pct,
        target_pct=target_pct,
        max_entry_wait_4h_bars=max_entry_wait_4h_bars,
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


def run_batch(tickers: Iterable[str], start, end, **kwargs) -> pd.DataFrame:
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
