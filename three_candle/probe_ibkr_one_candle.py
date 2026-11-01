#!/usr/bin/env python3
"""Read-only one-candle IBKR Gateway connectivity probe; saves no files."""
import json
from ib_insync import IB, Stock


def main():
    ib = IB()
    try:
        ib.connect("127.0.0.1", 1045, clientId=79431,
                   readonly=True, timeout=8)
        contract = Stock("AMD", "SMART", "USD")
        ib.qualifyContracts(contract)
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="20261030 19:00:00 UTC",
            durationStr="300 S",
            barSizeSetting="5 mins",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=2,
            keepUpToDate=False,
            timeout=25,
        )
        if not bars:
            print(json.dumps({"source": "IBKR", "ticker": "AMD",
                              "status": "NO_CANDLE", "saved_files": 0}))
            return 2
        candle = bars[-1]
        print(json.dumps({
            "source": "IBKR", "ticker": "AMD", "status": "CANDLE_RECEIVED",
            "time_utc": str(candle.date),
            "open": candle.open, "high": candle.high,
            "low": candle.low, "close": candle.close,
            "volume": candle.volume, "saved_files": 0,
        }))
        return 0
    except Exception as exc:
        print(json.dumps({"source": "IBKR", "ticker": "AMD",
                          "status": "ERROR", "error_type": type(exc).__name__,
                          "message": str(exc)[:250], "saved_files": 0}))
        return 1
    finally:
        if ib.isConnected():
            ib.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
