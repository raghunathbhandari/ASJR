print("Thank you Cornor and AI !")

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import mplfinance as mpf


DEFAULT_TICKERS = ["SPY", "QQQ", "NVDA", "AMD", "AAPL", "MSFT", "META", "AMZN", "TSLA"]


def make_config(
    pullback_lookback=4,
    pullback_tolerance_pct=0.15,
    entry_wait_bars=3,
    future_bars=40,
    cooldown_bars=8,
    require_bullish_candle=True,
    require_bearish_candle=True,
    regime_confirm_bars=3,
    max_signals_per_episode=2,
):
    return {
        "pullback_lookback": pullback_lookback,
        "pullback_tolerance_pct": pullback_tolerance_pct,
        "entry_wait_bars": entry_wait_bars,
        "future_bars": future_bars,
        "cooldown_bars": cooldown_bars,
        "require_bullish_candle": require_bullish_candle,
        "require_bearish_candle": require_bearish_candle,
        "regime_confirm_bars": regime_confirm_bars,
        "max_signals_per_episode": max_signals_per_episode,
    }


def get_5m(ticker, period="30d"):
    df = yf.download(
        ticker,
        period=period,
        interval="5m",
        auto_adjust=False,
        progress=False,
        prepost=False,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    wanted = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in df.columns for c in wanted):
        return pd.DataFrame()

    df = df[wanted].copy()

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    df.index = df.index.tz_convert("America/New_York")
    df = df.between_time("09:30", "16:00", inclusive="left")

    return df.dropna()


def add_sr_indicators(df):
    d = df.copy()

    d["EMA9"] = d["Close"].ewm(span=9, adjust=False).mean()
    d["EMA20"] = d["Close"].ewm(span=20, adjust=False).mean()

    typical = (d["High"] + d["Low"] + d["Close"]) / 3.0
    session = pd.Series(d.index.date, index=d.index)
    pv = typical * d["Volume"]

    d["VWAP"] = (
        pv.groupby(session).cumsum()
        / d["Volume"].groupby(session).cumsum().replace(0, np.nan)
    )

    d["EMA9_SlopePct"] = d["EMA9"].pct_change(3) * 100
    d["EMA20_SlopePct"] = d["EMA20"].pct_change(3) * 100
    d["VWAP_DistancePct"] = ((d["Close"] / d["VWAP"]) - 1) * 100
    d["BodyPct"] = (abs(d["Close"] - d["Open"]) / d["Open"]) * 100
    d["RangePct"] = ((d["High"] - d["Low"]) / d["Open"]) * 100
    d["VolumeMA20"] = d["Volume"].rolling(20).mean()
    d["RVOL20"] = d["Volume"] / d["VolumeMA20"]

    return d


def _future_diagnostics(d, entry_pos, entry_price, side, future_bars):
    future = d.iloc[entry_pos:min(len(d), entry_pos + future_bars + 1)]

    max_high = float(future["High"].max())
    min_low = float(future["Low"].min())

    if side == "LONG":
        mfe = ((max_high / entry_price) - 1) * 100
        mae = max(0.0, ((entry_price - min_low) / entry_price) * 100)
    else:
        mfe = ((entry_price - min_low) / entry_price) * 100
        mae = max(0.0, ((max_high - entry_price) / entry_price) * 100)

    return round(mfe, 3), round(mae, 3)


