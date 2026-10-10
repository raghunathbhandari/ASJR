#!/usr/bin/env python3
"""Friday 2026-10-09 historical RudraScanner ONE-ROUND research replay.

Read-only default: use archived 5M OHLCV; missing WAP or contextual data
=> no verified setup. Optional --download-ibkr asks the user's EXISTING
Gateway (new unique clientId, no production process changes) for archived
5M TRADES OHLCV + actual IBKR bar average/WAP, including SPY, QQQ and
sector ETFs. No orders, no Discord, no Chakra restart, no Git push.

IMPORTANT SURVIVORSHIP/HINDSIGHT: The 30 test names include Saturday
research and Friday-after-close inputs, so results CANNOT be reported
as an unbiased Friday premarket discovery backtest. 6-bar fixed-horizon
markouts are illustrative, NOT the user's approved exit strategy.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from RudraScanner.features import build_scanner_features
from RudraScanner.patterns import PatternSettings, detect_five_patterns
from RudraScanner.topdown import ticker_etf_from_sources
from RudraScanner.discovery import read_ai_csv

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
TEST_DATE = "2026-10-09"

# Frozen exactly from user's verified Saturday source replay (not as-of-open).
FROZEN = {
    "FIXED": ("AKAM", "AMAT", "CRDO", "INTC", "MSFT", "ORCL",
              "QCOM", "SMCI", "WDC", "WTTR"),
    "AI": ("AAPL", "AMT", "AMZN", "HUM", "JPM", "LITE",
           "NVDA", "PLTR", "SPCX", "TMUS"),
    "IBKR_LEGACY_REPLAY": ("ASTS", "AXTI", "DDOG", "DE", "MRNA",
                           "SNOW", "SWKS", "T", "VZ", "ZS"),
}
FROZEN_TICKERS = tuple(symbol for group in FROZEN.values() for symbol in group)
assert len(FROZEN_TICKERS) == 30 and len(set(FROZEN_TICKERS)) == 30


def _folder(root, day):
    return Path(root) / "ASJR_Analyst" / "DataLake" / day


def _file(root, day):
    return _folder(root, day) / "raw" / "rudra_friday_ibkr_wap.csv"


def _timestamp(value):
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        raise ValueError("IBKR timestamp must include timezone")
    return ts.tz_convert("UTC")


def _ibkr_close_end(day):
    return datetime.combine(date.fromisoformat(day), time(23, 59),
                            tzinfo=ET).astimezone(UTC)


def _read_sector_map(root):
    """Only user-provided explicit AI ETF or unambiguous FIXED sector."""
    config = Path(root) / "ASJR_Analyst" / "config" / "ai_scanner_list.csv"
    ai_rows, _ = read_ai_csv(config, now=datetime(2026, 10, 10, 12, tzinfo=UTC))
    fixed = _folder(root, TEST_DATE) / "config" / "fixed_watchlist.csv"
    fixed_sector = {}
    if fixed.is_file():
        frame = pd.read_csv(fixed).fillna("")
        for row in frame.to_dict("records"):
            fixed_sector[str(row.get("ticker", "")).upper()] = str(row.get("sector", ""))
    rows = [{"ticker": ticker, "fixed_sector": fixed_sector.get(ticker, "")}
            for ticker in FROZEN_TICKERS]
    sectors = ticker_etf_from_sources(rows, ai_rows=ai_rows)
    return sectors


def backfill_ibkr(root, day, *, host, port, client_id, pause):
    """Sequential archived TRADES history from a connected IBKR Gateway.

    Calls only reqHistoricalData and qualifyContracts, never placeOrder.
    bar.average is the ib_async name of IBKR historical BarData.WAP.
    """
    from ib_async import IB, Stock

    if day != TEST_DATE:
        raise ValueError("This replay pins the verified 2026-10-09 universe")
    sector_etf = _read_sector_map(root)
    symbols = list(dict.fromkeys(
        [*FROZEN_TICKERS, "SPY", "QQQ", *sector_etf.values()]
    ))
    api = IB()
    try:
        api.connect(host, port, clientId=client_id, timeout=12, readonly=True)
        if not api.isConnected():
            raise ConnectionError("IBKR Gateway is not connected")
        collected = []
        failures = {}
        end = _ibkr_close_end(day)
        for i, symbol in enumerate(symbols, 1):
            try:
                contract = Stock(symbol, "SMART", "USD")
                qualified = api.qualifyContracts(contract)
                if len(qualified) != 1 or qualified[0].secType != "STK":
                    failures[symbol] = "UNVERIFIED_OR_AMBIGUOUS_STOCK_CONTRACT"
                    print(f"IBKR {i}/{len(symbols)} | {symbol} | CONTRACT_INVALID")
                    continue
                bars = api.reqHistoricalData(
                    qualified[0], endDateTime=end,
                    durationStr="3 D", barSizeSetting="5 mins",
                    whatToShow="TRADES", useRTH=False, formatDate=2,
                    keepUpToDate=False, timeout=25,
                )
                count = 0
                for bar in bars:
                    stamp = _timestamp(bar.date)
                    et_day = stamp.tz_convert(ET).date().isoformat()
                    if et_day > day:
                        continue
                    # Do not trust a synthetic price proxy for IBKR WAP.
                    wap = float(bar.average) if bar.average is not None else float("nan")
                    collected.append({
                        "Ticker": symbol, "Date": stamp.isoformat(),
                        "Open": float(bar.open), "High": float(bar.high),
                        "Low": float(bar.low), "Close": float(bar.close),
                        "Volume": float(bar.volume), "WAP": wap,
                    })
                    count += 1
                if count == 0:
                    failures[symbol] = "NO_HISTORICAL_BARS"
                print(f"IBKR {i}/{len(symbols)} | {symbol} | bars={count}")
            except Exception as exc:
                failures[symbol] = f"{type(exc).__name__}: {exc}"
                print(f"IBKR {i}/{len(symbols)} | {symbol} | ERROR: {exc}")
            # Rate-limit while preserving the user's production bot.
            if pause:
                api.sleep(pause)
        if not collected:
            return {"state": "NO_HISTORICAL_BARS", "failures": failures}
        data = pd.DataFrame(collected)
        data = data.sort_values(["Ticker", "Date"]).drop_duplicates(
            ["Ticker", "Date"], keep="last")
        destination = _file(root, day)
        destination.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(destination, index=False)
        metadata = {
            "source": "IBKR_HISTORICAL_TRADES_WAP_BAR_AVERAGE",
            "date": day, "requested_symbols": symbols,
            "rows": len(data), "tickers": data["Ticker"].nunique(),
            "failures": failures,
            "warning": "SATURDAY-SELECTED UNIVERSE; RETROSPECTIVE, NOT AS-OF-OPEN",
            "orders_sent": 0, "discord_sent": 0,
        }
        metadata_file = _folder(root, day) / "reports" / "rudra_friday_ibkr_backfill_status.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        metadata_file.write_text(json.dumps(metadata, indent=2)+"\n")
        metadata["file"] = str(destination)
        return metadata
    finally:
        if api.isConnected():
            api.disconnect()


def _previous_rth_close(features, day):
    """Last prior completed 15:55 ET bar close only; never Friday EOD peeking."""
    preceding = features[
        (features["session"] == "RTH") &
        (features["session_date_et"] < day) &
        (features["minutes_into_rth"] == 385)
    ].sort_values("datetime")
    if preceding.empty:
        return None
    latest_date = preceding["session_date_et"].iloc[-1]
    return float(preceding[
        preceding["session_date_et"] == latest_date
    ].iloc[-1]["close"])


def _direction(current_pct, qqq_pct, sector_pct, index_spy_pct):
    """Reconstruct contemporaneous SPY+QQQ+sector directional bias."""
    if any(pd.isna(x) for x in
           (current_pct, qqq_pct, sector_pct, index_spy_pct)):
        return "WAIT"
    if (current_pct > 0.20 and qqq_pct > 0.20 and
            sector_pct > 0.20 and sector_pct > index_spy_pct):
        return "LONG"
    if (current_pct < -0.20 and qqq_pct < -0.20 and
            sector_pct < -0.20 and sector_pct < index_spy_pct):
        return "SHORT"
    return "WAIT"


def _day_bars(frame, day):
    return frame[
        (frame["session"] == "RTH") &
        (frame["session_date_et"] == day)
    ].sort_values("datetime").reset_index(drop=True)


def replay_once(raw, root, day, *, hold_bars=6):
    """Walk the Friday RTH candles without using any future candle to signal.

    Entries: next available 5M candle open.
    Research markout: 6 *following* completed 5M bars, ending at close
    of index i+hold_bars (30-minute markout). No costs, spread, fills,
    fees, stops or slippage assumed. NOT the user's locked exit strategy.
    """
    if day != TEST_DATE:
        raise ValueError("Frozen tickers are only verified for 2026-10-09")
    if hold_bars < 1 or hold_bars > 36:
        raise ValueError("hold_bars must be 1..36")
    raw = raw[raw["Ticker"].astype(str).str.upper().isin(
        set(FROZEN_TICKERS) | {"SPY", "QQQ"} | set(_read_sector_map(root).values())
    )].copy()
    features, status = build_scanner_features(raw, now=pd.Timestamp(
        datetime.combine(date.fromisoformat(day),
                         time(23, 59), tzinfo=ET).astimezone(UTC)
    ))
    sectors = _read_sector_map(root)
    group = {ticker: data.sort_values("datetime")
             for ticker, data in features.groupby("ticker")}
    benchmarks = {}
    missing = []
    for ticker in {"SPY", "QQQ", *sectors.values()}:
        history = group.get(ticker)
        if history is None:
            missing.append(ticker)
            continue
        prior = _previous_rth_close(history, day)
        if prior is None or prior <= 0:
            missing.append(ticker)
            continue
        part = _day_bars(history, day)
        if part.empty:
            missing.append(ticker)
            continue
        part = part.set_index("datetime")
        benchmarks[ticker] = (prior, part)

    entries = []
    blocks = {"missing_wap": 0, "missing_sector_or_index": 0,
              "insufficient_rth_bars": 0, "no_future_exit_bar": 0}
    eligible_bars = 0
    for ticker in FROZEN_TICKERS:
        stock = group.get(ticker)
        if stock is None:
            continue
        day_frame = _day_bars(stock, day)
        if day_frame.empty:
            continue
        for i in range(len(day_frame)):
            candle = day_frame.iloc[i]
            if int(candle["minutes_into_rth"]) < 30:
                continue
            eligible_bars += 1
            if not bool(candle["vwap_ready"]):
                blocks["missing_wap"] += 1
                continue
            etf = sectors.get(ticker)
            if etf not in benchmarks or "SPY" not in benchmarks or "QQQ" not in benchmarks:
                blocks["missing_sector_or_index"] += 1
                continue
            stamp = candle["datetime"]
            pct = {}
            for sym in ("SPY", "QQQ", etf):
                prior, history = benchmarks[sym]
                previous = history.loc[history.index <= stamp]
                if previous.empty or previous.index[-1] != stamp:
                    # Missing a benchmark ETF's SAME completed 5M
                    # candle is stale context, not a valid as-of quote.
                    pct[sym] = float("nan")
                else:
                    pct[sym] = (
                        float(previous["close"].iloc[-1]) / prior - 1
                    ) * 100
            side = _direction(pct["SPY"], pct["QQQ"],
                              pct[etf], pct["SPY"])
            if side == "WAIT":
                blocks["missing_sector_or_index"] += 1
                continue
            # The underlying detector sees only the candles up to THIS
            # completed bar. No future data or future sector closes.
            section = day_frame.iloc[:i + 1]
            signals, health = detect_five_patterns(
                section, index_bias=side,
                sector_bias_by_ticker={ticker: side},
                settings=PatternSettings(enabled_for_research=True),
            )
            if not signals:
                if health["blocked_data"]:
                    blocks["insufficient_rth_bars"] += 1
                continue
            for signal in signals:
                if i + hold_bars >= len(day_frame):
                    blocks["no_future_exit_bar"] += 1
                    continue
                entry_bar = day_frame.iloc[i + 1]
                exit_bar = day_frame.iloc[i + hold_bars]
                if (entry_bar["datetime"] != stamp + pd.Timedelta(minutes=5)
                        or exit_bar["datetime"] != stamp
                        + pd.Timedelta(minutes=5*hold_bars)):
                    blocks["no_future_exit_bar"] += 1
                    continue
                price_in = float(entry_bar["open"])
                price_out = float(exit_bar["close"])
                signed_return = (price_out / price_in - 1) * 100 * (
                    1 if side == "LONG" else -1
                )
                entries.append({
                    "ticker": ticker, "pattern": signal["pattern"],
                    "direction": side, "signal_time_uk": str(candle["bar_time_uk"]),
                    "entry_time_uk": str(entry_bar["bar_time_uk"]),
                    "exit_time_uk": str(exit_bar["bar_time_uk"]),
                    "signal_close": float(candle["close"]),
                    "entry_next_open": price_in,
                    "exit_6bar_close": price_out,
                    "markout_pct_before_costs": round(signed_return, 4),
                    "sector_etf": etf, "index_pct_at_signal": round(pct["SPY"], 4),
                    "sector_pct_at_signal": round(pct[etf], 4),
                    "kind": "RETROSPECTIVE_30M_MARKOUT_NOT_LIVE",
                })
    trades = pd.DataFrame(entries)
    if trades.empty:
        trades = pd.DataFrame(columns=[
            "ticker", "pattern", "direction", "signal_time_uk",
            "entry_time_uk", "exit_time_uk", "signal_close",
            "entry_next_open", "exit_6bar_close",
            "markout_pct_before_costs", "sector_etf",
            "index_pct_at_signal", "sector_pct_at_signal", "kind",
        ])
    # Pattern labels can overlap on the exact same ticker/entry candle.
    # Distinct entry opportunities and the raw pattern hits are NOT
    # interchangeable. Keep the raw ledger unchanged for research but
    # calculate the independent-entry diagnostic separately.
    distinct = trades.drop_duplicates(
        subset=["ticker", "direction", "entry_time_uk"],
        keep="first",
    )
    distinct_count = len(distinct)
    pattern_stats = {}
    for name, group in trades.groupby("pattern", sort=True):
        marks = group["markout_pct_before_costs"]
        pattern_stats[str(name)] = {
            "signals": int(len(group)),
            "wins": int((marks > 0).sum()),
            "win_rate_pct": round(float((marks > 0).mean()) * 100.0, 2),
            "average_markout_pct": round(float(marks.mean()), 4),
        }
    summary = {
        "date": day,
        "state": "FRIDAY_RESEARCH_ONLY",
        "selection_hindsight": True,
        "ticker_selection_sources": {"FIXED": 10, "AI": 10,
                                     "IBKR_LEGACY_REPLAY": 10},
        "input": {"rows": status["completed_rows"],
                  "tickers": status["tickers"],
                  "wap_valid": status["exact_wap_rows"],
                  "rth_vwap_ready": status["vwap_ready_rows"],
                  "missing_benchmark_or_sector": sorted(set(missing))},
        "eligible_rth_ticker_bars": eligible_bars,
        "blocks": blocks,
        "research_signals_with_markout": len(trades),
        "distinct_entry_opportunities": distinct_count,
        "overlapping_pattern_labels": int(len(trades) - distinct_count),
        "distinct_entry_wins": int(
            (distinct["markout_pct_before_costs"] > 0).sum()),
        "distinct_entry_win_rate_pct": round(
            100.0 * float((distinct["markout_pct_before_costs"] > 0).mean()), 2
        ) if distinct_count else None,
        "distinct_entry_average_markout_pct": round(
            float(distinct["markout_pct_before_costs"].mean()), 4
        ) if distinct_count else None,
        "markout_bars": hold_bars,
        "win_rate_pct": round(
            100.0*(trades["markout_pct_before_costs"] > 0).mean(), 2
        ) if len(trades) else None,
        "average_markout_pct": round(
            float(trades["markout_pct_before_costs"].mean()), 4
        ) if len(trades) else None,
        "by_pattern": {k: int(v) for k, v in
                       trades["pattern"].value_counts().items()},
        "by_pattern_diagnostics": pattern_stats,
        "exit_definition": "NEXT_5M_OPEN_TO_CLOSE_AFTER_6_5M_BARS",
        "costs_included": False,
        "real_live_signals": 0,
        "discord_sent": 0,
        "warning": ("NOT A FULL UNBIASED BACKTEST; needs historical "
                    "ex-ante universe and locked exits; repeated entries "
                    "can overlap and signal-level markouts are not a "
                    "portfolio equity curve"),
    }
    return trades, summary


def main(argv=None):
    p = argparse.ArgumentParser(description="One-round Oct 9 retrospective RudraScanner research")
    p.add_argument("--date", default=TEST_DATE, choices=[TEST_DATE])
    p.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--download-ibkr", action="store_true",
                   help="Connect separately to an already running IB Gateway; requires API access")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=4002)
    p.add_argument("--client-id", type=int, default=91,
                   help="must be different from any live bot client ID")
    p.add_argument("--pacing-sleep", type=float, default=1.0)
    p.add_argument("--hold-bars", type=int, default=6)
    p.add_argument("--save", action="store_true",
                   help="write only namespaced research status and trades; no Git push")
    args = p.parse_args(argv)
    if args.pacing_sleep < .25:
        p.error("--pacing-sleep must be at least 0.25 seconds")
    try:
        if args.download_ibkr:
            print("IBKR HISTORICAL BACKFILL ONLY | read-only connection; no bot restart")
            try:
                result = backfill_ibkr(
                    args.repo, args.date, host=args.host, port=args.port,
                    client_id=args.client_id, pause=args.pacing_sleep)
            except Exception as exc:
                # A closed/weekend Gateway or denied market-data
                # permission is not a fake backtest success.
                print("IBKR HISTORICAL BACKFILL UNAVAILABLE:",
                      f"{type(exc).__name__}: {exc}", file=sys.stderr)
                return 2
            print(json.dumps(result, indent=2))
            if result.get("state") == "NO_HISTORICAL_BARS":
                print("No real IBKR WAP bars. No signal result is available.")
                return 2
        file = _file(args.repo, args.date)
        if not file.is_file():
            file = _folder(args.repo, args.date) / "raw" / "intraday_5m.csv"
            print("NO SAVED IBKR WAP BACKFILL: archived 5M OHLCV only (expected DATA_NOT_READY)")
        if not file.is_file():
            print("DATA NOT READY: Friday 5M CSV missing", file)
            return 2
        raw = pd.read_csv(file)
        trades, report = replay_once(raw, args.repo, args.date,
                                     hold_bars=args.hold_bars)
    except (OSError, ValueError, KeyError, ConnectionError) as exc:
        print("BACKTEST INPUT ERROR:", exc, file=sys.stderr)
        return 2
    print("RUDRA FRIDAY | HISTORICAL RESEARCH; NOT A LIVE SIGNAL OR UNBIASED BACKTEST")
    print("Source:", file)
    print(json.dumps(report, indent=2))
    if not trades.empty:
        print(trades.to_string(index=False))
    else:
        print("NO EVALUABLE SIGNALS: see blockers above, not 0 losing trades")
    if args.save:
        reports = _folder(args.repo, args.date) / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        jsonfile = reports / "rudra_friday_round_status.json"
        csvfile = reports / "rudra_friday_round_markouts.csv"
        jsonfile.write_text(json.dumps(report, indent=2) + "\n")
        trades.to_csv(csvfile, index=False)
        print("Saved research-only:", jsonfile, csvfile)
        print("No Discord, no orders, no Git stage/push, no production files overwritten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
