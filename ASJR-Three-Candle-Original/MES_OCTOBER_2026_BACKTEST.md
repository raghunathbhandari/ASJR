# MES October 2026 — Original ASJR Three-Candle applied to MES

Date of review: 2026-11-26 (UK). Source: `three_candle/data/MESZ2026_IBKR_5m_2026-10.csv` (MESZ2026, IBKR, 5-minute).

**Important:** This is a new independent research review of the *original equity pattern* on MES, NOT any of the previous NQ/MES futures variants. This report's first table was computed from the archived input bars by a separate data replay; the newly committed Python replay source has not yet undergone an independently executed end-to-end regression.

## Data / model
- 6,048 archived 5-minute rows. 22 complete US regular sessions (09:30–16:00 ET), 78 5-minute bars per session; 572 complete 15-minute candles.
- Original 15m C1/C2/C3 rules unchanged: bullish C2, lower wick > body, C2 low sweeps C1 low and C2 close reclaims it; C3 volume > C2 and C3 close > C2 close. Do not connect signals across dates.
- Original reference entry C2 close, structural stop C2 open, R step=max(C2 bullish body, 0.10% of C2 close). Ex-post target touches from C3 until session close ignore earlier stops.
- The MES dataset uses Datetime_UTC and includes extended hours; only US RTH is used in this review.

## A. Original retrospective target touches

| Target | Setups | Later target touched | Target touch rate | Illustrative minimum-step gross gain sum |
|---|---:|---:|---:|---:|
| 1R | 8 | 7 | 87.5% | +0.70% |
| 2R | 8 | 5 | 62.5% | +1.00% |
| 3R | 8 | 2 | 25.0% | +0.60% |

Illustrative gross sums use 0.10% per R for each target hit. These are **NOT** realized gains, net return, win rates, nor risk-adjusted gains. They ignore the C3-look-ahead conflict and whether initial stop was hit before target. Do not add 1R, 2R and 3R together.

| Signal date (NY) | C3 start (UK) | C2-close ref | C2-open stop | 1R touch | 2R touch | 3R touch |
|---|---|---:|---:|---|---|---|
| 2026-10-08 | 20:15 BST | 7808.75 | 7807.25 | Yes | No | No |
| 2026-10-13 | 20:00 BST | 7852.00 | 7850.50 | Yes | No | No |
| 2026-10-14 | 20:15 BST | 7753.50 | 7751.25 | Yes | Yes | No |
| 2026-10-16 | 18:30 BST | 7711.00 | 7709.25 | Yes | Yes | No |
| 2026-10-21 | 19:15 BST | 7807.50 | 7805.25 | No | No | No |
| 2026-10-27 | 17:00 GMT | 7755.25 | 7754.75 | Yes | Yes | No |
| 2026-10-28 | 18:30 GMT | 7769.00 | 7764.25 | Yes | Yes | Yes |
| 2026-10-30 | 19:00 GMT | 7575.25 | 7571.00 | Yes | Yes | Yes |

## B. Causal entry follow-up — first 5m open AFTER completed C3

**This entry is a new test rule, not the frozen original C2-close entry.**
- Once C3 has completed, enter LONG at next 5-minute open. C3's already-formed price action cannot be traded retroactively.
- Initial stop remains C2 open; R step=max(actual entry-to-stop distance, 0.10% of actual entry).
- Fixed 1R, 2R, 3R scenarios: existing stop checked first, then the specified fixed target. If neither hits by session close, exit at last RTH 5-minute close.
- Step-trailing scenario: on hitting +1R, +2R, +3R, etc., ratchet stop to the reached milestone for **subsequent 5-minute bars** only. Existing active stop checked first. Stop-market gaps are filled at bar open when worse than active stop.
- 1 MES point = USD 5. Prices and exits are hypothetical; costs, spread, commissions, slippage and tick ordering unmodeled. Candidates considered independently; same-day overlapping positions not capital-managed.

| Variant | Candidates | Positive exits | Negative exits | Positive exit rate | Gross points | Gross at 1 MES | Sum trade price returns |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed 1R target | 8 | 3 | 5 | 37.5% | -12.50 | -$62.50 | -0.1560% |
| Fixed 2R target | 8 | 3 | 5 | 37.5% | +3.75 | +$18.75 | +0.0581% |
| Fixed 3R target | 8 | 3 | 5 | 37.5% | -3.25 | -$16.25 | -0.0341% |
| Original-style step trailing | 8 | 3 | 5 | 37.5% | -1.00 | -$5.00 | -0.0045% |

The positive exit rate includes 5-minute **session-close exits** (not necessarily target fills); it is not a 1R/2R/3R target-hit rate. The sum of per-trade price-return percentages is not a portfolio return. Gross figures exclude all costs.

### Step-trailing per-signal replay

| Session | Next-5m entry | Stop at C2 open | Exit reason | Gross points |
|---|---:|---:|---|---:|
| 08 Oct | 7813.00 | 7807.25 | RTH close | +4.50 |
| 13 Oct | 7859.25 | 7850.50 | RTH close | -3.25 |
| 14 Oct | 7763.50 | 7751.25 | RTH close | +8.00 |
| 16 Oct | 7722.00 | 7709.25 | Stop | -12.75 |
| 21 Oct | 7810.00 | 7805.25 | Stop | -4.75 |
| 27 Oct | 7758.00 | 7754.75 | Stop | -3.25 |
| 28 Oct | 7781.50 | 7764.25 | Stop | -17.25 |
| 30 Oct | 7587.25 | 7571.00 | Trailing stop gap | +27.75 |
| **Total** | | | | **-1.00** |

**Key example:** 28 Oct's original retrospective scan shows a 3R price touch when measured against the earlier C2-close entry, but waiting until C3 finishes gives a later entry at 7781.50 and a simulated stop-out at 7764.25. We must not advertise the earlier target-touch as a profitable trade.

**Conclusion:** Applying the original equity pattern to October MES produced only 8 signals, and the original historic high target-touch percentages did not translate to profitable post-confirmation step trailing in this simulated month. Fixed 2R was marginally positive before any trading costs (+3.75 MES points); that is insufficient evidence of a robust edge.

## Reproduction command

Run from repository root with Python and pandas:

```bash
python ASJR-Three-Candle-Original/backtest_mes_october.py --verify-october --out /tmp/asjr_mes_october
```

Source: [backtest_mes_october.py](backtest_mes_october.py) and [original_three_candle.py](original_three_candle.py). Do not change the original Sep 2026 10-ticker benchmark when refining MES.