def detect_small_repeatable_signals(df, ticker="", cfg=None):
    if cfg is None:
        cfg = make_config()

    d = add_sr_indicators(df).dropna().copy()
    signals = []

    pb_n = cfg["pullback_lookback"]
    tolerance = cfg["pullback_tolerance_pct"] / 100.0
    entry_wait = cfg["entry_wait_bars"]
    future_bars = cfg["future_bars"]
    cooldown = cfg["cooldown_bars"]
    regime_confirm_bars = cfg["regime_confirm_bars"]
    max_signals_per_episode = cfg["max_signals_per_episode"]

    last_long = -9999
    last_short = -9999

    active_regime = None
    regime_candidate = None
    regime_candidate_count = 0
    episode_signal_count = 0
    episode_number = 0
    current_day = None

    for i in range(max(25, pb_n + 2), len(d) - entry_wait - 1):
        current = d.iloc[i]
        previous = d.iloc[i - 1]
        day = d.index[i].date()

        if current_day != day:
            current_day = day
            active_regime = None
            regime_candidate = None
            regime_candidate_count = 0
            episode_signal_count = 0

        if current["Close"] > current["VWAP"] and current["EMA9"] > current["EMA20"]:
            raw_regime = "LONG"
        elif current["Close"] < current["VWAP"] and current["EMA9"] < current["EMA20"]:
            raw_regime = "SHORT"
        else:
            raw_regime = "NEUTRAL"

        if raw_regime in ("LONG", "SHORT"):
            if raw_regime == regime_candidate:
                regime_candidate_count += 1
            else:
                regime_candidate = raw_regime
                regime_candidate_count = 1

            if (
                regime_candidate_count >= regime_confirm_bars
                and active_regime != regime_candidate
            ):
                active_regime = regime_candidate
                episode_signal_count = 0
                episode_number += 1
        else:
            regime_candidate = None
            regime_candidate_count = 0

        pb_start = max(0, i - pb_n + 1)
        pb = d.iloc[pb_start:i + 1]
        pb = pb[pd.Series(pb.index.date, index=pb.index) == day]

        if len(pb) < 2:
            continue

        # ========================= LONG =========================
        long_trend = raw_regime == "LONG" and active_regime == "LONG"
        long_pullback = bool(
            (
                pb["Low"]
                <= pb[["EMA9", "EMA20"]].max(axis=1) * (1 + tolerance)
            ).any()
        )
        long_structure_hold = bool((pb["Close"] >= pb["VWAP"] * 0.997).all())
        bullish_candle = current["Close"] > current["Open"]
        long_confirmation = current["Close"] > previous["High"]
        long_episode_available = episode_signal_count < max_signals_per_episode

        if (
            long_trend
            and long_pullback
            and long_structure_hold
            and long_confirmation
            and long_episode_available
            and (bullish_candle or not cfg["require_bullish_candle"])
            and (i - last_long >= cooldown)
        ):
            trigger = float(current["High"])
            pullback_low = float(pb["Low"].min())
            entry_pos = None

            for j in range(i + 1, min(len(d), i + 1 + entry_wait)):
                if d.index[j].date() != day:
                    break
                if float(d.iloc[j]["High"]) > trigger:
                    entry_pos = j
                    break

            if entry_pos is not None:
                mfe, mae = _future_diagnostics(
                    d, entry_pos, trigger, "LONG", future_bars
                )
                risk_pct = ((trigger - pullback_low) / trigger) * 100
                episode_signal_count += 1

                signals.append({
                    "Ticker": ticker,
                    "Side": "LONG",
                    "Episode": episode_number,
                    "EpisodeSignal": episode_signal_count,
                    "PullbackTime": pb["Low"].idxmin(),
                    "ConfirmationTime": d.index[i],
                    "EntryTime": d.index[entry_pos],
                    "Entry": round(trigger, 4),
                    "SL": round(pullback_low, 4),
                    "RiskPct": round(risk_pct, 3),
                    "VWAP": round(float(current["VWAP"]), 4),
                    "VWAPDistancePct": round(float(current["VWAP_DistancePct"]), 3),
                    "EMA9": round(float(current["EMA9"]), 4),
                    "EMA20": round(float(current["EMA20"]), 4),
                    "EMA9SlopePct": round(float(current["EMA9_SlopePct"]), 3),
                    "EMA20SlopePct": round(float(current["EMA20_SlopePct"]), 3),
                    "BodyPct": round(float(current["BodyPct"]), 3),
                    "RangePct": round(float(current["RangePct"]), 3),
                    "RVOL": round(float(current["RVOL20"]), 2),
                    "MFE_Pct": mfe,
                    "MAE_Pct": mae,
                })
                last_long = i

        # ========================= SHORT ========================
        short_trend = raw_regime == "SHORT" and active_regime == "SHORT"
        short_pullback = bool(
            (
                pb["High"]
                >= pb[["EMA9", "EMA20"]].min(axis=1) * (1 - tolerance)
            ).any()
        )
        short_structure_hold = bool((pb["Close"] <= pb["VWAP"] * 1.003).all())
        bearish_candle = current["Close"] < current["Open"]
        short_confirmation = current["Close"] < previous["Low"]
        short_episode_available = episode_signal_count < max_signals_per_episode

        if (
            short_trend
            and short_pullback
            and short_structure_hold
            and short_confirmation
            and short_episode_available
            and (bearish_candle or not cfg["require_bearish_candle"])
            and (i - last_short >= cooldown)
        ):
            trigger = float(current["Low"])
            pullback_high = float(pb["High"].max())
            entry_pos = None

            for j in range(i + 1, min(len(d), i + 1 + entry_wait)):
                if d.index[j].date() != day:
                    break
                if float(d.iloc[j]["Low"]) < trigger:
                    entry_pos = j
                    break

            if entry_pos is not None:
                mfe, mae = _future_diagnostics(
                    d, entry_pos, trigger, "SHORT", future_bars
                )
                risk_pct = ((pullback_high - trigger) / trigger) * 100
                episode_signal_count += 1

                signals.append({
                    "Ticker": ticker,
                    "Side": "SHORT",
                    "Episode": episode_number,
                    "EpisodeSignal": episode_signal_count,
                    "PullbackTime": pb["High"].idxmax(),
                    "ConfirmationTime": d.index[i],
                    "EntryTime": d.index[entry_pos],
                    "Entry": round(trigger, 4),
                    "SL": round(pullback_high, 4),
                    "RiskPct": round(risk_pct, 3),
                    "VWAP": round(float(current["VWAP"]), 4),
                    "VWAPDistancePct": round(float(current["VWAP_DistancePct"]), 3),
                    "EMA9": round(float(current["EMA9"]), 4),
                    "EMA20": round(float(current["EMA20"]), 4),
                    "EMA9SlopePct": round(float(current["EMA9_SlopePct"]), 3),
                    "EMA20SlopePct": round(float(current["EMA20_SlopePct"]), 3),
                    "BodyPct": round(float(current["BodyPct"]), 3),
                    "RangePct": round(float(current["RangePct"]), 3),
                    "RVOL": round(float(current["RVOL20"]), 2),
                    "MFE_Pct": mfe,
                    "MAE_Pct": mae,
                })
                last_short = i

    return pd.DataFrame(signals)


