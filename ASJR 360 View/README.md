# ASJR 360 View V4 — RE10140 fix

**Current test version:** [ASJR 360 View V4 Pine Script](ASJR_360_View_V4.pine).

## V4 change: respect TradingView's 64-plot ceiling

The actual TradingView screenshot for V3 reported **RE10140: 66 plot counts (limit 64)**. My earlier plot-count estimate was wrong. TradingView [documents](https://www.tradingview.com/pine-script-docs/writing/limitations/) that each dynamic `plotcandle()` uses multiple plot counts, while `line.new()` uses **zero** plot counts.

**Fix:** retain 11 historical `plotcandle()` pressure bands and render **the 12th pressure cell** as a vertical `line.new()` drawing, using the **same p11–p12 boundaries and exact cell colour**. All 12 pressure bands and pressure mathematics remain active. The script should now be **approximately 61 plot counts**, below 64. This is an estimate from the observed 66 and the removed candle plot, not a TradingView-verified count.

**Trade-off:** the 12th band's vertical lines are retained for **up to 500 recent eligible bars** because TradingView caps line drawings; the other 11 candle plots cover all available chart history. The user-facing table, dynamic EMA21, EMA9/EMA200, RSI, RVOL5/20 and optional alerts are unchanged.

V1, V2 and V3 remain preserved for reference. **V4 has not been independently compiled or executed inside TradingView.** Please load V4 as a new indicator and share the exact error screenshot if anything else appears.

## Earlier notes and documentation

# ASJR 360 View V3 — RVOL function fix

**Use the latest source:** [ASJR 360 View V3 Pine Script](ASJR_360_View_V3.pine).

## What V3 fixes

V2 incorrectly called `rv.averageAtTime(volume, rvolLen5, rvolAnchor, isCum)` and the corresponding 20-session call with a timeframe **string** as the third argument. TradingView's official `RelativeValue/4` library requires the third argument to be a **series bool anchor**, such as `timeframe.change("1D")`. V3 passes `isNewAnchor = timeframe.change(rvolAnchor)` to both functions, preserving the selected daily anchor's intended behaviour.

- All original **12 price-zone pressure formulas** and strict **trend + pressure + RSI** green/red/grey rules remain unchanged.
- RVOL5/20 remain *reference only*. Same TradingView-style time-of-session baseline and optional cumulative or regular mode.
- V2's plot-budget fix is retained: 12 zone candles, 3 EMA plots, no glow; optional alerts via `alert()`.
- V1, V2 and the original Volume Delta Pressure V2 remain intact in GitHub.
- **Not yet independently compiled in TradingView's Pine Editor.** If the chart does not load, capture the **exact error text and line number** rather than guessing a new fix.

## Prior documentation

# ASJR 360 View V2 (plot-budget fix)

**Recommended version:** [ASJR 360 View V2 Pine source](ASJR_360_View_V2.pine). This is an attempt to resolve the TradingView loading error observed in V1. It is not yet verified by a live TradingView Pine Editor run.

- Preserves 12 original zone plots, EMA9, dynamic EMA21, EMA200, RSI and time-based RVOL5/20 dashboard; original pressure mathematics unchanged.
- Reduces the expected TradingView plot count to the 64-count maximum by omitting the optional EMA21 glow and replacing two `alertcondition()` plots with `alert()` calls.
- **Optional alerts:** enable the new `Enable state-change alerts` setting and create a TradingView alert with **Any alert() function call**. Choose Both / Green only / Red only in the indicator settings.
- V1 and Volume Delta Pressure V2 files remain available unchanged.

## Previous V1 documentation


A **new, separate TradingView Pine Script v6 overlay** for intraday chart confirmation. The existing `Volume Delta Pressure/ASJR_Volume_Delta_Pressure_V2.pine` is **not modified**.

- [Open ASJR 360 View V1 Pine source](ASJR_360_View_V1.pine)
- [Original Volume Delta Pressure V2](../Volume%20Delta%20Pressure/ASJR_Volume_Delta_Pressure_V2.pine)

## Visual design
- **On the main price chart**: three separately configurable EMAs (9, 21, 200 by default) plus the original 12 estimated pressure-zone candles.
- **The EMA21 / pressure anchor line becomes a dynamic 360 confirmation line**: GREEN for strict bullish alignment, RED for strict bearish alignment, GREY for disagreement or unavailable pressure.
- **One slim horizontal table**, with **ASJR 360 | Trend | Pressure | RSI | RVOL 5 | RVOL 20 | 360 Line**. No separate panes or RSI/RVOL lines.
- Mild-dark background and thin frame; independently change dashboard visibility, any of TradingView's 9 table positions, tiny/small/normal text, background/transparency/text/border colour.
- Show/hide each EMA line and the pressure zones separately.

## Exact colour logic (from completed bars)
The price of the 360 line is the EMA pressure anchor, **21** periods by default. Its colour is determined by **trend + existing 12-zone estimated pressure + RSI**, and held at the previous confirmed colour until the realtime bar closes.

| Confirmation | GREEN | RED |
| --- | --- | --- |
| Trend | EMA9 > EMA21; **both** slopes rising | EMA9 < EMA21; **both** slopes falling |
| Original 12-zone pressure | At least 8 bullish zones **and** estimated buying share >= 60% | At least 8 bearish zones **and** estimated buying share <= 40% |
| RSI | RSI14 >= 55 **and rising** versus prior bar | RSI14 <= 45 **and falling** versus prior bar |

If any condition fails, profile is inactive, or data is insufficient, the line is **GREY**. Thresholds and EMA/RSI lengths are editable. This is **not** an automatic entry; the EMA9 crossover, Gann area, completed confirmation candle, stops and potential reward need separate evaluation. The colour can remain green after a confirmed crossover without requiring a fresh crossover every bar.

**Source-preservation:** V1 copies the V2 12-zone pressure estimation formula unchanged. Its basis remains OHLCV candle bodies, close location, volume and wick estimates. **This is not real exchange bid/ask delta.** The original pressure plots' visibility can be changed without disabling their calculations.

## RVOL5 and RVOL20 — at Time, references only
Both use the **official TradingView RelativeValue/4 library** `averageAtTime()` at corresponding time offsets from the daily anchor; the same method is run separately across **5** and **20** preceding anchor periods. Defaults are daily anchor, **Cumulative**; alternate mode is **Regular**, both editable.

| RVOL | Display colour | Meaning |
| --- | --- | --- |
| > 1.00x | Green | Above same-time historical average |
| = 1.00x | Grey | Exactly average |
| < 1.00x | Red | Below historical average |
| N/A | Grey | Insufficient history, zero denominator, or unsupported chart/anchor pairing |

RVOL never changes the 360 line colour and is **not BUY/SELL direction**. The dashboard reads the most recently **completed** bar. TradingView's chart session choice controls whether premarket/after-hours is present; select a **regular-session chart** for regular-session-only volume comparisons. Mixing extended and regular data can make session-based values differ. This indicator does not claim to separate those sessions automatically.

Daily anchor must be larger than chart timeframe. On daily or higher timeframes (with a daily anchor), RVOL is N/A until a valid higher anchor is selected. At least `length` historical completed anchor periods are required before showing its value. TradingView data availability and historical depth can affect comparisons.

For background:
- [TradingView Relative Volume at Time documentation](https://www.tradingview.com/support/solutions/43000705489-relative-volume-at-time/)
- [TradingView RelativeValue library](https://www.tradingview.com/script/cZnSLls2-RelativeValue/)

## TradingView usage
1. Open the [Pine source](ASJR_360_View_V1.pine), copy into TradingView **Pine Editor**, and add to your chart.
2. Choose 5m/15m for intraday trading; adjust EMA9/21/200 colours/widths/visibility.
3. For the dashboard, adjust **Show dashboard**, **Position**, **Font size**, and mild-dark styling.
4. Confirm a Gann/market-structure price location and a completed candle rather than treating a line colour change as a trade.
5. Two optional alert conditions: first confirmed GREEN bar and first confirmed RED bar after a different status.

## Historical MES replay

[12-month MES 5m/15m backtest (Nov 2025–Oct 2026)](MES_15M_5M_BACKTEST_2025-11_TO_2026-10.md): 70,689 IBKR 5-minute bars; under a one-contract ATR 1R-stop/2R-target test, all tested V1 colour-change variants lost money after assumed costs. The line is **confirmation only**, not a validated standalone entry strategy.

## Validation and limitations
- Source created and structurally checked; **TradingView Pine Editor compilation and live-chart plotting are not independently verified**.
- This is research/confirmation, not a trading system, guaranteed edge or order-placement strategy.
- If the chart's EMA21 crosses the middle of the candle body, the original pressure profile may not draw; this is expected and means the pressure filter cannot confirm a direction on that bar.
- Historical-pressure estimates are price-derived and not independent of RSI/EMA price action.

## Attribution / licence
The pressure-zone layout derives from Zeiierman's *Rolling Candle Profile*. The existing source notice credits the original work and states **Creative Commons CC BY-NC-SA 4.0**; this derivative retains that notice and the same licence. The optional public TradingView `RelativeValue/4` library remains provided/owned by TradingView and is imported rather than copied.
