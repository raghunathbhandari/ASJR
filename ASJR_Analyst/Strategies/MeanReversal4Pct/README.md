# 4% Mean Reversal

Core universe: MU, CAT, TSLA, AMAT, INTC, LRCX.

Signal reference is the previous completed DAILY close.

Chakra evaluates completed 5-minute bars during the active US session. The first
5-minute candle per ticker/day that closes at -4.00% or lower versus the
previous daily close triggers the watch alert.

Alert levels are calculated from the detected 5-minute close:
- SL: -1%
- TP: +4%

This is an alert/watch strategy. It does not place an order automatically.
