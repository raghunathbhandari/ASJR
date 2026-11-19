# ASJR Renko V2 — Timeframe Friendly

[**Current Pine Script V2**](ASJR_Renko_V2.pine) · [Previous V1](ASJR_Renko_V1.pine) · [Back to ASJR home](../README.md)

**What changed in V2:** V1's narrow one-bar boxes and always-on cyan/orange EMA lines made daily charts appear as *step lines rather than Renko bricks*. V2 defaults to **wide, wickless green/red synthetic Renko candles**, disables EMA lines by default and sets the ATR multiplier to **0.50** (tune it by ticker/timeframe). Optional individual-sized boxes can be time-split inside each original bar.

## Timeframes and brick construction

- Runs on **standard, time-based TradingView charts**: 1m, 3m, 5m, 15m, 1H, 4H, 1D and other supported chart intervals. No native Renko chart type is required.
- Processes **completed chart candle closes** only. It does not use an imagined high/low order within each candle, and it does not generate unfinished-bar signals.
- **ATR / Fixed / Percent** sizing. ATR 14 × 0.50 is a visibility-oriented starting point, not a proven best parameter. Fixed uses constant price-unit increments. ATR and Percent sizes can vary when the source price/volatility changes.
- **Continuation** needs one new brick size. **Reversal** needs a two-brick price move before the first opposite brick is printed.
- Large movements may generate several synthetic bricks on a single original chart bar. Up to 50 per bar by default; beyond the limit, the residual movement can be caught up on later bars.

## Choose the display in indicator settings

| Render mode | What you see | Best for |
| --- | --- | --- |
| **Wide Renko candles** (default) | A wide, wickless, coloured synthetic price body on a time candle that creates one or more bricks. If multiple bricks form, the single wide body **aggregates** them. | Clear visibility on daily, 4H, 15m or 5m. |
| **Individual brick boxes** | Actual per-brick-height rectangles horizontally divided across the time-bar slot. | Inspecting the number and sizes of completed bricks. |
| **Both** | Wide synthetic body plus individual boxes. | Debugging and comparing the two views. |

**Important:** Bricks do not appear on every time bar, because Renko is **price-driven**. An absence of a new block means no whole Renko brick formed by that completed time candle. On a daily chart, a larger ATR threshold deliberately gives fewer blocks than on a 1-minute chart. Adjust ATR multiplier or use Fixed to inspect sensitivity. If the underlying chart is too visually prominent, leave **Fade original price candles = ON**, or hide the symbol's candle series in TradingView. Plotting an indicator over a time-based chart cannot change the chart's time axis into a true equal-width, brick-index axis.

**About multiple bricks within one source bar:** V2 positions the individual boxes at *artificial, evenly divided positions* inside that bar's timestamp interval for presentation. These are **not exact intrabar formation times**. Use Wide mode for the cleanest time-aligned overlay.

## EMA confirmation and alerts

Synthetic EMA9 and EMA20 advance **per completed brick**, not per source time candle. EMA lines are **off by default** so the bricks remain visible. Turning on the slope filter requires EMA9 and EMA20 to both rise for a bullish cross or both fall for a bearish cross. Historical bars use their final close; real-time signals are generated after the actual source candle is confirmed.

Alert conditions: **ASJR Renko V2 - BUY watch** and **ASJR Renko V2 - SELL watch**. In TradingView choose **Once Per Bar Close**; this indicator is a *watch/confirmation tool*, not an automatic order or a backtested trading strategy. For ASJR, confirm a trade with the original time-based price candles, Gann levels, structure and risk/SL.

## Installation

1. Open [ASJR_Renko_V2.pine](ASJR_Renko_V2.pine), copy into TradingView Pine Editor and add the indicator to a **standard candlestick** chart.
2. Select **1m / 5m / 15m / 1H / 4H / Daily** from the chart timeframe picker. Each timeframe independently recomputes its own close-based bricks.
3. Leave the default **Wide Renko candles** display and **Plot brick EMAs = OFF** for the clearest chart. Compare fixed brick sizes and ATR multipliers to your instrument.
4. If needed, switch to **Individual brick boxes** to inspect discrete steps. Do not treat the visual x positions of those boxes as real formation timestamps.
5. Use the alert conditions only after visually validating on your chart. V1 is preserved for comparison.

## Accuracy and validation limitations

This is an **approximation**, not TradingView's native Renko construction, tick-by-tick bars or true synthetic Renko timestamps. It uses only completed OHLC **closes**, so real intrabar swings are missing. The baseline depends on how much chart history loads. Synthetic prices and indicator alert points are not executable fills. ATR-adjusted brick sizes complicate comparison with conventional constant-size Renko; select Fixed if constant-height Renko is required.

**Validation status:** The Pine v6 source is committed, but it has **not been independently compiled or visually tested inside TradingView**. The next check is loading V2 in Pine Editor and verifying AMD/COHR on 1m, 5m, 15m and 1D; any compile/runtime errors should be corrected before trading or enabling alerts.

## ASJR repository rule

Each new TradingView indicator lives in its own GitHub **folder**, includes a **versioned .pine** source and **folder README**, and has a link from the main **README.md**.

*Research/educational use; no financial advice.*
