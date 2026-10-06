"""
ASJR Forex historical data downloader.

Downloads spot FX MIDPOINT history from IBKR and keeps it separate from the
equity backtest cache.

Default:
    EUR/USD
    1 year
    1 day, 4 hours, 1 hour

Output:
    Backtesting/BacktestData/IBKR/Forex/EURUSD/
        EURUSD_1d.csv
        EURUSD_4h.csv
        EURUSD_1h.csv

CSV schema:
    Datetime,Open,High,Low,Close,Volume

Notes:
- Raw timestamps are stored in UTC.
- Spot FX has no centralized exchange volume, so Volume is stored as 0.
- IBKR whatToShow=MIDPOINT and useRTH=False are used for FX.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import pandas as pd

try:
    from ib_async import IB, Contract
except ImportError as exc:
    raise ImportError("ib_async is required: pip install ib_async") from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "BacktestData" / "IBKR" / "Forex"

BAR_CONFIG = {
    "1d": {
        "bar_size": "1 day",
        "duration": "1 Y",
    },
    "4h": {
        "bar_size": "4 hours",
        "duration": "3 M",
    },
    "1h": {
        "bar_size": "1 hour",
        "duration": "1 M",
    },
}


def parse_pair(pair: str) -> tuple[str, str, str]:
    clean = pair.upper().replace("/", "").replace("-", "").replace("_", "").strip()
    if len(clean) != 6 or not clean.isalpha():
        raise ValueError(
            f"Invalid FX pair '{pair}'. Use a six-letter pair such as EURUSD."
        )
    return clean[:3], clean[3:], clean


def as_utc(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def bars_to_frame(bars) -> pd.DataFrame:
    rows = []
    for bar in bars or []:
        rows.append(
            {
                "Datetime": getattr(bar, "date", None),
                "Open": getattr(bar, "open", None),
                "High": getattr(bar, "high", None),
                "Low": getattr(bar, "low", None),
                "Close": getattr(bar, "close", None),
                "Volume": 0.0,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["Datetime", "Open", "High", "Low", "Close", "Volume"]
        )

    df = pd.DataFrame(rows)
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True, errors="coerce")
    df = df.dropna(subset=["Datetime", "Open", "High", "Low", "Close"])

    for col in ["Open", "High", "Low", "Close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df.sort_values("Datetime")
    df = df.drop_duplicates(subset=["Datetime"], keep="last")
    return df[["Datetime", "Open", "High", "Low", "Close", "Volume"]]


async def download_interval(
    ib: IB,
    contract: Contract,
    pair_name: str,
    interval: str,
    start_utc: pd.Timestamp,
    end_utc: pd.Timestamp,
    output_root: Path,
    pacing_sleep: float = 0.35,
) -> Path:
    cfg = BAR_CONFIG[interval]

    frames: list[pd.DataFrame] = []
    cursor_end = end_utc
    previous_earliest = None
    chunk = 0

    print()
    print(f"===== {pair_name} {interval} =====")
    print(f"Requested: {start_utc} -> {end_utc}")

    while cursor_end > start_utc:
        chunk += 1

        bars = await ib.reqHistoricalDataAsync(
            contract,
            endDateTime=cursor_end.to_pydatetime(),
            durationStr=cfg["duration"],
            barSizeSetting=cfg["bar_size"],
            whatToShow="MIDPOINT",
            useRTH=False,
            formatDate=2,
            keepUpToDate=False,
        )

        df = bars_to_frame(bars)
        if df.empty:
            print(f"{pair_name} {interval} | chunk {chunk:03d} | no bars")
            break

        earliest = as_utc(df["Datetime"].min())
        latest = as_utc(df["Datetime"].max())

        print(
            f"{pair_name} {interval} | chunk {chunk:03d} | "
            f"{earliest} -> {latest} | rows={len(df)}"
        )

        frames.append(df)

        if earliest <= start_utc:
            break

        if previous_earliest is not None and earliest >= previous_earliest:
            raise RuntimeError(
                f"{pair_name} {interval}: IBKR cursor did not move backward."
            )

        previous_earliest = earliest
        cursor_end = earliest - pd.Timedelta(seconds=1)

        if pacing_sleep > 0:
            await asyncio.sleep(pacing_sleep)

    if not frames:
        raise RuntimeError(f"No IBKR data returned for {pair_name} {interval}")

    out = pd.concat(frames, ignore_index=True)
    out["Datetime"] = pd.to_datetime(out["Datetime"], utc=True)
    out = out.sort_values("Datetime")
    out = out.drop_duplicates(subset=["Datetime"], keep="last")
    out = out[(out["Datetime"] >= start_utc) & (out["Datetime"] <= end_utc)]
    out = out[["Datetime", "Open", "High", "Low", "Close", "Volume"]]

    pair_dir = output_root / pair_name
    pair_dir.mkdir(parents=True, exist_ok=True)

    path = pair_dir / f"{pair_name}_{interval}.csv"
    tmp = path.with_suffix(".csv.tmp")
    out.to_csv(tmp, index=False)
    tmp.replace(path)

    print(
        f"SAVED {pair_name} {interval} | rows={len(out)} | "
        f"{out['Datetime'].min()} -> {out['Datetime'].max()}"
    )
    print(f"FILE: {path}")

    return path


async def main_async(args) -> None:
    base, quote, pair_name = parse_pair(args.pair)

    end_utc = as_utc(pd.Timestamp.now(tz="UTC"))
    start_utc = end_utc - pd.DateOffset(years=args.years)

    output_root = Path(args.output_root).expanduser().resolve()

    ib = IB()
    print(
        f"Connecting to IB Gateway {args.host}:{args.port} "
        f"clientId={args.client_id} ..."
    )

    await ib.connectAsync(
        args.host,
        int(args.port),
        clientId=int(args.client_id),
        timeout=15,
    )

    try:
        contract = Contract(
            symbol=base,
            secType="CASH",
            exchange="IDEALPRO",
            currency=quote,
        )

        qualified = await ib.qualifyContractsAsync(contract)
        if not qualified:
            raise RuntimeError(f"IBKR could not qualify {base}/{quote}")

        contract = qualified[0]

        print(
            f"Qualified: {base}/{quote} | "
            f"conId={getattr(contract, 'conId', '')} | "
            f"exchange={getattr(contract, 'exchange', '')}"
        )

        requested = [x.strip().lower() for x in args.intervals.split(",") if x.strip()]
        bad = [x for x in requested if x not in BAR_CONFIG]
        if bad:
            raise ValueError(
                f"Unsupported interval(s): {bad}. "
                f"Supported: {', '.join(BAR_CONFIG)}"
            )

        saved = []
        for interval in requested:
            path = await download_interval(
                ib=ib,
                contract=contract,
                pair_name=pair_name,
                interval=interval,
                start_utc=start_utc,
                end_utc=end_utc,
                output_root=output_root,
                pacing_sleep=args.pacing_sleep,
            )
            saved.append(path)

        print()
        print("===== FOREX DOWNLOAD COMPLETE =====")
        for path in saved:
            print(path)

    finally:
        if ib.isConnected():
            ib.disconnect()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download IBKR spot FX historical OHLC data."
    )
    parser.add_argument("--pair", default="EURUSD")
    parser.add_argument("--years", type=int, default=1)
    parser.add_argument("--intervals", default="1d,4h,1h")

    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4002)
    parser.add_argument(
        "--client-id",
        type=int,
        default=41,
        help="Separate client ID from the stock/history/live pipeline.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument("--pacing-sleep", type=float, default=0.35)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.years <= 0:
        raise ValueError("--years must be greater than zero")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
