#!/usr/bin/env python3
"""Descriptive return relationships and pre-move comparison for IBKR 46.

Reads only SAVED Yahoo OHLCV. No IBKR, Chakra, web requests, orders or Git.
Not a trading signal or calibrated predictive probability.
"""
from __future__ import annotations
import itertools
import numpy as np
import pandas as pd
from RudraScanner.research_ema50_46 import NAMES, OUT, _load

NEW_FILES = (
    "PATTERNS_RELATIONSHIPS_46.md",
    "CORRELATION_PAIRS_46.csv",
    "NORMALIZED_CLOSE_63D.csv",
    "PREMOVE_EVENTS_46.csv",
    "PREMOVE_SUMMARY_46.csv",
)


def _daily(ticker):
    f = _load("daily", ticker)
    if f.empty:
        return f
    f = f.copy()
    for c in ("Open", "High", "Low", "Close", "Volume"):
        f[c] = pd.to_numeric(f[c], errors="coerce")
    f = f.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    f.index = pd.Index(f.index.date, name="date")
    return f[~f.index.duplicated(keep="last")].sort_index()


def _features(f):
    c, v = f.Close, f.Volume
    e9 = c.ewm(span=9, adjust=False).mean()
    e20 = c.ewm(span=20, adjust=False).mean()
    low12 = f.Low.shift(1).rolling(12).min()
    return pd.DataFrame(index=f.index, data={
        "pre5": (c / c.shift(5) - 1) * 100,
        "pre20": (c / c.shift(20) - 1) * 100,
        "future20": (c.shift(-20) / c - 1) * 100,
        "rvol": v / v.shift(1).rolling(20).mean().replace(0, np.nan),
        "vcompress": v.rolling(5).mean() / v.rolling(20).mean().replace(0, np.nan),
        "ema_up": (e9 > e20) & (e20 > e20.shift(5)) & (c > e20),
        "ema_dist": (c / e20 - 1) * 100,
        "range10": (f.High.rolling(10).max() / f.Low.rolling(10).min() - 1) * 100,
        "sweep": (f.Low < low12) & (c > low12),
        "breakout": c > f.High.shift(1).rolling(20).max(),
    })


