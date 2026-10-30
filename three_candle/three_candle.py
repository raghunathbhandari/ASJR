"""Rudra Three-Candle: original RTH sweep/reclaim research.

Notebook API remains:
    test = check_signals("INTC", "2026-10-28", "2026-10-28", r=0.10)
    show_chart(test)

Historical C2-close entry is an EX-POST hypothesis: C3 volume was unavailable
at entry. Target touches do not prove executed wins or realised profit.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd

__version__ = "2.1.0-20261030"
MODEL = "RTH_C2_SWEEP_EXPOST"
print(f"[Rudra Three-Candle] LOADED v{__version__} | MODEL={MODEL}")
COLS = ["Open", "High", "Low", "Close", "Volume"]
TIMEFRAMES = {"5min": 5, "15min": 15, "30min": 30, "1h": 60}


def timeframe_minutes(value: str) -> int:
    aliases = {"5m": "5min", "15m": "15min", "30m": "30min",
               "60m": "1h", "60min": "1h", "1hr": "1h"}
    key = aliases.get(str(value).lower(), str(value).lower())
    if key not in TIMEFRAMES:
        raise ValueError("interval must be 5min, 15min, 30min, or 1h")
    return TIMEFRAMES[key]



@dataclass(frozen=True)
class Signal:
    time: pd.Timestamp
    direction: str
    candle1_time: pd.Timestamp
    candle2_time: pd.Timestamp
    candle3_time: pd.Timestamp
    candle2_high: float
    candle2_low: float
    candle2_open: float
    candle2_close: float
    candle3_volume: float
    candle2_volume: float


def download_data(start: str, end: str, symbol: str = "INTC",
                  interval: str = "5m") -> pd.DataFrame:
    """Get Yahoo 5-minute bars with timezone and volume (retention limited)."""
    import yfinance as yf
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last < first:
        raise ValueError("end before start")
    data = yf.download(
        symbol, start=first.isoformat(),
        end=(last+timedelta(days=1)).isoformat(), interval=interval,
        prepost=True, auto_adjust=False, progress=False, threads=False,
    )
    if data.empty:
        raise ValueError("No Yahoo bars: check date range and 5m retention")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    if data.index.tz is None:
        raise ValueError("Yahoo data lacks timezone")
    return data[COLS].copy()


def resample_rth_5m(raw: pd.DataFrame, start: str, end: str,
                    symbol: str = "INTC", interval: str = "15min") -> pd.DataFrame:
    """Completed US RTH bars from 5m, anchored at 09:30 ET for any supported timeframe."""
    if raw.index.tz is None:
        raise ValueError("Input timestamps must be timezone-aware")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last < first:
        raise ValueError("end before start")
    minutes = timeframe_minutes(interval)
    group_size = minutes // 5
    data = raw[COLS].apply(pd.to_numeric, errors="coerce").dropna().sort_index()
    data.index = data.index.tz_convert("America/New_York")
    data = data.loc[(pd.Index(data.index.date) >= first) &
                    (pd.Index(data.index.date) <= last)]
    data = data.between_time("09:30", "15:59")
    sessions = []
    for day_date, day in data.groupby(data.index.date):
        offset = day.index.hour*60 + day.index.minute - 570
        day = day.loc[offset % 5 == 0]
        bucket = (day.index.hour*60 + day.index.minute - 570)//minutes
        grouped = day.groupby(bucket)
        count = grouped.size()
        bars = grouped.agg({"Open":"first", "High":"max", "Low":"min",
                            "Close":"last", "Volume":"sum"}).loc[count[count==group_size].index]
        if bars.empty:
            continue
        session_open = pd.Timestamp(day_date, tz="America/New_York") + pd.Timedelta(hours=9, minutes=30)
        bars.index = pd.DatetimeIndex([
            session_open + pd.Timedelta(minutes=int(b)*minutes) for b in bars.index
        ])
        sessions.append(bars)
    if not sessions:
        raise ValueError(f"No complete RTH {interval} candles")
    result = pd.concat(sessions)
    result.index = result.index.tz_convert("Europe/London")
    result.attrs.update({"symbol":symbol, "model":MODEL, "interval_minutes":minutes})
    return result


def load_historical_5m(path: str, start: str, end: str,
                       interval: str = "15min") -> pd.DataFrame:
    raw = pd.read_csv(path)
    time_col = "Datetime" if "Datetime" in raw else "datetime_source"
    if time_col not in raw:
        raise ValueError("Expected Datetime or datetime_source CSV column")
    raw.index = pd.DatetimeIndex(pd.to_datetime(raw[time_col], utc=True))
    return resample_rth_5m(raw, start, end, Path(path).name.split("_")[0].split(".")[0], interval)


def historical_three_candle(c1: pd.Series, c2: pd.Series,
                            c3: pd.Series) -> bool:
    """Green C2, lower-wick sweep/reclaim C1 low; strong-volume bullish C3."""
    body = float(c2.Close - c2.Open)
    return (body > 0 and float(c2.Open-c2.Low) > body
            and float(c2.Low) < float(c1.Low)
            and float(c2.Close) > float(c1.Low)
            and pd.notna(c2.Volume) and pd.notna(c3.Volume)
            and float(c2.Volume) > 0 and float(c3.Volume) > float(c2.Volume)
            and float(c3.Close) > float(c2.Close))


def find_historical_signals(data: pd.DataFrame):
    """Never join pattern candles across two US trading sessions."""
    for _, day in data.groupby(data.index.tz_convert("America/New_York").date):
        for i in range(2, len(day)):
            c1, c2, c3 = day.iloc[i-2], day.iloc[i-1], day.iloc[i]
            if not historical_three_candle(c1, c2, c3):
                continue
            yield Signal(
                day.index[i], "LONG", day.index[i-2], day.index[i-1], day.index[i],
                float(c2.High), float(c2.Low), float(c2.Open), float(c2.Close),
                float(c3.Volume), float(c2.Volume),
            )


def historical_target_touches(signals: list[Signal], data: pd.DataFrame,
                              r_pct: float = 0.10) -> tuple[int, int, int]:
    """Same-session future highs from C3; stop ordering is deliberately ignored."""
    if r_pct <= 0:
        raise ValueError("r must be positive")
    ny_dates = data.index.tz_convert("America/New_York").date
    hits = [0, 0, 0]
    for signal in signals:
        entry = signal.candle2_close
        step = max(entry-signal.candle2_open, entry*r_pct/100)
        day = signal.time.tz_convert("America/New_York").date()
        later = data.loc[(ny_dates == day) & (data.index >= signal.candle3_time)]
        if later.empty:
            continue
        high = float(later.High.max())
        for k in (1, 2, 3):
            hits[k-1] += int(high >= entry+k*step)
    return tuple(hits)


def historical_potential_gains(signals: list[Signal], data: pd.DataFrame,
                               r_pct: float = 0.10) -> tuple[float, float, float]:
    """Sum target-hit gross price returns per hypothetical equal-sized trade.

    NOT realised profit: stop order, C3 look-ahead, overlap, fees and slippage
    are all ignored. Each kR column is a separate fixed-target scenario.
    """
    if r_pct <= 0:
        raise ValueError("r must be positive")
    dates = data.index.tz_convert("America/New_York").date
    gains = [0.0, 0.0, 0.0]
    for signal in signals:
        entry = signal.candle2_close
        step = max(entry-signal.candle2_open, entry*r_pct/100)
        day = signal.time.tz_convert("America/New_York").date()
        later = data.loc[(dates == day) & (data.index >= signal.candle3_time)]
        if later.empty:
            continue
        peak = float(later.High.max())
        for k in (1, 2, 3):
            if peak >= entry+k*step:
                gains[k-1] += 100*k*step/entry
    return tuple(gains)


def check_signals(ticker: str = "INTC", *args: str, r: float = 0.10,
                  start: str | None = None, end: str | None = None,
                  interval: str = "15min", target_r: int = 1,
                  require_breakout: bool = False,
                  source_csv: str | None = None) -> dict:
    """Supports both (ticker,start,end) and (ticker,interval,start,end).\n\n    Historical scanner; not an execution backtest.

    target_r/require_breakout remain accepted for older cells but do not
    change the archived fixed pattern, which is a separate research model.
    """
    if len(args) == 2:
        start, end = args
    elif len(args) == 3:
        interval, start, end = args
    elif len(args) != 0:
        raise TypeError("Use check_signals(ticker, start, end) or (ticker, interval, start, end)")
    if start is None or end is None:
        raise TypeError("start and end dates are required")
    minutes = timeframe_minutes(interval)
    interval_label = f"{minutes}min" if minutes < 60 else "1h"
    print(f"[Rudra Three-Candle] v{__version__} | MODEL={MODEL} | TIMEFRAME={interval_label}")
    data = (load_historical_5m(source_csv, start, end, interval_label) if source_csv else
            resample_rth_5m(download_data(start, end, ticker), start, end, ticker, interval_label))
    signals = list(find_historical_signals(data))
    hits = historical_target_touches(signals, data, r)
    gains = historical_potential_gains(signals, data, r)
    total = len(signals)
    print(f"\n{ticker} | {start} to {end} | {len(data)} RTH {interval_label} candles")
    print("=== RUDRA THREE-CANDLE SUMMARY (ex-post price touches) ===")
    print(f"{'Metric':<24} {'Count':>8} {'Rate':>9} {'Gain %':>12}")
    print(f"{'Qualifying signals':<24} {total:>8} {'100%' if total else 'N/A':>9} {'—':>12}")
    for k, count in enumerate(hits, 1):
        rate = f"{count/total*100:.1f}%" if total else "N/A"
        print(f"{str(k)+'R price touches':<24} {count:>8} {rate:>9} {gains[k-1]:>11.2f}%")
    print("Gain % = sum of hypothetical gross target-hit returns at each R; NOT realized P&L.")
    print("Executed win rate: NOT DETERMINED (C3 look-ahead / intrabar order).")
    print("\n=== SIGNAL DETAILS (CANDLE 2 ONLY) ===")
    if not signals:
        print("No qualifying signals.")
    for number, s in enumerate(signals, 1):
        c2 = data.loc[s.candle2_time]
        print(f"\n#{number} LONG | C2 {s.candle2_time:%Y-%m-%d %H:%M %Z} | "
              f"C3 close/confirmation {(s.candle3_time + pd.Timedelta(minutes=minutes)):%H:%M %Z}")
        print(pd.DataFrame([c2], index=[s.candle2_time], columns=COLS).to_string())
        print(f"C2 close hypothesis {s.candle2_close:.4f} | SL {s.candle2_open:.4f} | "
              f"C3/C2 volume {s.candle3_volume/s.candle2_volume:.2f}x")
    return {"data":data, "signals":signals, "results":[],
            "touches":hits, "potential_gains_pct":gains, "model":MODEL, "r_pct":r, "interval":interval_label}


def show_chart(test: dict, signal_number: int | None = None) -> None:
    """C1/C2/C3 charts: hypothesis green, initial SL red, R references purple."""
    signals = test["signals"]
    if signal_number is not None:
        if not 1 <= signal_number <= len(signals):
            raise ValueError(f"signal_number must be 1..{len(signals)}")
        signals = [signals[signal_number-1]]
    data = test["data"]
    ny_dates = data.index.tz_convert("America/New_York").date
    for s in signals:
        idx = data.index.get_loc(s.candle3_time)
        day = s.time.tz_convert("America/New_York").date()
        last = max(i for i in range(idx, len(data)) if ny_dates[i] == day)
        view = data.iloc[max(0, idx-10):last+1]
        fig, (ax, volume) = plt.subplots(
            2, 1, figsize=(13, 6), sharex=True,
            gridspec_kw={"height_ratios":[4,1]},
        )
        for x, (_, bar) in enumerate(view.iterrows()):
            color = "#168650" if bar.Close >= bar.Open else "#c64242"
            ax.vlines(x, bar.Low, bar.High, color=color, linewidth=1.2)
            ax.add_patch(Rectangle((x-.32, min(bar.Open,bar.Close)), .64,
                                   max(abs(bar.Close-bar.Open), .005),
                                   facecolor=color, edgecolor=color))
            volume.bar(x, bar.Volume, color=color, width=.7)
        for name, stamp, color in [
            ("C1",s.candle1_time,"#4c78a8"),
            ("C2",s.candle2_time,"#d9a128"),
            ("C3",s.candle3_time,"#7b58a5"),
        ]:
            if stamp in view.index:
                x = view.index.get_loc(stamp)
                ax.axvspan(x-.45, x+.45, color=color, alpha=.15)
                ax.annotate(name, (x,view.iloc[x].High), xytext=(0,8),
                            textcoords="offset points", ha="center",
                            color=color, weight="bold")
        entry = s.candle2_close
        step = max(entry-s.candle2_open, entry*test.get("r_pct", .10)/100)
        ax.axhline(entry, color="#138a36", linestyle="--",
                   label=f"C2 close hypothesis {entry:.2f}")
        ax.axhline(s.candle2_open, color="#d33232", linestyle=":",
                   label=f"Initial SL {s.candle2_open:.2f}")
        for k in (1,2,3):
            ax.axhline(entry+k*step, color="#853fb7", linestyle="-.", alpha=.55,
                       label=f"{k}R reference {entry+k*step:.2f}")
        ax.set_title(f"{data.attrs.get('symbol','INTC')} | {MODEL} | "
                     f"C3 {s.time:%Y-%m-%d %H:%M %Z} | ex-post, not fills")
        ax.set_ylabel("Price")
        volume.set_ylabel("Volume")
        ticks = list(range(0, len(view), max(1,len(view)//9)))
        volume.set_xticks(ticks, [view.index[i].strftime("%d %b %H:%M") for i in ticks],
                          rotation=35, ha="right")
        ax.legend(loc="best", fontsize=8)
        fig.tight_layout()
        plt.show()
        plt.close(fig)


def historical_report(path: str, start: str, end: str) -> list[Signal]:
    """Compatibility helper for archived reproduction."""
    ticker = Path(path).name.split("_")[0].split(".")[0]
    return check_signals(ticker, start, end, source_csv=path)["signals"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--symbol", default="INTC")
    parser.add_argument("--r-pct", type=float, default=.10)
    parser.add_argument("--historical-csv", default=None)
    parser.add_argument("--no-charts", action="store_true")
    args = parser.parse_args()
    result = check_signals(args.symbol, args.start, args.end,
                           r=args.r_pct, source_csv=args.historical_csv)
    if not args.no_charts:
        show_chart(result)
