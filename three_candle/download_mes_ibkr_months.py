"""Download MES Dec-2026 IBKR 5-minute extended-session bars for Sep/Oct 2026.

Run on VPS after pulling this file:
    /root/trading/venv_new/bin/python three_candle/download_mes_ibkr_months.py --port 4002

Uses the existing monthly downloader's daily requests and coverage audit.
This is historical data only: no orders, no bot/Gateway restart.
Existing monthly MES files are never overwritten.
"""
import argparse
from pathlib import Path

from ib_insync import IB, Future

# Reuse the tested day-by-day download, timestamp conversion and audit functions.
from download_nq_gc_ibkr_months import download_month


DATA_DIR = Path(__file__).resolve().parent / "data"
MONTHS = [(2026, 9), (2026, 10)]


def download_mes_months(host="127.0.0.1", port=4002, client_id=89, pause=2.0):
    """Download only missing MESZ2026 monthly datasets."""
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id, timeout=20, readonly=True)

        # Specific Dec 2026 micro E-mini S&P 500 contract; avoid continuous data.
        matched = ib.qualifyContracts(
            Future(symbol="MES", lastTradeDateOrContractMonth="202612",
                   exchange="CME", currency="USD")
        )
        if len(matched) != 1:
            raise RuntimeError("MES Dec 2026 contract could not be uniquely qualified")

        contract = matched[0]
        print(f"Qualified MES: {contract}", flush=True)
        if contract.symbol != "MES" or not contract.lastTradeDateOrContractMonth.startswith("202612"):
            raise RuntimeError("Qualified wrong MES contract; refusing download")

        for year, month in MONTHS:
            label = f"MESZ2026_IBKR_5m_{year}-{month:02d}"
            csv = DATA_DIR / f"{label}.csv"
            report = DATA_DIR / f"{label}_coverage.txt"

            # Never replace historical data or its audit without explicit review.
            if csv.exists() or report.exists():
                print(f"SKIPPED {label}: existing file found; no overwrite", flush=True)
                continue

            download_month(ib, contract, "MES", year, month, pause)
    finally:
        if ib.isConnected():
            ib.disconnect()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4002)
    parser.add_argument("--client-id", type=int, default=89)
    parser.add_argument("--pause", type=float, default=2.0)
    args = parser.parse_args()
    download_mes_months(args.host, args.port, args.client_id, args.pause)


if __name__ == "__main__":
    main()
