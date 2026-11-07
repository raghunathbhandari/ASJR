#!/usr/bin/env python3
"""Split existing IBKR multi-day CSVs into immutable UTC daily files.

Example:
  python three_candle/split_ibkr_daily.py three_candle/data/MESZ2026_IBKR_5m_2026-11-01_to_2026-11-06.csv
Does not delete, overwrite, download or Git-push anything.
"""
import argparse
import re
from pathlib import Path
import pandas as pd


def split(path: Path) -> None:
    match = re.fullmatch(r"([A-Z0-9]+[FGHJKMNQUVXZ][0-9]{4})_IBKR_5m_\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}\.csv", path.name)
    if not match:
        raise ValueError(f"Expected explicit dated-futures range filename: {path.name}")
    df = pd.read_csv(path)
    required = {"Datetime_UTC", "Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(df.columns):
        raise ValueError(f"{path.name}: missing columns {sorted(required - set(df.columns))}")
    times = pd.to_datetime(df["Datetime_UTC"], utc=True, errors="raise")
    if times.duplicated().any():
        raise ValueError(f"{path.name}: duplicate timestamps; review source")
    df["_UTC_day"] = times.dt.date
    for day, chunk in df.groupby("_UTC_day", sort=True):
        dest = path.parent / f"{match.group(1)}_IBKR_5m_{day}.csv"
        if dest.exists():
            print(f"SKIP existing {dest.name}")
            continue
        with dest.open("x", encoding="utf-8", newline="") as file:
            chunk.drop(columns="_UTC_day").to_csv(file, index=False)
        print(f"SAVED {dest.name} | {len(chunk)} bars")
    print(f"Original preserved: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    for file in args.files:
        split(file)
