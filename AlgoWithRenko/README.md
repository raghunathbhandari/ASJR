# AlgoWithRenko — ASJR MES 20-point Renko Swing Research

**Experimental, not live trading.** Research recorded 25 Nov 2026. MESZ2026: **1 MES = $5 per index point**.

This folder stores the confirmed 20-point strategy, the September pure-Renko comparison, the 1:1 and trailing-stop lessons, Python replay, tests and an actual-data-style October Renko entry/exit illustration.

## Selected research baseline (20-point bricks)

| Parameter | Rule |
|---|---|
| Data | IBKR 5m MESZ2026, aggregated to completed 15m OHLC |
| Renko | 20-point fixed bricks, 2-brick reversal, derived from completed 15m **closes** |
| Entry | **Second same-colour brick** after reversal, fill next 15m open |
| Chop | Skip if the **two preceding completed Renko legs both have <=1 brick** |
| BUY filter | RSI(14) >=50, ADX(14) >=30 |
| SHORT filter | RSI(14) >=20, ADX(14) >=30 (the exact user-specified threshold) |
| RSI/ADX source | Wilder-smoothed on underlying completed 15m candles |
| Initial stop | 20 MES points from executed entry, not from drawn brick |
| Exit | First opposite-colour confirmed brick, exit next 15m open; stop may exit earlier |
| Re-entry | No same-leg re-entry after stop; requires a fresh qualifying leg |
| Trading fees | Not included |

## Verified historical experiments (gross, 1 MES)

| Test | Period | Trades | Win rate | Net MES pts | Max closed-trade DD |
|---|---|---:|---:|---:|---:|
| **Selected RSI/ADX** | **Sep 2026** | **2** | **50%** | **-13.50** | **26.00** |
| Selected RSI/ADX | Oct 2026 | 2 | 50% | +71.50 | 7.50 |
| Selected RSI/ADX | Nov 1–6, 2026 | 2 | 50% | +121.00 | 12.25 |
| **Selected combined** | Sep–Nov 6 | 6 | 50% | **+179.00** | **26.00** |
| **Pure Renko, no indicators** | Sep 2026 | 8 | 37.50% | **+45.00** | **66.00** |

September-only testing has **no August warm-up**; October and November are warmed using earlier available data. November is only Nov 1–6. These settings have been examined against October and November, so they are **not independently out-of-sample validated**.

## Reproduce (run from repo root)

~~~bash
python AlgoWithRenko/backtest.py --month 2026-09 --filter rsi-adx
python AlgoWithRenko/backtest.py --month 2026-09 --filter none
python AlgoWithRenko/backtest.py --month 2026-10 --filter rsi-adx
python AlgoWithRenko/backtest.py --month 2026-11 --filter rsi-adx
python -m unittest discover -s AlgoWithRenko/tests -p "test_*.py"
~~~

Python standard library only. CSVs are read from the existing three_candle/data directory. The default pattern loads all available September–November MES files; for September the absence of August means September is initialized independently. Outputs include per-trade RSI/ADX and optional JSON file via --json-out. Trades are selected by **entry month**, and positions are forcibly marked at the last available candle if still open.

## Materials

- [Mechanical execution rules](STRATEGY.md)
- [Research diary, experiments and risk caveats](RESEARCH_LOG.md)
- [Backtest Python engine](backtest.py)
- [Offline smoke tests](tests/test_core.py)
- [October Renko brick/entry/exit chart](images/mes_october_20pt_renko.svg)

## Critical risks

Max **closed-trade** drawdown is not maximum mark-to-market drawdown. The September BUY at 7703.50 had planned stop 7683.50, but MES opened Sunday at 7677.50 and the stop filled **-26 points** rather than -20. A stop order does not guarantee execution price. Renko here is a synthetic **close-based** chart, not intrabar/provisional or tick-accurate Renko. Commissions, bid/ask, slippage, spread, leverage, maintenance margin, rollover and latency are excluded. There is **no trained predictive AI model**; this is AI-assisted rules research only.
