"""Bridge new shared tickers to locked 1H Rudra-Reversal state safely.

The original BB(20,2) and 150-bar detector logic is NOT modified.
Newly discovered stock names are seeded from their latest COMPLETED
historical 1H bar to avoid replaying weeks of old entries into Discord.
"""
from __future__ import annotations

from pathlib import Path


def seed_new_symbols(trade_date, tickers, *, state_file=None):
    """Seed only previously untracked 1H names. Preserve pending alerts.

    Never silently seed symbols without >=150 completed 1H candles.
    Return explicit diagnostics. Do not fetch data or create alerts.
    """
    from ASJR_Analyst.Strategies.RudraReversal1H import rudra_reversal as rr
    path = Path(state_file) if state_file is not None else rr.STATE_FILE
    state = rr._load_state(path)
    if not isinstance(state, dict):
        raise ValueError("Invalid Rudra-Reversal state")
    tracked = state.setdefault("last_seen_bar", {})
    added, not_ready, already = [], [], []
    for ticker in dict.fromkeys(str(t).strip().upper() for t in tickers):
        if ticker in tracked:
            already.append(ticker)
            continue
        bars = rr._load_ticker_1h(ticker, trade_date)
        if len(bars) < 150:
            not_ready.append(ticker)
            continue
        stamp = bars.iloc[-1]["datetime"]
        tracked[ticker] = stamp.tz_convert(rr.UK).isoformat()
        added.append(ticker)
    if added:
        rr._write_json_atomic(path, state)
    return {"state": "SEEDED" if added else "NO_NEW_READY_SYMBOLS",
            "seeded": added, "not_ready_150h": not_ready,
            "already_tracked": already, "alerts_created": 0}
