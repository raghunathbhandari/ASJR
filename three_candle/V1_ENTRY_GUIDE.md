# Rudra Three-Candle V1 — C2-body breakout entry (9 Nov 2026)

This is a **separate, executable-entry research variant** in `three_candle_v1.py`.
It does not change `three_candle_learing.py`, V4, the notebook, or historical CSVs.

## Entry known at decision time

1. Read consecutive IBKR 5-minute candles C1 and completed C2.
2. C2 must be bullish, have a lower wick larger than its body, sweep C1 low,
   and close above C1 low.
3. **Immediately after C2 closes**, place a stop-buy at the top of the C2
   body (= C2 close for bullish C2).
4. If C3 trades through that level, fill at the trigger, or at C3 open
   if C3 gaps above it. Do not wait for C3 close or enter at C4 open.
5. Initial structural stop is C2 open. Record the actual entry-to-stop
   distance, which can differ from 1R.
6. 1R = max(C2 bullish body, 0.10% of C2 close). On each completed 5-minute
   bar, if the high reaches a +nR milestone, ratchet the stop to that
   milestone (rounded down to a valid 0.25-point MES tick) **for later bars**.
   Stop gets priority over trailing updates within a bar.
7. Never run overlapping positions. Entries are BUY-only in this original
   bullish V1 pattern. Fees/slippage are excluded from gross points.

## Avoid lookahead

The C3 final volume and C3 close are **not available at the instant of a
C3 breakout**. Therefore they must not filter this causal entry.

For comparison, the result includes columns
`C3_volume_higher_research_only` and
`C3_close_higher_research_only`. These are research labels only, not trading
conditions. The 2026-10-25 archived 83/83/75/64 results **did require**
C3 confirmation and used a hypothetical earlier C2-close entry, so
their percentages are not directly comparable to executed V1 results.

A 5-minute OHLC candle does not reveal whether its high or low happened
first. If C3 both breaks the entry and hits C2-open stop, the simulator
conservatively books an initial-stop exit and flags
`Ambiguous_entry_stop=True`. These must be revisited with 1-minute/tick
data before live trading.

## Notebook call

From the existing `three_candle` notebook folder, without changing
`test_three_candle.ipynb`:

```python
import importlib
import three_candle_v1 as v1
importlib.reload(v1)

sep = v1.three_candle_v1("MESZ2026", "2026-09-01", "2026-09-30")
oct = v1.three_candle_v1("MESZ2026", "2026-10-01", "2026-10-31")
nov6 = v1.three_candle_v1("MESZ2026", "2026-11-06", "2026-11-06")
```

This new model needs verification against the local downloaded IBKR files
and realistic brokerage fees. Do not claim historical 1R price-touch rates
as executable success rates.
