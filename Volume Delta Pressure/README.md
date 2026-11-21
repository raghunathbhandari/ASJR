# ASJR Volume Delta Pressure V2

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
