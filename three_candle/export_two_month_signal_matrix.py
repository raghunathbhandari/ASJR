"""Rebuild one-row-per-signal NQ Sep-Oct metrics CSV from saved source files.

Run from repository root:
    python three_candle/export_two_month_signal_matrix.py
Then inspect and commit the resulting CSV. This never modifies strategy filters.
"""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import three_candle as strategy

OUTPUT = ROOT / "results" / "NQ_2026-09_10_signal_matrix.csv"
SOURCE = [ROOT / "data" / "NQ_2026-09_5m_UTC.csv",
          ROOT / "data" / "NQ_2026-10_5m_UTC.csv"]

def main():
    frames = []
    for path in SOURCE:
        d = pd.read_csv(path)
        d.index = pd.to_datetime(d.pop("Datetime_UTC"), utc=True)
        frames.append(d[["Open", "High", "Low", "Close", "Volume"]])
    raw = pd.concat(frames).sort_index()
    raw = raw.loc[~raw.index.duplicated(keep="last")]
    data = strategy.build_extended_nq_candles(raw, "2026-09-01", "2026-10-30", "15min")
    trades = strategy.backtest_breakout_reversals(
        data, min_c1_range_pct=0.0, min_c2_range_pct=0.0, r_floor_pct=0.20
    )
    research = strategy.build_signal_candle_research(data, trades)
    if trades.empty:
        raise RuntimeError("No signals detected")
    if research.empty:
        raise RuntimeError("No C1/C2/C3 research indicators available")
    header = trades.copy()
    header["signal_id"] = [
        f"NQ-SEP-OCT-{i+1:04d}" for i in range(len(header))
    ]
    header["status"] = header.max_r_before_sl.map(
        lambda r: "GOOD" if r >= 2 else "WEAK" if r == 1 else "BAD"
    )
    header["time_uk"] = header.trigger_time.apply(lambda x: x.tz_convert("Europe/London").isoformat())
    header["time_utc"] = header.trigger_time.apply(lambda x: x.tz_convert("UTC").isoformat())
    table = research.copy()
    # Pivot 3 separate C1/C2/C3 rows into a single wide record per signal.
    table["candle"] = table["candle"].astype(str)
    keep = [c for c in table.columns if c not in ("signal_id", "candle", "side")]
    wide = table.set_index(["signal_id", "candle"])[keep].unstack("candle")
    wide.columns = [f"{candle}_{field}" for field, candle in wide.columns]
    wide = wide.reset_index()
    combined = header.merge(wide, on="signal_id", how="left", validate="one_to_one")
    def v(row, candle, field):
        return pd.to_numeric(row.get(f"{candle}_{field}"), errors="coerce")
    def filter_name(row):
        return "BUY_BODY_WICK_SWEEP_V1" if row.direction == "BUY" else "SELL_SWEEP_RANGE_V1"
    def pass_filter(row):
        if row.direction == "BUY":
            return (v(row,"C3","Body_pct") >= .06 and
                    v(row,"C3","Wick_body_ratio") <= 1 and
                    v(row,"C2","Lower_wick_pct") >= .06)
        return (v(row,"C3","Upper_wick_pct") >= .05 and
                v(row,"C2","Range_pct") >= .12)
    combined["proposed_filter_name"] = combined.apply(filter_name, axis=1)
    combined["proposed_filter_pass"] = combined.apply(pass_filter, axis=1)
    # Avoid implying these are realized returns.
    combined["calculation_warning"] = "EXPOST_OHLC_TARGET_HITS_NOT_REALIZED_RETURN"
    front = ["signal_id","time_uk","time_utc","direction","status",
             "entry","sl","max_r_before_sl","highest_target_gain_pct",
             "proposed_filter_name","proposed_filter_pass"]
    front = [x for x in front if x in combined]
    combined = combined[front + [c for c in combined if c not in front]]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT, index=False)
    print(f"CREATED {OUTPUT} | {len(combined)} signals | {len(combined.columns)} columns")
    print(combined.groupby(["direction","status"]).size().to_string())
    print("FILTERED:", combined.groupby(["proposed_filter_pass","status"]).size().to_string())

if __name__ == "__main__":
    main()
