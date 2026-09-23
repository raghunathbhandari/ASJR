print("Thank you  Everyone !")

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

    try:
        df = df.between_time("09:30", "16:00", inclusive="left")
    except TypeError:
        df = df.between_time("09:30", "16:00", include_start=True, include_end=False)

    return df.dropna()



def get_5m_range(ticker, start_date, end_date):
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date) + pd.Timedelta(days=1)  # make end_date inclusive

    df = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
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
    if not all(col in df.columns for col in wanted):
        return pd.DataFrame()

    df = df[wanted].copy()

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    df.index = df.index.tz_convert("America/New_York")

    try:
        df = df.between_time("09:30", "16:00", inclusive="left")
    except TypeError:
        df = df.between_time("09:30", "16:00", include_start=True, include_end=False)

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



def test_small_repeatable_range(
    ticker,
    start_date,
    end_date,
    cfg=None,
    print_signals=True,
    plot=True,
    bars_before=20,
    bars_after=40,
    max_plots=12,
):
    if cfg is None:
        cfg = make_config()

    print(f"\nTesting {ticker} | {start_date} -> {end_date}")

    df = get_5m_range(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
    )

    if df.empty:
        print(ticker, "NO DATA")
        return pd.DataFrame()

    print(f"Rows : {len(df)}")
    print(f"From : {df.index.min()}")
    print(f"To   : {df.index.max()}")

    signals = detect_small_repeatable_signals(
        df=df,
        ticker=ticker,
        cfg=cfg,
    )

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


def test_small_repeatable_range_summary(
    ticker,
    start_date,
    end_date,
    cfg=None,
    rr_targets=(1.0, 1.5, 2.0),
    max_hold_bars=40,
    sl_multiplier=1.0,
    max_sl_pct=None,
    fixed_sl_pct=None,
    use_sl=True,
    print_signals=False,
    plot=False,
    max_plots=12,
):
    if cfg is None:
        cfg = make_config()

    print(f"\nTesting {ticker} | {start_date} -> {end_date}")

    df = get_5m_range(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
    )

    if df.empty:
        print(ticker, "NO DATA")
        return pd.DataFrame(), pd.DataFrame(), {}

    print(f"Rows : {len(df)}")
    print(f"From : {df.index.min()}")
    print(f"To   : {df.index.max()}")

    signals = detect_small_repeatable_signals(
        df=df,
        ticker=ticker,
        cfg=cfg,
    )

    print(f"Signals: {len(signals)}")

    if print_signals:
        print_small_repeatable_signals(signals)

    if plot and not signals.empty:
        plot_small_repeatable_signals(
            df=df,
            signals=signals,
            ticker=ticker,
            max_plots=max_plots,
        )

    rr_summary, rr_trades = compare_rr_targets(
        df=df,
        signals=signals,
        rr_targets=rr_targets,
        max_hold_bars=max_hold_bars,
        sl_multiplier=sl_multiplier,
        max_sl_pct=max_sl_pct,
        fixed_sl_pct=fixed_sl_pct,
        use_sl=use_sl,
        print_trades=False,
    )

    print("\nRR RESULT SUMMARY")
    print(rr_summary.to_string(index=False))

    return signals, rr_summary, rr_trades

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


