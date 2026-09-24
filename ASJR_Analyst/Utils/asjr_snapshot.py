import pandas as pd

def _safe_merge(left, right, on="ticker"):
    if left is None or left.empty:
        return right.copy() if right is not None else pd.DataFrame()
    if right is None or right.empty:
        return left.copy()
    return left.merge(right, on=on, how="left")

def build_ticker_summary(universe_df, intraday_summary=None, daily_summary=None):
    out = universe_df.copy()

    if intraday_summary is not None and not intraday_summary.empty:
        out = out.merge(intraday_summary, on="ticker", how="left")

    if daily_summary is not None and not daily_summary.empty:
        d = daily_summary.copy()
        keep = [c for c in ["ticker","close","ema20","dist_ema20_pct","atr14","volume"] if c in d.columns]
        d = d[keep].copy()
        d = d.rename(columns={
            "close":"daily_close",
            "ema20":"daily_ema20",
            "dist_ema20_pct":"daily_dist_ema20_pct",
            "volume":"daily_volume",
        })
        out = out.merge(d, on="ticker", how="left")

    if "exchange" in out.columns:
        out["tradingview_url"] = out.apply(
            lambda r: f"https://www.tradingview.com/chart/?symbol={str(r.get('exchange','NASDAQ')).upper()}:{r['ticker']}",
            axis=1
        )
    else:
        out["tradingview_url"] = out["ticker"].apply(
            lambda t: f"https://www.tradingview.com/chart/?symbol=NASDAQ:{t}"
        )

    return out.reset_index(drop=True)

def build_snapshot_dict(trade_date, ticker_summary, sector_summary=None):
    return {
        "trade_date": str(trade_date),
        "ticker_count": int(len(ticker_summary)) if ticker_summary is not None else 0,
        "tickers": [] if ticker_summary is None else ticker_summary.where(pd.notna(ticker_summary), None).to_dict(orient="records"),
        "sectors": [] if sector_summary is None else sector_summary.where(pd.notna(sector_summary), None).to_dict(orient="records"),
    }