def analyze():
    OUT.mkdir(parents=True, exist_ok=True)
    prices = {t: _daily(t) for t in NAMES}
    liquid = {}
    for t, f in prices.items():
        if (len(f) >= 80 and f.Volume.tail(20).mean() >= 200000
                and f.Close.tail(64).nunique() >= 20):
            liquid[t] = f.Close.pct_change(fill_method=None).replace(
                [np.inf, -np.inf], np.nan).tail(63)
    pairs = []
    for a, b in itertools.combinations(sorted(liquid), 2):
        z = pd.concat([liquid[a], liquid[b]], axis=1, join="inner").dropna()
        if len(z) < 45 or z.iloc[:, 0].std() == 0 or z.iloc[:, 1].std() == 0:
            continue
        x, y = z.iloc[:, 0], z.iloc[:, 1]
        pairs.append({
            "a": a, "b": b, "bars": len(z),
            "pearson63": round(float(x.corr(y)), 4),
            "spearman63": round(float(x.corr(y, method="spearman")), 4),
            "pearson20": round(float(x.tail(20).corr(y.tail(20))), 4),
        })
    cols = ["a", "b", "bars", "pearson63", "spearman63", "pearson20"]
    cp = pd.DataFrame(pairs, columns=cols).sort_values(
        "pearson63", ascending=False).reset_index(drop=True)
    cp.to_csv(OUT / "CORRELATION_PAIRS_46.csv", index=False)

    calendar = sorted(set().union(*(f.index[-64:] for f in prices.values() if len(f))))
    normalized = pd.DataFrame(index=pd.Index(calendar[-64:], name="date"))
    for ticker, f in prices.items():
        aligned = f.Close.reindex(normalized.index)
        valid = aligned.dropna()
        normalized[ticker] = (100 * aligned / valid.iloc[0]
                              if len(valid) and valid.iloc[0] > 0 else np.nan)
    normalized.round(3).to_csv(OUT / "NORMALIZED_CLOSE_63D.csv")

    events = []
    for ticker, f in prices.items():
        if len(f) < 120 or f.Volume.tail(20).mean() < 200000:
            continue
        d = _features(f)
        last_selected = -21
        for i in range(65, len(d) - 20):
            r = d.iloc[i]
            keys = ("pre5", "pre20", "future20", "range10", "ema_dist")
            if any(pd.isna(r[k]) for k in keys):
                continue
            # Study stocks BEFORE extension, using only as-of-date features.
            if r["pre20"] > 15 or r["ema_dist"] > 15:
                continue
            win = r["future20"] >= 20
            ctrl = r["future20"] < 5
            if (not win and not ctrl) or i - last_selected < 20:
                continue
            last_selected = i
            before5 = d.iloc[i-4:i+1]
            events.append({
                "ticker": ticker, "asof_date": str(d.index[i]),
                "group": "WIN20" if win else "CONTROL_LT5",
                "forward20_close_pct": round(float(r["future20"]), 2),
                "prior5_pct": round(float(r["pre5"]), 2),
                "prior20_pct": round(float(r["pre20"]), 2),
                "rvol_daily": round(float(r["rvol"]), 3) if pd.notna(r["rvol"]) else np.nan,
                "vol5_over20": round(float(r["vcompress"]), 3) if pd.notna(r["vcompress"]) else np.nan,
                "range10_pct": round(float(r["range10"]), 2),
                "ema_up": bool(r["ema_up"]),
                "sweep_last5": bool(before5.sweep.any()),
                "breakout_last5": bool(before5.breakout.any()),
                "base_tight15": bool(r["range10"] <= 15),
                "volume_contract": bool(r["vcompress"] < 0.8)
                        if pd.notna(r["vcompress"]) else False,
            })
    es = pd.DataFrame(events)
    if es.empty:
        es = pd.DataFrame(columns=[
            "ticker", "asof_date", "group", "forward20_close_pct",
            "prior5_pct", "prior20_pct", "rvol_daily", "vol5_over20",
            "range10_pct", "ema_up", "sweep_last5", "breakout_last5",
            "base_tight15", "volume_contract"])
    es.to_csv(OUT / "PREMOVE_EVENTS_46.csv", index=False)
    summaries = []
    for group in ("WIN20", "CONTROL_LT5"):
        z = es.loc[es.group.eq(group)]
        info = {"group": group, "events": len(z), "tickers": z.ticker.nunique()}
        if len(z):
            for feature in ("prior5_pct", "prior20_pct", "rvol_daily",
                            "vol5_over20", "range10_pct"):
                info["median_" + feature] = round(float(z[feature].median()), 3)
            for feature in ("ema_up", "sweep_last5", "breakout_last5",
                            "base_tight15", "volume_contract"):
                info[feature + "_pct"] = round(float(100 * z[feature].mean()), 1)
        summaries.append(info)
    pd.DataFrame(summaries).to_csv(OUT / "PREMOVE_SUMMARY_46.csv", index=False)

    report = [
        "# Rudra 46: historical co-movement and pre-move patterns",
        "",
        "As-of: last completed US session 2026-10-15. Original IBKR EMA50 ticker universe.",
        f"Correlation universe: {len(liquid)} liquid/non-frozen ticker series; "
        f"{len(cp)} pairs with >=45 aligned trading-day returns.",
        "Daily returns are correlated, NOT raw prices. 63-day Pearson and Spearman",
        "and 20-day Pearson; 20-day results are inherently unstable.",
        "",
        "## Highest positive 63-session pairwise correlations",
        "| Pair | Pearson 63d | Spearman 63d | Pearson 20d |",
        "|---|---:|---:|---:|",
    ]
    for _, x in cp.head(20).iterrows():
        report.append(f"| {x.a}/{x.b} | {x.pearson63:+.2f} | "
                      f"{x.spearman63:+.2f} | {x.pearson20:+.2f} |")
    report += [
        "", "## Lowest 63-session correlations",
        "| Pair | Pearson 63d | Spearman 63d | Pearson 20d |",
        "|---|---:|---:|---:|",
    ]
    for _, x in cp.tail(10).iloc[::-1].iterrows():
        report.append(f"| {x.a}/{x.b} | {x.pearson63:+.2f} | "
                      f"{x.spearman63:+.2f} | {x.pearson20:+.2f} |")
    report += [
        "", "## Conditions recorded BEFORE historical 20-session gains",
        "WIN20 means the next 20 trading-session CLOSE rose >=20%; CONTROL_LT5",
        "means less than +5%. At as-of date, trailing 20d move <=15% and",
        "distance above EMA20 <=15%, to avoid already-extended start dates.",
        "Observations are separated by at least 20 sessions per ticker.",
        "",
        "| Group | Samples | Tickers | Prior5 median | Daily RVOL median | Rising EMAs | Sweeps last5 | Tight 10d base | Declining volume |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a in summaries:
        def get(key, suffix=""):
            v = a.get(key)
            return "N/A" if v is None else f"{v}{suffix}"
        report.append(f"| {a['group']} | {a['events']} | {a['tickers']} | "
                      f"{get('median_prior5_pct', '%')} | "
                      f"{get('median_rvol_daily', 'x')} | "
                      f"{get('ema_up_pct', '%')} | {get('sweep_last5_pct', '%')} | "
                      f"{get('base_tight15_pct', '%')} | {get('volume_contract_pct', '%')} |")
    report += [
        "",
        "## Interpretation and quality limits",
        "- This universe was selected by a 2026-10-15 scanner; historical",
        "  tests consequently suffer point-in-time selection/survivorship bias.",
        "- Negative controls are not matched for market regime, sectors or company cap.",
        "- WIN20 is defined using future closing price for research LABELS only.",
        "  No future values enter the recorded pre-move conditions.",
        "- Tight-base, sweep and consolidation definitions are simple first-pass",
        "  diagnostics and are not verified entry rules.",
        "- 5-minute RVOL behaviour before every past event has NOT been",
        "  measured here. Only daily-volume conditions are included.",
        "- Correlation does not establish causality or predictive leadership.",
        "",
        "## Data files",
        "CORRELATION_PAIRS_46.csv, NORMALIZED_CLOSE_63D.csv,",
        "PREMOVE_EVENTS_46.csv and PREMOVE_SUMMARY_46.csv",
    ]
    (OUT / "PATTERNS_RELATIONSHIPS_46.md").write_text("\n".join(report) + "\n")
    print(f"RELATIONSHIPS | liquid {len(liquid)} | pairs {len(cp)} "
          f"| winner samples {(es.group == 'WIN20').sum()} "
          f"| controls {(es.group == 'CONTROL_LT5').sum()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(analyze())
