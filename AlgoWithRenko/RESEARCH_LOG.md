# Research diary — 25 November 2026

Sources: IBKR MESZ2026 5m UTC OHLC under three_candle/data. Sep has 6,024 five-minute rows / 2,008 complete 15m candles. Oct has 6,048 / 2,016. November 1–6 is partial-period data.

## Iterations tested (gross 1 MES, points)

| Idea | Date | Trades | Win % | Net pts | Closed DD pts |
|---|---|---:|---:|---:|---:|
| Original 20pt first reversal, SL20, exit reversal | October | 15 | 26.67 | +20.00 | 91.75 |
| Same entry, fixed 1:1 take profit at +20 | October | 15 | 46.67 | -8.00 | 40.00 |
| Same entry, after +20 activate trailing 20pt, protect +1 | October | 15 | 46.67 | +4.50 | 40.00 |
| 20pt **second brick + chop**, pure Renko | October | 11 | 36.36 | +90.25 | 87.25 |
| 20pt **second brick + chop**, pure Renko | Nov 1–6 | 7 | 42.86 | +297.25 | 25.75 |
| **Selected** 20pt second brick + chop + RSI/ADX | September | 2 | 50.00 | -13.50 | 26.00 |
| **Selected** 20pt second brick + chop + RSI/ADX | October | 2 | 50.00 | +71.50 | 7.50 |
| **Selected** 20pt second brick + chop + RSI/ADX | Nov 1–6 | 2 | 50.00 | +121.00 | 12.25 |
| **Pure Renko** 20pt second brick + chop, no indicators | **September** | **8** | **37.50** | **+45.00** | **66.00** |
| 10pt brick / 10pt SL, with selected RSI/ADX | October | 5 | 0.00 | -50.00 | 50.00 |
| 10pt brick / 10pt SL, with selected RSI/ADX | Nov 1–6 | 5 | 20.00 | -18.50 | 30.00 |

- **Visual lesson:** A later +20 target hit on Renko does not mean a live entry was profitable. At least five of October's first-brick trades hit their -20 stops before eventually reaching their +20 targets. A 1:1 picture without sequencing is not a valid backtest.
- **Chop:** Waiting for a second new-colour brick sometimes avoided early false reversals; skipping the entry when both prior colour legs were a single brick was helpful in the October sample. This is not a proof of predictive power.
- **RSI/ADX:** On 11 Oct second-brick + chop trades, all RSI50 values were already directionally aligned. Adding ADX>=30 and user's BUY RSI>=50, SHORT RSI>=20 cut trades to 2 in Oct and 2 in early Nov, increasing selectivity but excluding big winners (+92.25 Oct short, +209.75 Nov short).
- **Brick size:** With the RSI/ADX rules held fixed, switching to 10pt bricks generated losing tests in both periods, even with 20pt stops. User chose 20pt.
- **September gap:** 11 Sep BUY 7703.50, initial stop 7683.50; Sunday 13 Sep first 5m OPEN 7677.50 -> **-26.00 pts**. This is why low reported closed-trade DD must not be called guaranteed safety.
- **September pure Renko** separate fixed-rules check: 8 trades, 3 wins, 5 losses, +45 pts, PF1.42, max closed DD66. Largest BUY winner +125.50, and one -26 gap loss.

## September pure Renko trades (UTC)

| Entry | Side | Net pts |
|---|---|---:|
| Sep 03 13:00 | BUY | +13.00 |
| Sep 08 08:00 | SHORT | -20.00 |
| Sep 11 12:30 | BUY | -26.00 |
| Sep 13 22:15 | SHORT | -20.00 |
| Sep 17 00:45 | BUY | +125.50 |
| Sep 23 16:30 | SHORT | +12.50 |
| Sep 25 07:30 | BUY | -20.00 |
| Sep 28 15:00 | SHORT | -20.00 |

## Validation limits

Synthetic 15m-close Renko, not true 5m/tick event Renko. No August MES dataset in current repository folder; initial Renko level and indicators from September only for September tests. Earlier October/November data participated in rule selection, so these are **development tests**, not unseen out-of-sample results. Gross points omit fees/spread, slippage except explicit 5m gap stop handling, actual fill latency, margin and rollover. AI in strategy name denotes assisted study, NOT a trained model.
