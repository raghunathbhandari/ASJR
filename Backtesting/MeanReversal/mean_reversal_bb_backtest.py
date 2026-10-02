"""
ASJR Mean Reversal Bollinger Band backtest.

Strategy, default version
-------------------------
1. Daily shock: daily close-to-close return <= -4%.
2. 4H setup: at least one 4H candle on the shock day closes at/below
   the lower Bollinger Band (20, 2).
3. Entry: BUY only. Starting after the shock-day close, buy on the first
   4H candle that closes back above the lower Bollinger Band after the
   previous 4H candle was at/below its lower band.
4. Stop: 1% below entry.
5. Target: 3.5% above entry.
6. If stop and target are both touched in the same 4H bar, stop is assumed
   first (conservative, because intrabar sequence is unknown).

Yahoo Finance does not provide a native 4H interval. This module downloads
60-minute bars and aggregates regular-session bars into 4H-style candles:
09:30-13:30 ET and the remaining regular-session bars into the second candle.

The public notebook/test call is intentionally small and stable. Strategy
internals can be optimized here without repeatedly changing the notebook.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    shock_pct: float = -4.0
    bb_window: int = 20
    bb_std: float = 2.0
    stop_pct: float = 1.0
    target_pct: float = 3.5
    max_entry_wait_4h_bars: int = 6
    regular_hours_only: bool = True
    conservative_same_bar_exit: bool = True


def _as_timestamp(value: str | date | datetime) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts.normalize()


def _normalize_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance single-ticker output to OHLCV columns."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        # yfinance may return (Price, Ticker) or (Ticker, Price).
        wanted = {"Open", "High", "Low", "Close", "Volume"}
        lvl0 = set(map(str, out.columns.get_level_values(0)))
        if wanted.intersection(lvl0):
            out.columns = out.columns.get_level_values(0)
        else:
            out.columns = out.columns.get_level_values(-1)

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


def download_yfinance_data(
    ticker: str,
    start: str | date | datetime,
    end: str | date | datetime,
    *,
    warmup_calendar_days: int = 90,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Download daily and 60-minute Yahoo Finance data for a date-to-date test.

    Notes
    -----
    - yfinance's end date is exclusive, so one day is added internally.
    - 60-minute data is used because Yahoo does not expose a native 4H bar.
    - Extra warmup history is downloaded for Bollinger calculations.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError(
            "Missing yfinance. Install with: pip install yfinance pandas numpy matplotlib mplfinance"
        ) from exc

    start_ts = _as_timestamp(start)
    end_ts = _as_timestamp(end)
    if end_ts < start_ts:
        raise ValueError("end must be on or after start")

    fetch_start = start_ts - pd.Timedelta(days=warmup_calendar_days)
    fetch_end = end_ts + pd.Timedelta(days=1)

    kwargs = dict(
        tickers=ticker.upper(),
        start=fetch_start.strftime("%Y-%m-%d"),
        end=fetch_end.strftime("%Y-%m-%d"),
        auto_adjust=False,
        progress=False,
        threads=False,
        prepost=False,
    )

    daily = _normalize_yf_columns(yf.download(interval="1d", **kwargs))
    hourly = _normalize_yf_columns(yf.download(interval="60m", **kwargs))

    if daily.empty:
        raise RuntimeError(f"No daily Yahoo Finance data returned for {ticker}")
    if hourly.empty:
        raise RuntimeError(
            f"No 60-minute Yahoo Finance data returned for {ticker}. "
            "Yahoo intraday-history limits or an invalid date range may be the cause."
        )

    return daily, hourly


def build_4h_candles(hourly: pd.DataFrame, regular_hours_only: bool = True) -> pd.DataFrame:
    """
    Aggregate Yahoo 60m bars into regular-session 4H-style candles.

    Each US session is grouped sequentially:
    - first four 60m bars -> first 4H candle
    - remaining regular-session bars -> second partial-session candle
    """
    if hourly.empty:
        return hourly.copy()

    df = hourly.copy()
    idx = pd.DatetimeIndex(df.index)

    if idx.tz is None:
        # Yahoo normally supplies timezone-aware intraday bars. If it does not,
        # interpret them as US/Eastern for deterministic session grouping.
        idx = idx.tz_localize("America/New_York")
    else:
        idx = idx.tz_convert("America/New_York")
    df.index = idx

    if regular_hours_only:
        local_time = df.index.time
        start_t = pd.Timestamp("09:30").time()
        end_t = pd.Timestamp("16:00").time()
        mask = [(t >= start_t and t < end_t) for t in local_time]
        df = df.loc[mask]

    pieces = []
    for session_date, day_df in df.groupby(df.index.date):
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
        first_times = grouped.apply(lambda x: x.index[0])
        agg.index = pd.DatetimeIndex(first_times.values)
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


def add_daily_shock(daily: pd.DataFrame) -> pd.DataFrame:
    out = daily.copy()
    out["DAILY_RETURN_PCT"] = out["Close"].pct_change() * 100.0
    return out


def _session_date_et(index: pd.DatetimeIndex) -> pd.Series:
    idx = index
    if idx.tz is None:
        idx = idx.tz_localize("America/New_York")
    else:
        idx = idx.tz_convert("America/New_York")
    return pd.Series(idx.date, index=index)


def identify_setups(
    daily: pd.DataFrame,
    bars_4h: pd.DataFrame,
    config: BacktestConfig,
) -> pd.DataFrame:
    """
    Return qualifying daily shock dates that also stretched to/below lower BB.
    """
    d = add_daily_shock(daily)
    b = bars_4h.copy()
    b["SESSION_DATE"] = _session_date_et(b.index).values

    shock_rows = d[d["DAILY_RETURN_PCT"] <= config.shock_pct]
    setups = []

    for shock_idx, shock_row in shock_rows.iterrows():
        shock_date = pd.Timestamp(shock_idx).date()
        same_day = b[b["SESSION_DATE"] == shock_date]
        if same_day.empty:
            continue

        stretched = same_day[
            same_day["BB_LOWER"].notna() & (same_day["Close"] <= same_day["BB_LOWER"])
        ]
        if stretched.empty:
            continue

        last_bar = same_day.index.max()
        setups.append(
            {
                "shock_date": pd.Timestamp(shock_date),
                "shock_return_pct": float(shock_row["DAILY_RETURN_PCT"]),
                "shock_close": float(shock_row["Close"]),
                "shock_last_4h_time": last_bar,
                "shock_min_bb_z": float(stretched["BB_Z"].min()),
            }
        )

    return pd.DataFrame(setups)


def backtest_mean_reversal(
    daily: pd.DataFrame,
    bars_4h: pd.DataFrame,
    config: BacktestConfig,
) -> pd.DataFrame:
    """
    Run BUY-only Bollinger mean-reversion trades.

    Entry is deliberately after the shock-day close to avoid look-ahead bias.
    """
    setups = identify_setups(daily, bars_4h, config)
    if setups.empty:
        return pd.DataFrame()

    trades = []
    next_allowed_index = 0

    for _, setup in setups.sort_values("shock_date").iterrows():
        after = bars_4h[bars_4h.index > setup["shock_last_4h_time"]]
        if after.empty:
            continue

        # Prevent overlapping trades/setups.
        after = after.iloc[next_allowed_index:] if next_allowed_index else after

        # Find first lower-band re-entry within configured wait.
        window = after.head(config.max_entry_wait_4h_bars)
        entry_time = None
        entry_price = None

        for current_time in window.index:
            current_loc = bars_4h.index.get_loc(current_time)
            if current_loc <= 0:
                continue
            prev = bars_4h.iloc[current_loc - 1]
            cur = bars_4h.iloc[current_loc]
            if (
                pd.notna(prev["BB_LOWER"])
                and pd.notna(cur["BB_LOWER"])
                and prev["Close"] <= prev["BB_LOWER"]
                and cur["Close"] > cur["BB_LOWER"]
            ):
                entry_time = current_time
                entry_price = float(cur["Close"])
                break

        if entry_time is None:
            continue

        stop_price = entry_price * (1.0 - config.stop_pct / 100.0)
        target_price = entry_price * (1.0 + config.target_pct / 100.0)

        entry_loc = bars_4h.index.get_loc(entry_time)
        exit_time = None
        exit_price = None
        exit_reason = None

        for j in range(entry_loc + 1, len(bars_4h)):
            bar = bars_4h.iloc[j]
            hit_stop = float(bar["Low"]) <= stop_price
            hit_target = float(bar["High"]) >= target_price

            if hit_stop and hit_target:
                if config.conservative_same_bar_exit:
                    exit_reason = "SL"
                    exit_price = stop_price
                else:
                    exit_reason = "TP"
                    exit_price = target_price
                exit_time = bars_4h.index[j]
                break
            if hit_stop:
                exit_reason = "SL"
                exit_price = stop_price
                exit_time = bars_4h.index[j]
                break
            if hit_target:
                exit_reason = "TP"
                exit_price = target_price
                exit_time = bars_4h.index[j]
                break

        if exit_time is None:
            exit_time = bars_4h.index[-1]
            exit_price = float(bars_4h.iloc[-1]["Close"])
            exit_reason = "EOD_DATA"

        return_pct = (exit_price / entry_price - 1.0) * 100.0
        exit_loc = bars_4h.index.get_loc(exit_time)

        trades.append(
            {
                "shock_date": setup["shock_date"],
                "shock_return_pct": setup["shock_return_pct"],
                "shock_min_bb_z": setup["shock_min_bb_z"],
                "entry_time": entry_time,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "target_price": target_price,
                "exit_time": exit_time,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "return_pct": return_pct,
                "bars_held": int(exit_loc - entry_loc),
                "win": bool(exit_reason == "TP"),
            }
        )

        # Skip any shock setups that occur while this trade is open.
        setups = setups[setups["shock_date"] > pd.Timestamp(exit_time).tz_localize(None).normalize()]

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
            "total_compounded_return_pct": 0.0,
            "profit_factor": 0.0,
            "max_trade_equity_drawdown_pct": 0.0,
            "avg_bars_held": 0.0,
        }

    rets = trades["return_pct"].astype(float)
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    equity = (1.0 + rets / 100.0).cumprod()
    peak = equity.cummax()
    dd = (equity / peak - 1.0) * 100.0

    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    return {
        "trades": int(len(trades)),
        "wins": int((trades["exit_reason"] == "TP").sum()),
        "losses": int((trades["exit_reason"] == "SL").sum()),
        "open_data_end": int((trades["exit_reason"] == "EOD_DATA").sum()),
        "win_rate_pct": float((trades["exit_reason"] == "TP").mean() * 100.0),
        "avg_return_pct": float(rets.mean()),
        "median_return_pct": float(rets.median()),
        "best_trade_pct": float(rets.max()),
        "worst_trade_pct": float(rets.min()),
        "total_compounded_return_pct": float((equity.iloc[-1] - 1.0) * 100.0),
        "profit_factor": float(profit_factor),
        "max_trade_equity_drawdown_pct": float(dd.min()),
        "avg_bars_held": float(trades["bars_held"].mean()),
    }


def print_summary(ticker: str, start, end, config: BacktestConfig, trades: pd.DataFrame) -> dict:
    summary = summarize_trades(trades)
    print("=" * 72)
    print(f"ASJR Mean Reversal BB Backtest | {ticker.upper()} | {start} -> {end}")
    print(
        f"Shock <= {config.shock_pct:.2f}% | BB({config.bb_window},{config.bb_std}) "
        f"| SL {config.stop_pct:.2f}% | TP {config.target_pct:.2f}%"
    )
    print("-" * 72)
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key:34s}: {value:10.2f}")
        else:
            print(f"{key:34s}: {value}")
    print("=" * 72)

    if trades is not None and not trades.empty:
        cols = [
            "shock_date",
            "shock_return_pct",
            "shock_min_bb_z",
            "entry_time",
            "entry_price",
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
    try:
        import mplfinance as mpf
    except ImportError as exc:
        raise ImportError(
            "Missing mplfinance. Install with: pip install mplfinance matplotlib"
        ) from exc

    start_ts = _as_timestamp(start)
    end_ts = _as_timestamp(end) + pd.Timedelta(days=1)

    plot_df = bars_4h.copy()
    naive_index = plot_df.index
    if naive_index.tz is not None:
        naive_index = naive_index.tz_convert("America/New_York").tz_localize(None)
    plot_df.index = naive_index
    plot_df = plot_df[(plot_df.index >= start_ts) & (plot_df.index < end_ts)]

    if plot_df.empty:
        print("No 4H bars available in requested plotting range.")
        return

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
            if xt in sell.index:
                sell.loc[xt] = float(trade["exit_price"])

        if buy.notna().any():
            addplots.append(
                mpf.make_addplot(
                    buy, type="scatter", marker="^", markersize=100
                )
            )
        if sell.notna().any():
            addplots.append(
                mpf.make_addplot(
                    sell, type="scatter", marker="v", markersize=100
                )
            )

    kwargs = dict(
        type="candle",
        volume=True,
        addplot=addplots,
        title=f"{ticker.upper()} 4H | -4% Shock + Bollinger Mean Reversal",
        ylabel="Price",
        ylabel_lower="Volume",
        tight_layout=True,
        warn_too_much_data=5000,
        returnfig=True,
    )
    fig, _ = mpf.plot(plot_df, **kwargs)

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
    start: str | date | datetime,
    end: str | date | datetime,
    *,
    shock_pct: float = -4.0,
    bb_window: int = 20,
    bb_std: float = 2.0,
    stop_pct: float = 1.0,
    target_pct: float = 3.5,
    max_entry_wait_4h_bars: int = 6,
    plot: bool = True,
    save_chart: Optional[str | Path] = None,
    save_trades_csv: Optional[str | Path] = None,
) -> dict:
    """
    Stable public entry point intended for the VS Code notebook.

    Returns a dict with daily data, 4H data, trades and summary.
    """
    config = BacktestConfig(
        shock_pct=shock_pct,
        bb_window=bb_window,
        bb_std=bb_std,
        stop_pct=stop_pct,
        target_pct=target_pct,
        max_entry_wait_4h_bars=max_entry_wait_4h_bars,
    )

    daily, hourly = download_yfinance_data(ticker, start, end)
    bars_4h = build_4h_candles(hourly, config.regular_hours_only)
    bars_4h = add_bollinger_bands(bars_4h, config.bb_window, config.bb_std)

    # Backtest may use warmup history, but signals are restricted to requested dates.
    daily_signal = daily.copy()
    daily_idx = pd.DatetimeIndex(daily_signal.index)
    if daily_idx.tz is not None:
        daily_idx = daily_idx.tz_localize(None)
    daily_signal.index = daily_idx
    start_ts = _as_timestamp(start)
    end_ts = _as_timestamp(end)
    warmup_daily = daily_signal[daily_signal.index <= end_ts]

    trades = backtest_mean_reversal(warmup_daily, bars_4h, config)
    if not trades.empty:
        shock_dates = pd.to_datetime(trades["shock_date"]).dt.tz_localize(None)
        trades = trades[(shock_dates >= start_ts) & (shock_dates <= end_ts)].reset_index(drop=True)

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
        "daily": daily_signal,
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
    """Run the same strategy for several tickers and return one summary table."""
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
    # Quick command-line smoke test.
    run_backtest(
        ticker="INTC",
        start=(pd.Timestamp.today() - pd.Timedelta(days=365)).strftime("%Y-%m-%d"),
        end=pd.Timestamp.today().strftime("%Y-%m-%d"),
        plot=True,
    )
