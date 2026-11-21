# ASJR Design System — Monk (Lama) Colours

**Chosen as the default ASJR colour reference on 21 November 2026.**

The user's inspiration images show Buddhist monks in maroon and saffron robes, with monastery textiles and prayer flags. The five solid swatches in the first image have been sampled as the primary ASJR palette.

| Token | Hex | RGB | Typical use |
| --- | --- | --- | --- |
| Monk Maroon | `#6B231A` | 107, 35, 26 | Main line / deep accent |
| Monk Vermilion | `#C43212` | 196, 50, 18 | Falling / warning direction |
| Monk Slate | `#8B9499` | 139, 148, 153 | Neutral and reference lines |
| Monk Saffron | `#F7A801` | 247, 168, 1 | Rising / primary highlight |
| Monk Light Gold | `#F6CC5F` | 246, 204, 95 | Secondary highlight and labels |

**Additional explicit chart colour:** swing high/low step line purple `#6765AE` (103, 101, 174), sampled approximately from the supplied Gann swing reference.

## Rules for new ASJR TradingView indicators

1. **Default to the Monk (Lama) Colours** where the semantic meaning and chart readability permit.
2. Expose **`input.color` controls** so every main plotted line/candle colour can be overridden by the user.
3. Do not force monk colours over an explicit user colour requirement (example: purple confirmed High/Low step line).
4. Maintain adequate contrast on light and dark TradingView themes. Users can change any default.
5. When fixed green/red status semantics are required, follow the specific indicator's approved contract rather than silently changing status meaning.
6. Update this guide when the user approves a new official colour, preserving existing colour definitions for comparison.

## ASJR Gann Swing V2 defaults

- Diagonal swing **up:** Monk Saffron `#F7A801`
- Diagonal swing **down:** Monk Vermilion `#C43212`
- Optional diagonal **single colour:** Monk Maroon `#6B231A`
- Confirmed High/Low **stepped line:** Purple `#6765AE`
- All colours and line widths are adjustable in TradingView settings.

This is a project design convention, not a religious or historical claim about prescribed Buddhist colour values.
