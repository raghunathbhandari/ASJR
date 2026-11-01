#!/usr/bin/env python3
"""Non-mutating AMD 5m direct-download probe for the VPS research bridge.

Prints availability only. Never saves OHLCV files or changes Git working trees.
"""
import json
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf


def main():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=5)
    frame = yf.download(
        "AMD", start=start, end=end, interval="5m", prepost=True,
        progress=False, auto_adjust=False, threads=False,
        multi_level_index=False,
    )
    if frame is None or frame.empty:
        print(json.dumps({"ticker": "AMD", "status": "NO_DATA", "rows": 0}))
        return 1
    if not isinstance(frame.index, pd.DatetimeIndex):
        print(json.dumps({"ticker": "AMD", "status": "BAD_INDEX"}))
        return 2
    print(json.dumps({
        "ticker": "AMD", "status": "DATA_RECEIVED", "rows": int(len(frame)),
        "first_utc": str(frame.index[0]),
        "last_utc": str(frame.index[-1]),
        "saved_files": 0,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
