# RudraEMA5 V2 — Why the November 5-minute baseline lacks a demonstrated edge

Research date: 27 November 2026. COHR; IBKR TRADES extended-hours feed; 3,564 five-minute candles, 2 Nov through 27 Nov 17:55 GMT. All tests use the existing V2 entry/exit rules, a single open position, indicators warmed up on previous available bars, and day-end mark-out on UK calendar dates. No costs. No changes made to active V2 parameters.

## Baseline

70 trades; 30 winners, 40 losers; win rate 42.86%; gross +35.40815R from winners, -40R from losers, net -4.59185R, expectancy -0.06560R/trade, profit factor 0.8852. Average winner +1.18027R and average loss -1R; break-even win rate 45.87% before costs. Closed-trade cumulative-R peak-to-trough drawdown -11.17544R. R = 1% of entry price; not account return.

Of 40 losses, 29 were ordinary initial stop exits and 11 were stop-first entry-bar exits with unknown intrabar sequence. Two of these 11 bars also reached +1R in their recorded high. Four losing trades in total recorded a +1R high on the entry-through-exit bars (not necessarily while the trade was still open). 17 of 40 losers reached entry+1% in a subsequent bar within 60 clock minutes of exit. These are retrospective observations, NOT a justification for removing stops.

## Session attribution (existing baseline trades; entry timestamp, GMT)

| Entry time | Trades | Wins | Gross R |
|---|---:|---:|---:|
| 00:00–09:00 | 2 | 0 | -2.00 |
| 09:00–14:30 | 30 | 11 | -7.81 |
| 14:30–15:30 | 9 | 3 | -2.33 |
| 15:30–18:00 | 18 | 8 | +2.84 |
| 18:00–21:00 | 2 | 2 | +1.94 |
| 21:00–24:00 | 9 | 6 | +2.78 |

Normal regular session entry times 14:30–21:00: 29 trades, 13 wins, +2.44557R. Other hours: 41 trades, 17 wins, -7.03742R. 27 Nov was clipped at 18:00 UK. The baseline includes partial midnight UK dates, and session label is a clock-time proxy for available November data.

## RSI and swing attribution

| C1 RSI(14) | Trades | Wins | Net R |
|---|---:|---:|---:|
| <26 | 18 | 9 | +0.84 |
| 26–<30 | 19 | 8 | +1.14 |
| 30–<33 | 19 | 5 | -8.73 |
| 33–<36 | 14 | 8 | +2.16 |

All four observed swing-depth groups (2–<3%, 3–<4%, 4–<6%, >=6%) were negative. The 35 trades with EMA5 decline of at least 1% over 3 bars contributed -4.71R. A large decline or low RSI alone does not establish reversal. Baseline 10 Nov -4.059R (6 losses from 8); 24 Nov -3.639R (6 losses from 8).

## Independent full replays of candidate refinements

Each row is rerun from flat at each UK date, not simply removing trades from the ledger. Except for named change, keep V2. First/second halves are chronological diagnostics, not untouched holdouts, because the refinements were examined using November data.

| Variant | Trades | Wins | Win % | Net R | Nov 2–13 | Nov 16–27 |
|---|---:|---:|---:|---:|---:|---:|
| V2 baseline | 70 | 30 | 42.86 | -4.592 | -0.992 | -3.600 |
| Regular-hours entries only (14:30–21:00) | 29 | 13 | 44.83 | +2.446 | +2.939 | -0.494 |
| Entries 15:30–21:00 | 20 | 10 | 50.00 | +4.780 | +3.427 | +1.353 |
| RSI rising at C1: RSI(C1)>RSI(previous completed bar), still <36 | 23 | 14 | 60.87 | +8.644 | +7.819 | +0.826 |
| C1 high-low range >=0.25% of C1 close | 66 | 29 | 43.94 | -1.730 | +1.008 | -2.738 |
| Initial SL at/below C1 low | 46 | 21 | 45.65 | -3.134 | -4.041 | +0.907 |
| C2 closes above its EMA5 and entry trigger, buy C3 open | 29 | 15 | 51.72 | +3.482 | +3.026 | +0.456 |
| RTH entries + C2 close confirmation | 13 | 8 | 61.54 | +5.082 | +1.745 | +3.337 |
| 0.4% trail instead of 0.2% | 70 | 30 | 42.86 | -9.063 | -3.754 | -5.309 |
| 0.6% trail | 70 | 29 | 41.43 | -10.109 | -4.591 | -5.518 |
| 1% trail | 70 | 28 | 40.00 | -10.074 | -2.979 | -7.095 |

## Intrabar execution sensitivity

A separate piecewise-linear synthetic path replay for each OHLC bar tests two possible sequences: open-low-high-close (OLHC) and open-high-low-close (OHLC). Entry occurs only when the synthetic path actually crosses the trigger, stops and trail are updated along the path. Neither path is the true tape; they are scenarios, not rigorous bounds, and both omit bid/ask costs. No reentry in a bar after closing a trade.

| Variant | OLHC trades / wins / R | OHLC trades / wins / R |
|---|---|---|
| V2 | 68 / 33 / +5.974 | 70 / 34 / +6.563 |
| RSI rising | 23 / 15 / +11.215 | 23 / 15 / +10.880 |
| Entries 15:30–21:00 | 19 / 11 / +8.842 | 20 / 11 / +7.262 |
| RSI rising + 15:30–21:00 | 9 / 6 / +6.783 | 9 / 6 / +6.516 |

These results show the baseline profitability estimate changes sign with simulated intrabar mechanics. A 0.2% trail is especially vulnerable to 5-minute resolution and execution costs. Verify actual order of price touches with 1-minute data (preferably IBKR historical trades/ticks); lower resolution reduces but does not eliminate uncertainty.

## Research decision

Keep V2 unchanged. The most interesting **research hypothesis** is RSI turning upwards at the completed C1 while RSI remains below 36; this tests a reversal of momentum instead of simply oversold conditions. Evaluate it on untouched months, with commission, spread, slippage, and finer-resolution execution; the result here is in-sample and 23 trades are not a robust edge. Session filters are secondary hypotheses. Do not choose parameters from November outcomes and then claim independent validation on the same data.