def print_small_repeatable_signals(signals):
    if signals is None or signals.empty:
        print("No Small Repeatable signals.")
        return

    for _, s in signals.iterrows():
        print("\n" + "=" * 72)
        print(
            f"{s['Ticker']} | {s['Side']} | "
            f"Episode {int(s['Episode'])} | Signal #{int(s['EpisodeSignal'])}"
        )
        print("=" * 72)
        print(f"Pullback     : {s['PullbackTime']}")
        print(f"Confirmation : {s['ConfirmationTime']}")
        print(f"Entry Break  : {s['EntryTime']}")
        print("\nStructure:")
        print(f"Entry        : {s['Entry']:.2f}")
        print(f"SL Reference : {s['SL']:.2f}")
        print(f"Risk         : {s['RiskPct']:.2f}%")
        print("\nTrend Diagnostics:")
        print(f"VWAP Dist    : {s['VWAPDistancePct']:+.2f}%")
        print(f"EMA9 Slope   : {s['EMA9SlopePct']:+.3f}%")
        print(f"EMA20 Slope  : {s['EMA20SlopePct']:+.3f}%")
        print(f"Body         : {s['BodyPct']:.2f}%")
        print(f"Range        : {s['RangePct']:.2f}%")
        print(f"RVOL         : {s['RVOL']:.2f}")
        print("\nAfter Signal:")
        print(f"MFE          : +{s['MFE_Pct']:.2f}%")
        print(f"MAE          : {s['MAE_Pct']:.2f}%")


