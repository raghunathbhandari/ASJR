# AlgoWithRenko — Locked Mechanical Rules (25 Nov 2026)

**Keep a fixed research baseline. Do not retroactively change it to fit results.**

1. Construct 15m OHLC using exactly three consecutive MES IBKR 5m candles, preserving actual UTC times. Reject missing/incomplete groups.
2. Initialize Renko on the first 15m close rounded to the 20-point grid. Continuation needs 20 points; **direction reversal needs 40 points**. Bricks are formed only after a completed 15m close (no provisional bricks).
3. On a new colour leg, wait for **brick 2 of that colour**. Before entry, examine the **two preceding completed legs**. If both are only one brick long, skip that entry as chop.
4. At the trigger candle close obtain Wilder RSI(14) and ADX(14) on the original 15m OHLC. Require **BUY RSI>=50 and ADX>=30**; **SHORT RSI>=20 and ADX>=30**. The RSI SHORT condition is >=20 intentionally, not <=20.
5. Submit next-bar market entry (simulation at the following completed 15m interval's OPEN). One contract/position at once. Do not fill at Renko drawn brick prices by assumption.
6. Stop is **20 points from the actual entry fill**. Check 5m highs/lows. Fill worse on a gap beyond stop; this occurred in September (-26 pts actual loss versus -20 planned).
7. In absence of a stop, close when the first opposite colour Renko brick is confirmed at a 15m close, executed next 15m open. Do not force fixed 1:1 target or prematurely exit same-colour trend.
8. After SL, wait for a qualifying fresh new leg; no re-entry within the same leg. At end of historical data, close open positions at last candle close, clearly label artificial end exit.
9. **Pure Renko comparison** disables RSI/ADX only, and retains all price, entry, chop, risk and exit rules. CLI flag: --filter none.
10. Always report trade count, winners/losers, win rate %, net MES points, gross $ for 1 MES ($5/point), profit factor, maximum closed-trade drawdown pts and actual gap-through stop fills.

Caveats: samples limited, partially optimized from October chart, no August MES data for September prior warm-up, November incomplete, no commissions, no tick-level stop-vs-reversal sequencing, no live validations.
