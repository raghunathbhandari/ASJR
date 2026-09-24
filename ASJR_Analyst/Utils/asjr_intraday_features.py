import pandas as pd
import numpy as np

def add_intraday_features(df):
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    cols = {c.lower(): c for c in out.columns}

    ticker_col = cols.get("ticker", "Ticker")
    date_col = cols.get("date", "Date")
    open_col = cols.get("open", "Open")
    high_col = cols.get("high", "High")
    low_col = cols.get("low", "Low")
    close_col = cols.get("close", "Close")
    volume_col = cols.get("volume", "Volume")

    out = out.rename(columns={
        ticker_col: "ticker",
        date_col: "datetime",
        open_col: "open",
        high_col: "high",
        low_col: "low",
        close_col: "close",
        volume_col: "volume",
    })

    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["datetime"] = pd.to_datetime(out["datetime"])
    out = out.sort_values(["ticker", "datetime"]).reset_index(drop=True)

    # Full 3D history is intentionally retained for stable EMA20 calculation.
    g = out.groupby("ticker", group_keys=False)
    out["ema20"] = g["close"].transform(
        lambda s: s.ewm(span=20, adjust=False).mean()
    )

    out["dist_ema20_pct"] = (
        (out["close"] / out["ema20"]) - 1.0
    ) * 100.0

    out["bar_range_pct"] = (
        (out["high"] - out["low"])
        / out["close"].replace(0, np.nan)
        * 100.0
    )

    prev_close = g["close"].shift(1)
    prev_ema = g["ema20"].shift(1)

    out["cross_up"] = (
        (prev_close <= prev_ema)
        & (out["close"] > out["ema20"])
    )

    out["cross_down"] = (
        (prev_close >= prev_ema)
        & (out["close"] < out["ema20"])
    )

    # Session metrics must reset every trading day.
    out["session_date"] = out["datetime"].dt.date
    session_g = out.groupby(
        ["ticker", "session_date"],
        group_keys=False,
    )

    out["session_high"] = session_g["high"].cummax()
    out["session_low"] = session_g["low"].cummin()
    out["session_volume"] = session_g["volume"].cumsum()

    return out


def classify_setup(latest_row, session_rows):
    if latest_row is None:
        return "NO_DATA"

    close = float(latest_row["close"])
    ema = float(latest_row["ema20"])
    dist = float(latest_row.get("dist_ema20_pct", 0.0))

    recent = (
        session_rows.tail(12)
        if session_rows is not None
        else pd.DataFrame()
    )

    crossed_recently = (
        bool(recent["cross_up"].any())
        if not recent.empty and "cross_up" in recent.columns
        else False
    )

    if close < ema:
        return "BELOW_EMA20"

    if crossed_recently:
        if abs(dist) <= 0.20:
            return "NEAR_RETEST"
        if dist <= 0.80:
            return "WAIT_PULLBACK"
        return "EXTENDED_ABOVE_EMA20"

    if abs(dist) <= 0.20:
        return "AT_EMA20"

    return "ABOVE_EMA20"


def latest_intraday_summary(df):
    if df is None or df.empty:
        return pd.DataFrame()

    rows = []

    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("datetime").copy()

        latest_date = g["datetime"].iloc[-1].date()

        # Current trading day only for today's statistics.
        session = g[g["session_date"] == latest_date].copy()

        if session.empty:
            continue

        last = session.iloc[-1]
        first = session.iloc[0]

        setup = classify_setup(
            last,
            session.iloc[:-1],
        )

        first_open = float(first["open"])

        day_pct = (
            (float(last["close"]) / first_open - 1.0) * 100.0
            if first_open
            else None
        )

        rows.append({
            "ticker": ticker,
            "datetime": last["datetime"],
            "price": float(last["close"]),
            "ema20": float(last["ema20"]),
            "dist_ema20_pct": float(last["dist_ema20_pct"]),
            "day_pct": day_pct,
            "volume_so_far": float(session["volume"].sum()),
            "session_high": float(session["high"].max()),
            "session_low": float(session["low"].min()),
            "setup_status": setup,
            "cross_up_recent": bool(
                session.tail(12)["cross_up"].any()
            ),
        })

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["setup_status", "day_pct"],
            ascending=[True, False],
        )
        .reset_index(drop=True)
    )