def plot_small_repeatable_signals(
    df,
    signals,
    ticker,
    bars_before=20,
    bars_after=40,
    max_plots=12,
):
    if signals is None or signals.empty:
        print(f"{ticker}: no signals to plot.")
        return

    d = add_sr_indicators(df).dropna()

    x = (
        signals[signals["Ticker"] == ticker]
        .sort_values("EntryTime")
        .tail(max_plots)
    )

    if x.empty:
        print(f"{ticker}: no signals.")
        return

    n = len(x)
    cols = 2
    rows = int(np.ceil(n / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(18, 5 * rows))
    axes = np.array(axes).reshape(-1)

    for ax_i, (_, s) in enumerate(x.iterrows()):
        ax = axes[ax_i]

        pb_time = pd.Timestamp(s["PullbackTime"])
        confirm_time = pd.Timestamp(s["ConfirmationTime"])
        entry_time = pd.Timestamp(s["EntryTime"])

        pb_pos = d.index.get_indexer([pb_time], method="nearest")[0]
        confirm_pos = d.index.get_indexer([confirm_time], method="nearest")[0]
        entry_pos = d.index.get_indexer([entry_time], method="nearest")[0]

        start = max(0, pb_pos - bars_before)
        end = min(len(d), entry_pos + bars_after + 1)
        p = d.iloc[start:end].copy()

        mpf.plot(
            p,
            type="candle",
            ax=ax,
            style="yahoo",
            volume=False,
            show_nontrading=False,
        )

        xx = np.arange(len(p))
        ax.plot(xx, p["VWAP"].values, linewidth=1.2, label="VWAP")
        ax.plot(xx, p["EMA9"].values, linewidth=1.0, label="EMA9")
        ax.plot(xx, p["EMA20"].values, linewidth=1.0, label="EMA20")

        pb_local = pb_pos - start
        confirm_local = confirm_pos - start
        entry_local = entry_pos - start

        ax.axvline(pb_local, linestyle=":", linewidth=1)
        ax.text(pb_local, ax.get_ylim()[1], " PULLBACK", rotation=90, va="top", fontsize=8)

        ax.axvline(confirm_local, linestyle=":", linewidth=1)
        ax.text(confirm_local, ax.get_ylim()[1], " CONFIRM", rotation=90, va="top", fontsize=8)

        entry = float(s["Entry"])
        sl = float(s["SL"])
        marker = "^" if s["Side"] == "LONG" else "v"

        ax.scatter(entry_local, entry, marker=marker, s=120, zorder=5)
        ax.text(entry_local, entry, f" {s['Side']}", fontsize=8)

        ax.axhline(entry, linestyle="--", linewidth=1.0, label=f"ENTRY {entry:.2f}")
        ax.axhline(sl, linestyle="--", linewidth=1.0, label=f"SL REF {sl:.2f}")

        ax.set_title(
            (
                f"{ticker} | {s['Side']} | Ep {int(s['Episode'])} "
                f"#{int(s['EpisodeSignal'])} | {entry_time.strftime('%m-%d %H:%M')}"
                f"\nRisk {s['RiskPct']:.2f}% | MFE +{s['MFE_Pct']:.2f}% | "
                f"MAE {s['MAE_Pct']:.2f}% | RVOL {s['RVOL']:.2f}"
            ),
            fontsize=10,
        )

        ax.legend(fontsize=7, loc="upper left")
        ax.grid(True, alpha=0.20)

    for i in range(n, len(axes)):
        axes[i].axis("off")

    fig.suptitle(f"ASJR SMALL REPEATABLE V1 — {ticker}", fontsize=15)
    plt.tight_layout()
    plt.show()


def test_small_repeatable(
    ticker,
    period="30d",
    cfg=None,
    print_signals=True,
    plot=True,
    bars_before=20,
    bars_after=40,
    max_plots=12,
):
    if cfg is None:
        cfg = make_config()

    print(f"\nTesting {ticker} ...")

    df = get_5m(ticker, period=period)

    if df.empty:
        print(ticker, "NO DATA")
        return pd.DataFrame()

    signals = detect_small_repeatable_signals(df=df, ticker=ticker, cfg=cfg)

    print(f"{ticker}: {len(signals)} signals")

    if print_signals:
        print_small_repeatable_signals(signals)

    if plot and not signals.empty:
        plot_small_repeatable_signals(
            df=df,
            signals=signals,
            ticker=ticker,
            bars_before=bars_before,
            bars_after=bars_after,
            max_plots=max_plots,
        )

    return signals


def test_small_repeatable_batch(
    tickers=DEFAULT_TICKERS,
    period="30d",
    cfg=None,
    plot=False,
):
    if cfg is None:
        cfg = make_config()

    all_signals = []

    print("\n" + "=" * 80)
    print("ASJR SMALL REPEATABLE V1")
    print("DETECT -> PRINT -> ANALYSE -> PLOT")
    print("=" * 80)

    for ticker in tickers:
        try:
            signals = test_small_repeatable(
                ticker=ticker,
                period=period,
                cfg=cfg,
                print_signals=True,
                plot=plot,
            )

            if not signals.empty:
                all_signals.append(signals)

        except Exception as e:
            print(ticker, "ERROR:", e)

    if not all_signals:
        return pd.DataFrame()

    result = pd.concat(all_signals, ignore_index=True)

    print("\n" + "=" * 80)
    print("SIGNAL SUMMARY")
    print("=" * 80)
    print(result.groupby(["Ticker", "Side"]).size().unstack(fill_value=0))
    print("\nTOTAL SIGNALS:", len(result))

    return result