def evaluate_rr_backtest(
    df,
    signals,
    rr=1.5,
    max_hold_bars=40,
    sl_multiplier=1.0,
    max_sl_pct=None,
    fixed_sl_pct=None,
    use_sl=True,
):
    if signals is None or signals.empty:
        return pd.DataFrame()

    d = df.copy()
    trades = []

    for _, s in signals.sort_values("EntryTime").iterrows():
        entry_time = pd.Timestamp(s["EntryTime"])
        if entry_time not in d.index:
            continue

        side = s["Side"]
        entry = float(s["Entry"])
        base_sl = float(s["SL"])
        base_risk = abs(entry - base_sl)

        if base_risk <= 0:
            continue

        if fixed_sl_pct is not None:
            risk = entry * (float(fixed_sl_pct) / 100.0)
        else:
            risk = base_risk * float(sl_multiplier)
            if max_sl_pct is not None:
                risk = min(risk, entry * (float(max_sl_pct) / 100.0))

        if risk <= 0:
            continue

        sl = entry - risk if side == "LONG" else entry + risk
        tp = entry + (risk * rr) if side == "LONG" else entry - (risk * rr)

        entry_pos = d.index.get_loc(entry_time)
        day = entry_time.date()

        exit_time = entry_time
        exit_price = entry
        exit_reason = "TIME"
        r_result = 0.0
        exit_pos = entry_pos

        last_pos = min(len(d) - 1, entry_pos + int(max_hold_bars))

        for j in range(entry_pos, last_pos + 1):
            if d.index[j].date() != day:
                last_pos = j - 1
                break

            bar = d.iloc[j]
            high = float(bar["High"])
            low = float(bar["Low"])

            if side == "LONG":
                sl_hit = use_sl and low <= sl
                tp_hit = high >= tp
            else:
                sl_hit = use_sl and high >= sl
                tp_hit = low <= tp

            # Conservative 5m OHLC rule:
            # if both TP and SL are touched in the same candle, count SL first.
            if sl_hit and tp_hit:
                exit_pos = j
                exit_time = d.index[j]
                exit_price = sl
                exit_reason = "SL_AMBIGUOUS"
                r_result = -1.0
                break
            elif sl_hit:
                exit_pos = j
                exit_time = d.index[j]
                exit_price = sl
                exit_reason = "SL"
                r_result = -1.0
                break
            elif tp_hit:
                exit_pos = j
                exit_time = d.index[j]
                exit_price = tp
                exit_reason = "TP"
                r_result = float(rr)
                break
        else:
            last_pos = min(last_pos, len(d) - 1)

        if exit_reason == "TIME":
            last_pos = max(entry_pos, last_pos)
            exit_pos = last_pos
            exit_time = d.index[last_pos]
            exit_price = float(d.iloc[last_pos]["Close"])

            if side == "LONG":
                r_result = (exit_price - entry) / risk
            else:
                r_result = (entry - exit_price) / risk

        if side == "LONG":
            return_pct = ((exit_price / entry) - 1) * 100
        else:
            return_pct = ((entry - exit_price) / entry) * 100

        hold_bars = max(0, int(exit_pos - entry_pos))
        hold_minutes = hold_bars * 5
        actual_sl_pct = (risk / entry) * 100

        trades.append({
            "Ticker": s["Ticker"],
            "Side": side,
            "Episode": int(s["Episode"]),
            "EpisodeSignal": int(s["EpisodeSignal"]),
            "EntryTime": entry_time,
            "ExitTime": exit_time,
            "Entry": round(entry, 4),
            "BaseSL": round(base_sl, 4),
            "SL": round(sl, 4),
            "ActualSLPct": round(actual_sl_pct, 3),
            "SLMultiplier": float(sl_multiplier),
            "MaxSLPct": max_sl_pct,
            "FixedSLPct": fixed_sl_pct,
            "UseSL": bool(use_sl),
            "TP": round(tp, 4),
            "RR_Target": rr,
            "MaxHoldBars": int(max_hold_bars),
            "HoldBars": hold_bars,
            "HoldMinutes": hold_minutes,
            "ExitPrice": round(exit_price, 4),
            "ExitReason": exit_reason,
            "R": round(float(r_result), 3),
            "ReturnPct": round(float(return_pct), 3),
        })

    return pd.DataFrame(trades)


