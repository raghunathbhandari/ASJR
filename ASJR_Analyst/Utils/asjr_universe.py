import pandas as pd
from Utils import asjr_watchlist as watchlist
from Utils import asjr_ibkr as ibkr

def load_gapup_csv(path):
    df = pd.read_csv(path)
    return ibkr.normalize_gapup(df)

def build_universe(trade_date=None, gapup_df=None):
    fixed = watchlist.load_fixed_watchlist(trade_date).copy()
    fixed["source"] = "WATCHLIST"

    if gapup_df is None or gapup_df.empty:
        return fixed.reset_index(drop=True)

    gap = ibkr.normalize_gapup(gapup_df).copy()
    gap["source"] = "GAPUP"

    for col in fixed.columns:
        if col not in gap.columns:
            gap[col] = None
    for col in gap.columns:
        if col not in fixed.columns:
            fixed[col] = None

    cols = list(dict.fromkeys(list(fixed.columns) + list(gap.columns)))
    out = pd.concat([fixed[cols], gap[cols]], ignore_index=True)

    # Prefer GAPUP label if ticker appears in both groups, but retain note.
    grouped = []
    for ticker, g in out.groupby("ticker", sort=False):
        row = g.iloc[0].copy()
        sources = sorted(set(g["source"].dropna().astype(str)))
        row["source"] = "+".join(sources)
        grouped.append(row)

    return pd.DataFrame(grouped).reset_index(drop=True)
