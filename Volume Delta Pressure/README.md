# ASJR Volume Delta Pressure

## V3 — RSI confirmation (latest)

[ASJR Volume Delta Pressure V3 + RSI](ASJR_Volume_Delta_Pressure_V3_RSI.pine)

**New feature:** one Pine indicator displays **RSI in its own lower pane** (native 0–100 scale), while the **original twelve price-zone pressure cells, EMA21 anchor/glow, EMA9 and EMA200** continue to overlay the price candles using `force_overlay = true`. The chart dashboard now also displays the RSI value. Existing volume-pressure logic and EMA calculations are unchanged.

### RSI settings
- Default RSI length **14**, source **close**
- Default line **purple**, width **2**, independently adjustable
- Guide lines at **70 (overbought), 50 (midpoint), 30 (oversold)**; overbought and oversold thresholds are editable, and all guide lines can be hidden
- RSI line can be turned on/off without changing the underlying pressure data

### Suggested use (not automatic trade signals)
Check whether an EMA9/EMA21 trend reversal and support/resistance reaction is backed by rising RSI above 50 and improving estimated buying pressure (reverse for short setups). RSI >70 is not automatically a sell signal. ASJR volume-pressure values are OHLCV estimates, **not** exchange-verified aggressor delta.

**TradingView setup:** Because V3 intentionally changes `overlay` from true to false to place RSI in a proper lower pane, remove the old instance and **add V3 as a fresh indicator**. Otherwise an existing TradingView instance might retain its previous pane placement.

**Validation:** The Pine source was structurally checked; compilation and real-chart display must still be confirmed in TradingView. V2 is retained unchanged for comparison.



This TradingView Pine Script v6 overlay estimates buying/selling pressure using candle structure and OHLCV over 12 price cells. It does **not** represent exchange-reported bid/ask volume delta.

## Indicator
[ASJR Volume Delta Pressure V2](ASJR_Volume_Delta_Pressure_V2.pine)

## Moving averages
- **Existing EMA21:** remains the pressure anchor; original green/red slope colouring and glow are retained. The pressure profile calculation still uses the EMA21 anchor.
- **EMA 1:** enabled by default at length **9**, colour **orange** (`#E59B23`), width **2**.
- **EMA 2:** enabled by default at length **200**, colour **blue** (`#3676C8`), width **3**.

In **Settings → Inputs → Additional EMAs**, independently choose visibility, period, colour and line width (1–4) for each new EMA. They appear as chart overlays and do not alter the pressure calculations.

## Source / licence
This adaptation preserves the source notice crediting Zeiierman's Rolling Candle Profile and the **CC BY-NC-SA 4.0** terms. Original copyright and licence information appears at the top of the Pine source.

**Validation:** Source edited and structurally checked; Pine Editor compilation and live TradingView plotting have not been independently verified.
