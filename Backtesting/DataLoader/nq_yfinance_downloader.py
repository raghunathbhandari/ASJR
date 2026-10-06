"""
Open-source NQ historical downloader using Yahoo Finance via yfinance.

Ticker:
    NQ=F (E-mini Nasdaq-100 continuous futures)

Outputs:
    Backtesting/BacktestData/OpenSource/NQ/
        NQ_1d_1y.csv
        NQ_1h_1y.csv
        NQ_4h_1y.csv
        NQ_15m_60d.csv
        NQ_5m_60d.csv

Notes:
- Yahoo/yfinance limits most intraday intervals below 1h to roughly 60 days.
- 4H is resampled from the 1H series.
- Timestamps are saved in UTC.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "BacktestData" / "OpenSource" / "NQ"
TICKER = "NQ=F"


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    out = df.reset_index()
    time_col = "Datetime" if "Datetime" in out.columns else "Date"
    out = out.rename(columns={time_col: "Datetime"})

    out["Datetime"] = pd.to_datetime(out["Datetime"], utc=True, errors="coerce")

    keep = ["Datetime", "Open", "High", "Low", "Close", "Volume"]
    for col in keep:
        if col not in out.columns:
            out[col] = 0.0 if col == "Volume" else pd.NA

    out = out[keep].dropna(subset=["Datetime", "Open", "High", "Low", "Close"])
    out = out.sort_values("Datetime").drop_duplicates("Datetime", keep="last")
    return out


def save(df: pd.DataFrame, filename: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)
    print(
        f"SAVED {filename} | rows={len(df)} | "
        f"{df['Datetime'].min() if not df.empty else 'NA'} -> "
        f"{df['Datetime'].max() if not df.empty else 'NA'}"
    )
    return path


def resample_4h(hourly: pd.DataFrame) -> pd.DataFrame:
    if hourly.empty:
        return hourly.copy()

    x = hourly.set_index("Datetime").sort_index()

    agg = x.resample("4h", origin="epoch").agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    )
    agg = agg.dropna(subset=["Open", "High", "Low", "Close"]).reset_index()
    return agg


def main() -> None:
    print("===== OPEN SOURCE NQ DOWNLOAD =====")
    print(f"Ticker: {TICKER}")

    daily = normalize(
        yf.download(
            TICKER,
            period="1y",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    )
    save(daily, "NQ_1d_1y.csv")

    hourly = normalize(
        yf.download(
            TICKER,
            period="1y",
            interval="1h",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    )
    save(hourly, "NQ_1h_1y.csv")

    four_hour = resample_4h(hourly)
    save(four_hour, "NQ_4h_1y.csv")

    m15 = normalize(
        yf.download(
            TICKER,
            period="60d",
            interval="15m",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    )
    save(m15, "NQ_15m_60d.csv")

    m5 = normalize(
        yf.download(
            TICKER,
            period="60d",
            interval="5m",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    )
    save(m5, "NQ_5m_60d.csv")

    print("===== OPEN SOURCE NQ DOWNLOAD COMPLETE =====")


if __name__ == "__main__":
    main()
