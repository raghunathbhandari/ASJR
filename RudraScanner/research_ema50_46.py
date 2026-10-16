#!/usr/bin/env python3
"""ON-DEMAND research only: collect dated Yahoo candles for 46 EMA50 IBKR symbols.

No IBKR connection, no Chakra changes, no scheduled tasks, no orders, no Git
commands. Run five batches, then --finalize. All outputs live in an isolated,
Git-trackable RudraScanner/ResearchData directory.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "RudraScanner" / "ResearchData" / "EMA50_2026-10-15"
ET = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")
SOURCE = "User-pasted IBKR HIGH_LAST_VS_EMA50 scan, 2026-10-15 20:15 UK"
NAMES = (
    "MAMK PMI FVNNU GIBO MRNA SVRN BSP KOD RGC IOVA VNCE FIGS XP PCRX "
    "AEHL ODD SG GRAL NVAX CVI CBRL RCEL TBCH PTC PICS IBTA PD OPCH "
    "RXO CDNA GME TEAM KSS EFOR VIA NTSK SUJA DXC SIG DNA CAI SHOP ACN "
    "MPC VEEV PRGO"
).split()
BATCH_SIZE = 10
BATCHES = 5
COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def _frame(raw, symbol):
    if raw is None or raw.empty:
        return pd.DataFrame()
    try:
        sub = raw[symbol] if isinstance(raw.columns, pd.MultiIndex) else raw
        sub = sub.loc[:, list(COLUMNS)].copy()
        for key in COLUMNS:
            sub[key] = pd.to_numeric(sub[key], errors="coerce")
        sub = sub.dropna(subset=list(COLUMNS)).sort_index()
        sub = sub[~sub.index.duplicated(keep="last")]
        valid = (sub["Volume"] >= 0) & (sub["Low"] > 0)
        valid &= sub["High"] >= sub[["Open", "Close", "Low"]].max(axis=1)
        valid &= sub["Low"] <= sub[["Open", "Close", "High"]].min(axis=1)
        return sub.loc[valid]
    except (KeyError, TypeError, ValueError):
        return pd.DataFrame()


def _completed_bars(frame, intraday=False):
    if frame.empty:
        return frame
    idx = frame.index
    if idx.tz is None:
        idx = idx.tz_localize(ET)
    else:
        idx = idx.tz_convert(ET)
    frame = frame.copy()
    frame.index = idx
    # Exclude CURRENT US date, which may contain partial 5m and daily candles.
    frame = frame.loc[frame.index.date < datetime.now(ET).date()]
    if intraday:
        hhmm = frame.index.hour * 60 + frame.index.minute
        frame = frame.loc[(hhmm >= 570) & (hhmm <= 955)]  # 09:30–15:55 ET
    frame.index.name = "timestamp_et"
    return frame


def _download(yf, symbols, *, intraday=False):
    # Yahoo 5-minute data is usually limited to the recent ~60 days;
    # request only 45 days and record gaps rather than invent candles.
    return yf.download(
        tickers=" ".join(symbols),
        period="45d" if intraday else "2y",
        interval="5m" if intraday else "1d",
        group_by="ticker", auto_adjust=not intraday,
        prepost=False, threads=False, progress=False,
    )


def _save(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, compression="gzip", float_format="%.8f")


def collect_batch(batch):
    import yfinance as yf
    selected = NAMES[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
    if not selected:
        raise ValueError("Invalid batch number")
    OUT.mkdir(parents=True, exist_ok=True)
    status = {
        "batch": batch, "source": SOURCE,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "symbol_status": {}, "errors": [],
    }
    print(f"EMA50 RESEARCH | BATCH {batch}/{BATCHES} | {len(selected)} tickers", flush=True)
    # Daily and intraday are independent so one failed Yahoo request cannot
    # masquerade as successful full coverage for the other timeframe.
    for intraday in (False, True):
        kind = "five_minute" if intraday else "daily"
        size = 3 if intraday else 10
        for i in range(0, len(selected), size):
            part = selected[i:i + size]
            try:
                downloaded = _download(yf, part, intraday=intraday)
            except Exception as exc:
                downloaded = pd.DataFrame()
                status["errors"].append(f"{kind}:{','.join(part)}:{type(exc).__name__}")
            for symbol in part:
                subset = _completed_bars(_frame(downloaded, symbol), intraday)
                entry = status["symbol_status"].setdefault(symbol, {})
                entry[kind] = len(subset)
                target = OUT / kind / f"{symbol}.csv.gz"
                if len(subset):
                    _save(subset, target)
                else:
                    # Failed refresh must not masquerade as fresh data.
                    if target.exists():
                        target.unlink()
                    status["errors"].append(f"{kind}:{symbol}:NO_VALID_BARS")
                print(f"{symbol} {kind} rows={len(subset)}", flush=True)
    (OUT / f"batch_{batch}.json").write_text(json.dumps(status, indent=2) + "\n")
    print(f"BATCH {batch} SAVED | {OUT.relative_to(ROOT)} | errors={len(status['errors'])}")
    return 0


def _load(kind, symbol):
    path = OUT / kind / f"{symbol}.csv.gz"
    if not path.is_file():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path, index_col=0, parse_dates=True)
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize(ET)
        else:
            frame.index = frame.index.tz_convert(ET)
        return frame.sort_index()
    except (OSError, ValueError, TypeError):
        return pd.DataFrame()


def _ratio(a, b):
    try:
        a, b = float(a), float(b)
        return round(a / b, 4) if math.isfinite(a) and math.isfinite(b) and b > 0 else None
    except (TypeError, ValueError):
        return None


def _pct(a, b):
    r = _ratio(a, b)
    return round((r - 1) * 100, 2) if r is not None else None


def _daily_features(frame):
    if len(frame) < 65:
        return {"daily_rows": len(frame), "daily_status": "INSUFFICIENT"}
    close, vol = frame["Close"], frame["Volume"]
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    sma50 = close.rolling(50).mean()
    old = frame.iloc[-2]
    latest = frame.iloc[-1]
    vol_prev5 = vol.shift(1).rolling(5).mean().iloc[-1]
    vol_prev20 = vol.shift(1).rolling(20).mean().iloc[-1]
    hi20 = frame["High"].shift(1).rolling(20).max().iloc[-1]
    base_high = frame["High"].tail(10).max()
    base_low = frame["Low"].tail(10).min()
    v5 = vol.tail(5).mean()
    v20 = vol.tail(20).mean()
    return {
        "daily_rows": len(frame), "daily_status": "OK",
        "daily_last_et": str(frame.index[-1].date()),
        "close": round(float(close.iloc[-1]), 4),
        "return_5d_pct": _pct(close.iloc[-1], close.iloc[-6]),
        "return_10d_pct": _pct(close.iloc[-1], close.iloc[-11]),
        "return_20d_pct": _pct(close.iloc[-1], close.iloc[-21]),
        "return_63d_pct": _pct(close.iloc[-1], close.iloc[-64]),
        "daily_volume": int(vol.iloc[-1]),
        "daily_rvol5_prev_days": _ratio(vol.iloc[-1], vol_prev5),
        "daily_rvol20_prev_days": _ratio(vol.iloc[-1], vol_prev20),
        "daily_volume5_vs20": _ratio(v5, v20),
        "ema9_daily": round(float(ema9.iloc[-1]), 4),
        "ema20_daily": round(float(ema20.iloc[-1]), 4),
        "sma50_daily": round(float(sma50.iloc[-1]), 4),
        "ema9_slope5_pct": _pct(ema9.iloc[-1], ema9.iloc[-6]),
        "ema20_slope5_pct": _pct(ema20.iloc[-1], ema20.iloc[-6]),
        "sma50_slope5_pct": _pct(sma50.iloc[-1], sma50.iloc[-6]),
        "distance_ema9_pct": _pct(close.iloc[-1], ema9.iloc[-1]),
        "distance_ema20_pct": _pct(close.iloc[-1], ema20.iloc[-1]),
        "distance_sma50_pct": _pct(close.iloc[-1], sma50.iloc[-1]),
        "daily_high_breakout20": bool(close.iloc[-1] > hi20),
        "range10_pct": _pct(base_high, base_low),
        "volume_contraction_daily": bool(v5 < 0.8 * v20),
        "daily_inside_bar": bool(latest["High"] < old["High"] and
                                 latest["Low"] > old["Low"]),
    }


def _intraday_features(frame):
    if len(frame) < 25:
        return {"five_minute_rows": len(frame), "five_minute_status": "INSUFFICIENT"}
    f = frame.copy()
    # Session slots are compared ONLY with earlier, same ET 5-minute slots.
    slots = f.index.strftime("%H:%M")
    barvol = f["Volume"]
    last = f.iloc[-1]
    ema9 = f["Close"].ewm(span=9, adjust=False).mean()
    ema20 = f["Close"].ewm(span=20, adjust=False).mean()
    prev5 = barvol.shift(1).rolling(5).mean().iloc[-1]
    prev20 = barvol.shift(1).rolling(20).mean().iloc[-1]
    grouped = barvol.groupby(slots)
    slot5 = grouped.transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    slot20 = grouped.transform(lambda x: x.shift(1).rolling(20, min_periods=20).mean())
    high_prev20 = f["High"].shift(1).rolling(20).max().iloc[-1]
    low_prev12 = f["Low"].shift(1).rolling(12).min().iloc[-1]
    previous = f.iloc[-2]
    body = abs(last["Close"] - last["Open"])
    lower_wick = min(last["Open"], last["Close"]) - last["Low"]
    upper_wick = last["High"] - max(last["Open"], last["Close"])
    current_range = last["High"] - last["Low"]
    range_med20 = (f["High"] - f["Low"]).shift(1).tail(20).median()
    consolidation_high = f["High"].tail(10).max()
    consolidation_low = f["Low"].tail(10).min()
    return {
        "five_minute_rows": len(f), "five_minute_status": "OK",
        "last_bar_et": f.index[-1].isoformat(),
        "last_bar_volume": int(last["Volume"]),
        "rvol5bar": _ratio(last["Volume"], prev5),
        "rvol20bar": _ratio(last["Volume"], prev20),
        "rvol5day_same_slot": _ratio(last["Volume"], slot5.iloc[-1]),
        "rvol20day_same_slot": _ratio(last["Volume"], slot20.iloc[-1]),
        "ema9_5m": round(float(ema9.iloc[-1]), 4),
        "ema20_5m": round(float(ema20.iloc[-1]), 4),
        "ema9_5bar_slope_pct": _pct(ema9.iloc[-1], ema9.iloc[-6]),
        "ema20_5bar_slope_pct": _pct(ema20.iloc[-1], ema20.iloc[-6]),
        "close_above_ema9_5m": bool(last["Close"] > ema9.iloc[-1]),
        "close_above_ema20_5m": bool(last["Close"] > ema20.iloc[-1]),
        "lower_wick_of_range": _ratio(lower_wick, current_range),
        "upper_wick_of_range": _ratio(upper_wick, current_range),
        "body_of_range": _ratio(body, current_range),
        "lower_sweep12_reclaim": bool(last["Low"] < low_prev12 and last["Close"] > low_prev12),
        "inside_bar_5m": bool(last["High"] < previous["High"] and
                              last["Low"] > previous["Low"]),
        "bullish_engulfing_5m": bool(last["Close"] > last["Open"] and
                                    previous["Close"] < previous["Open"] and
                                    last["Open"] <= previous["Close"] and
                                    last["Close"] >= previous["Open"]),
        "breakout_prev20_high_5m": bool(last["Close"] > high_prev20),
        "tight_bar_5m": bool(current_range > 0 and
                            current_range < 0.65 * range_med20),
        "range10_5m_pct": _pct(consolidation_high, consolidation_low),
    }


def finalize():
    if len(NAMES) != 46 or len(set(NAMES)) != 46:
        raise ValueError("IBKR 46-name universe was altered")
    entries = []
    for symbol in NAMES:
        daily = _load("daily", symbol)
        five = _load("five_minute", symbol)
        record = {"ticker": symbol, "ibkr_source": "HIGH_LAST_VS_EMA50",
                  "market_cap_usd": None, "market_cap_status": "NOT_VERIFIED",
                  "sector_status": "NOT_VERIFIED", "catalyst_status": "NOT_VERIFIED"}
        record.update(_daily_features(daily))
        record.update(_intraday_features(five))
        entries.append(record)
    OUT.mkdir(parents=True, exist_ok=True)
    missing_batches = [i for i in range(1, BATCHES + 1) if not (OUT / f"batch_{i}.json").exists()]
    if missing_batches:
        print(f"INCOMPLETE | run collection batches first: {missing_batches}", flush=True)
        return 2
    df = pd.DataFrame(entries)
    df.to_csv(OUT / "research_metrics_46.csv", index=False)
    covered_daily = int(df["daily_status"].eq("OK").sum())
    covered_5m = int(df["five_minute_status"].eq("OK").sum())
    full_slots = int(df["rvol20day_same_slot"].notna().sum()) if "rvol20day_same_slot" in df else 0
    if "return_20d_pct" not in df:
        df["return_20d_pct"] = float("nan")
    sorted_df = df.sort_values("return_20d_pct", ascending=False, na_position="last")
    lines = [
        "# Rudra 46 — historical data collection",
        f"Source: {SOURCE}",
        f"Report time UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Daily metrics coverage: {covered_daily}/46",
        f"5-minute metrics coverage: {covered_5m}/46",
        f"20-day same-time-slot RVOL coverage: {full_slots}/46",
        "",
        "No scoring weights or trading thresholds have been approved.",
        "Raw IBKR scan membership alone is NOT evidence of fresh entry setup.",
        "No historical market capitalization or catalysts are verified here.",
        "Recent daily bars are adjusted; intraday bars are unadjusted Yahoo data.",
        "Yahoo data can be delayed or incomplete; no IBKR 5m comparison yet.",
        "",
        "## Top 15 by measured 20-session return (NOT a buy list)",
        "| Ticker | 20D% | RVOL5bar | RVOL20bar | Same-slot RVOL20 | EMA20 daily slope5% |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, item in sorted_df.head(15).iterrows():
        def show(key):
            val = item.get(key)
            return "N/A" if pd.isna(val) else f"{val:.2f}"
        lines.append("| " + str(item["ticker"]) + " | " +
                     " | ".join(show(key) for key in (
                         "return_20d_pct", "rvol5bar", "rvol20bar",
                         "rvol20day_same_slot", "ema20_slope5_pct")) + " |")
    lines += ["", "Full audit: research_metrics_46.csv and dated compressed OHLCV files.",
              "Catalysts/sector/market caps must be separately verified before scoring."]
    (OUT / "RESEARCH_REPORT.md").write_text("\n".join(lines) + "\n")
    print(f"FINALIZED | {len(df)} tickers | daily {covered_daily}/46 | 5m {covered_5m}/46 "
          f"| same-slot RVOL20 {full_slots}/46", flush=True)
    print(f"FILES | {OUT.relative_to(ROOT)}/research_metrics_46.csv")
    print(f"FILES | {OUT.relative_to(ROOT)}/RESEARCH_REPORT.md")
    return 0 if covered_daily else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="On-demand fixed IBKR EMA50-46 Yahoo research collector")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--batch", type=int, choices=range(1, BATCHES + 1))
    group.add_argument("--finalize", action="store_true")
    args = parser.parse_args(argv)
    return finalize() if args.finalize else collect_batch(args.batch)


if __name__ == "__main__":
    raise SystemExit(main())