def summarize_rr_results(trades):
    if trades is None or trades.empty:
        return {
            "Trades": 0,
            "Wins": 0,
            "Losses": 0,
            "TPHits": 0,
            "SLHits": 0,
            "Timeouts": 0,
            "WinRatePct": 0.0,
            "TotalR": 0.0,
            "AvgR": 0.0,
            "TotalPct": 0.0,
            "AvgPct": 0.0,
            "ProfitFactor": 0.0,
            "MaxDD_R": 0.0,
            "AvgHoldMin": 0.0,
            "MaxHoldMin": 0,
        }

    wins = int((trades["R"] > 0).sum())
    losses = int((trades["R"] < 0).sum())
    timeouts = int((trades["ExitReason"] == "TIME").sum())
    tp_hits = int((trades["ExitReason"] == "TP").sum())
    sl_hits = int(trades["ExitReason"].isin(["SL", "SL_AMBIGUOUS"]).sum())

    gross_profit = float(trades.loc[trades["R"] > 0, "R"].sum())
    gross_loss = abs(float(trades.loc[trades["R"] < 0, "R"].sum()))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    equity_r = trades["R"].cumsum()
    drawdown_r = equity_r.cummax() - equity_r
    max_dd_r = float(drawdown_r.max()) if len(drawdown_r) else 0.0

    return {
        "Trades": len(trades),
        "Wins": wins,
        "Losses": losses,
        "TPHits": tp_hits,
        "SLHits": sl_hits,
        "Timeouts": timeouts,
        "WinRatePct": round((wins / len(trades)) * 100, 2),
        "TotalR": round(float(trades["R"].sum()), 3),
        "AvgR": round(float(trades["R"].mean()), 3),
        "TotalPct": round(float(trades["ReturnPct"].sum()), 3),
        "AvgPct": round(float(trades["ReturnPct"].mean()), 3),
        "ProfitFactor": round(float(profit_factor), 3) if np.isfinite(profit_factor) else np.inf,
        "MaxDD_R": round(max_dd_r, 3),
        "AvgHoldMin": round(float(trades["HoldMinutes"].mean()), 1),
        "MaxHoldMin": int(trades["HoldMinutes"].max()),
    }


def compare_rr_targets(
    df,
    signals,
    rr_targets=(1.0, 1.5, 2.0),
    max_hold_bars=40,
    sl_multiplier=1.0,
    max_sl_pct=None,
    fixed_sl_pct=None,
    use_sl=True,
    print_trades=False,
):
    rows = []
    trade_sets = {}

    for rr in rr_targets:
        trades = evaluate_rr_backtest(
            df=df,
            signals=signals,
            rr=rr,
            max_hold_bars=max_hold_bars,
            sl_multiplier=sl_multiplier,
            max_sl_pct=max_sl_pct,
            fixed_sl_pct=fixed_sl_pct,
            use_sl=use_sl,
        )
        trade_sets[rr] = trades

        summary = summarize_rr_results(trades)
        rows.append({
            "RR": rr,
            "UseSL": bool(use_sl),
            "SLMult": sl_multiplier,
            "MaxSLPct": max_sl_pct,
            "FixedSLPct": fixed_sl_pct,
            "MaxHoldBars": max_hold_bars,
            "MaxHoldMin": max_hold_bars * 5,
            **summary,
        })

    summary_df = pd.DataFrame(rows)

    print("\n" + "=" * 120)
    print("ASJR SMALL REPEATABLE V1 — RR EXIT COMPARISON")
    print("=" * 120)
    print(summary_df.to_string(index=False))

    if print_trades:
        for rr, trades in trade_sets.items():
            print("\n" + "-" * 120)
            print(f"RR {rr}:1 TRADES")
            print("-" * 120)
            print(trades.to_string(index=False))

    return summary_df, trade_sets


def compare_sl_holding_grid(
    df,
    signals,
    rr=1.5,
    sl_multipliers=(0.75, 1.0, 1.25, 1.5),
    max_sl_pcts=(None, 0.25, 0.50),
    hold_bars=(12, 24, 40),
):
    rows = []

    for sl_mult in sl_multipliers:
        for max_sl_pct in max_sl_pcts:
            for bars in hold_bars:
                trades = evaluate_rr_backtest(
                    df=df,
                    signals=signals,
                    rr=rr,
                    max_hold_bars=bars,
                    sl_multiplier=sl_mult,
                    max_sl_pct=max_sl_pct,
                )
                summary = summarize_rr_results(trades)

                rows.append({
                    "RR": rr,
                    "SLMult": sl_mult,
                    "MaxSLPct": max_sl_pct,
                    "MaxHoldBars": bars,
                    "MaxHoldMin": bars * 5,
                    **summary,
                })

    result = pd.DataFrame(rows)

    print("\n" + "=" * 140)
    print("ASJR SMALL REPEATABLE V1 — SL / MAX SL / HOLDING TEST")
    print("=" * 140)
    print(result.to_string(index=False))

    return result
