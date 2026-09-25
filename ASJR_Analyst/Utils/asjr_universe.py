import pandas as pd
from Utils import asjr_watchlist as watchlist
from Utils import asjr_ibkr as ibkr

def load_gapup_csv(path):
    df = pd.read_csv(path)
    return ibkr.normalize_gapup(df)

def _align_columns(frames):
    cols = []
    for df in frames:
        for col in df.columns:
            if col not in cols:
                cols.append(col)

    aligned = []
    for df in frames:
        x = df.copy()
        for col in cols:
            if col not in x.columns:
                x[col] = None
        aligned.append(x[cols])

    return aligned

def build_universe(trade_date=None, gapup_df=None):
    fixed = watchlist.load_fixed_watchlist(trade_date).copy()
    fixed["source"] = "WATCHLIST"

    hot = watchlist.load_hot_sector_watchlist().copy()
    hot["source"] = "HOT_SECTOR"

    frames = [fixed, hot]

    if gapup_df is not None and not gapup_df.empty:
        gap = ibkr.normalize_gapup(gapup_df).copy()
        gap["source"] = "GAPUP"
        frames.append(gap)

    frames = _align_columns(frames)
    out = pd.concat(frames, ignore_index=True)

    grouped = []
    for ticker, g in out.groupby("ticker", sort=False):
        row = g.iloc[0].copy()
        sources = sorted(set(g["source"].dropna().astype(str)))
        row["source"] = "+".join(sources)
        grouped.append(row)

    return pd.DataFrame(grouped).reset_index(drop=True)
