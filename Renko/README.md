# ASJR Renko V1

A **TradingView Pine Script v6, timeframe-friendly Renko-style price overlay** for US equities and other symbols.

- **Source:** ordinary closed chart candles; use on **1m, 3m, 5m, 15m, 1H, 4H or daily** charts, subject to available market data.
- **Brick modes:** ATR (default, ATR 14 × 1.0), fixed price increment, or a percentage of price. ATR/percentage bricks adapt to the chart interval/price; **Fixed** is preferred when a constant brick height matters.
- **Direction:** continuation after one price increment; reversal requires **two increments**. A sufficiently large closed-candle move can make multiple bricks in one time-based candle.
- **Visuals:** green/red boxes superimposed on standard candles; optional synthetic close step line, optional candle fading and configurable brick transparency/history. No always-on text labels.
- **Confirmation:** Renko-brick EMA 9 and EMA 20 (they advance **per brick**, not per chart candle). Alerts fire only for a cross after at least 20 bricks, with both EMA slopes aligned by default.
- **Notifications:** add TradingView alerts using the script's BUY watch / SELL watch conditions, and set alert frequency to **Once per bar close**.

## How to install

1. Open [ASJR_Renko_V1.pine](ASJR_Renko_V1.pine), copy its entire source into TradingView **Pine Editor**, and add to chart.
2. Keep the **standard candlestick chart type**. Change TradingView's chart interval (e.g. **1m → 5m → 15m → 1H → 4H → 1D**) to recompute the overlay using that interval's completed candles.
3. For US stocks such as AMD/COHR, try **ATR** for automatic scaling; compare against **Fixed** to make brick heights consistent. These are research starting settings, **not optimized trade parameters**.
4. Use the existing **ASJR Gann Ideas** on the time-based chart for support/resistance, liquidity and entry location. A Renko signal is a **watch**, not an automatic entry. Wait for the confirmed 15m setup and use broker-real prices for stop/target.

## Important limitations

This is a **close-based Renko-style approximation**, **not** native TradingView Renko, tick-by-tick Renko, or a complete history of intrabar highs/lows. An indicator cannot recover the sequence of trades inside a 1-minute or 15-minute OHLC bar. Bricks that form within the same time-based candle occupy the same horizontal chart interval; they are not evenly spaced as in a standalone Renko chart. The very first reference close depends on the amount of history TradingView loads. ATR/percentage sizing can change brick height over time. A large gap exceeding *Max bricks per chart candle* will be processed over later chart candles. Brick history is also subject to TradingView drawing-object limits.

**No intrabar/projected alerts:** processing only closed time-based candles makes alert conditions stable at the chart interval, but a late chart close means a trade can already have moved significantly. Historical signals/brick prices must not be interpreted as actual executable fills. Backtest against actual tradeable prices, including gaps, spread and slippage, before considering live use.

**Validation status:** Source committed for research; Pine Editor compilation and live TradingView validation have **not** yet been independently confirmed. If TradingView reports a compiler message, verify it in Pine Editor before using alerts.

## Repository rule

New ASJR TradingView indicators get **their own folder**, a versioned **.pine** source file, a folder **README.md**, and a link from the repository root **README.md**.

*Research only. Not financial advice.*
