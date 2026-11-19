#!/usr/bin/env python3
"""Fixed, single-session Yahoo 5m import. No IBKR connection or Git main writes."""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/root/trading/ASJR")
DAY = "2026-10-20"
OUT = ROOT / "Rudra-DDB" / "ResearchData" / "Daily5m" / DAY
SYMBOLS = {"NQ": "NQ=F", "INTC": "INTC"}

def execute():
    import pandas as pd
    import yfinance as yf
    results = {}
    for name, symbol in SYMBOLS.items():
        try:
            day = datetime.fromisoformat(DAY).date()
            data = yf.download(
                symbol, start=(day-timedelta(days=1)).isoformat(),
                end=(day+timedelta(days=2)).isoformat(),
                interval="5m", prepost=True, auto_adjust=False,
                progress=False, threads=False, multi_level_index=False,
            )
            if data is None or data.empty or data.index.tz is None:
                results[name] = {"status":"FAILED","reason":"NO_YAHOO_5M_BARS"}
                continue
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            ny = data.tz_convert("America/New_York")
            ny = ny[ny.index.strftime("%Y-%m-%d") == DAY]
            columns = ["Open", "High", "Low", "Close", "Volume"]
            if ny.empty or not set(columns).issubset(ny.columns):
                results[name] = {"status":"FAILED","reason":"SESSION_OR_COLUMNS_MISSING"}
                continue
            ny = ny[columns].dropna(subset=columns[:4])
            ny = ny[~ny.index.duplicated(keep=False)]
            ny = ny.sort_index()
            if ny.empty:
                results[name] = {"status":"FAILED","reason":"NO_VALID_BARS"}
                continue
            if OUT.is_symlink():
                results[name]={"status":"FAILED","reason":"UNSAFE_DESTINATION"}
                continue
            OUT.mkdir(parents=True,exist_ok=True)
            target=OUT/(name+"_5m.csv")
            if target.is_symlink():
                results[name]={"status":"FAILED","reason":"UNSAFE_TARGET"}
                continue
            ny.index.name="datetime_ny"
            ny.to_csv(target)
            results[name]={
                "status":"SUCCESS", "rows":len(ny),
                "first_ny":str(ny.index[0]),"last_ny":str(ny.index[-1]),
                "relative_path":str(target.relative_to(ROOT)),
                "bytes":target.stat().st_size,
                "complete_session":datetime.now(ZoneInfo("America/New_York")).date()>day,
            }
        except Exception as exc:
            results[name]={"status":"FAILED","reason":type(exc).__name__}
    return {"status":"SUCCESS" if all(x["status"]=="SUCCESS" for x in results.values()) else "PARTIAL_OR_FAILED",
            "source":"Yahoo Finance", "date_ny":DAY,"interval":"5m", "symbols":results}

if __name__=="__main__":
    print(json.dumps(execute(),indent=2))
