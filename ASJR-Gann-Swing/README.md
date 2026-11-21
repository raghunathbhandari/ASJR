# ASJR Gann Swing — V2 (latest), V1 preserved

**TradingView Pine Script v6 — candlestick overlay**

[V2 — Two-line Pine source](ASJR_Gann_Swing_V2.pine) · [V1 original](ASJR_Gann_Swing_V1.pine) · [Monk (Lama) colour guide](../Design/ASJR_Monk_Lama_Colors.md)

## Purpose

Show a configurable Gann-inspired swing chart over ordinary price candles. The indicator compares consecutive **completed** OHLC bars and counts qualifying bars in the opposite direction before identifying a new swing leg. It draws diagonal swing lines rather than moving averages, fixed-period fractal pivots or close-only zigzags.

## Inputs

- **Opposite bars required:** 1, 2 (default), or 3. A reversal requires that many eligible bars in the new direction.
- **Inside bars:** Ignore (default), or classify by the close versus the preceding close.
- **Outside bars:** Next bar (default: ignore the ambiguous bar and defer to the next qualifying bar), Follow trend, or Close direction. These are explicit **ASJR handling conventions**, not claims of exact Optuma cluster-rule equivalence.
- **Swing line colours:** Direction colours (Monk Saffron rising / Monk Vermilion falling), or single Monk Maroon; independent editable colours and width.
- **High/Low step:** Visible by default, independently toggleable; purple `#6765AE` by default, configurable colour and width. The High/Low *step* changes at the real **confirmation** bar, not retrospectively at a past pivot.
- **Show swing path**, optional confirmation triangles (off by default), and adjustable retained historical leg count.

## Interpretation

**Two overlay lines in V2:** (1) the diagonal **Gann Swing path**, default saffron up / vermilion down; (2) a separate **purple confirmed High/Low step line**, which holds the most recently confirmed pivot price horizontally and steps vertically to the next confirmed pivot value. Show/hide each independently, and adjust their colours and widths in settings.

A Gann Swing line connects swing extremes. Its active endpoint can extend as higher highs/lower lows form. **A reversal becomes known only when the required qualifying bars are complete.** On historical charts, the line's turn can appear on an earlier price-extreme bar than the confirmation itself. That is intended visual back-plotting, **not** a signal available at the earlier bar. Alerts and optional triangles are triggered exclusively on the confirming candle.

The Gann Swing price structure is a distinct research method from our Gann Date Square/time-cycle study.

## Test checklist

1. Paste the **V2 source** into TradingView Pine Editor and verify compilation.
2. Test 1-, 2- and 3-bar rules on 5m, 15m, 1H, 4H, and daily charts.
3. Manually check inside, outside, equal, and gap bars against the chosen interpretation.
4. Verify reversal triangles/alerts land on confirmation bars, never on the historical pivot bar.
5. Cross-check with a reference swing chart, allowing for differences in special-bar handling.

**Status:** Original V1 and V2 source written to GitHub; live TradingView compilation and cross-platform equivalence are not independently verified.

## Learning references

- [Optuma Gann Swing Chart Overlay](https://www.optuma.com/kb/tools/swings/gann-swing-chart-overlay/)
- [Optuma GANNSWING() documentation](https://www.optuma.com/kb/scripting/formulas-and-scripting-functions/gannswing-function/)
- [TradingView Pine Script v6: Lines and boxes](https://www.tradingview.com/pine-script-docs/visuals/lines-and-boxes/)

An original educational ASJR approximation inspired by public swing-chart concepts; not a certified recreation of any proprietary chart engine.
