# Rudra-Gann — INTC 30-day premarket research

**Experiment:** 23 October–21 November 2026 (30 calendar days).  
**Daily snapshot:** approximately 10:00 Europe/London; 23 October is the initial snapshot created in chat, with subsequent runs scheduled at 10:00 UK.  
**Ticker:** NASDAQ:INTC. **Time zone:** Europe/London. **Price currency:** USD.

## Locked inputs and reproducibility

1. **Fixed price anchor for entire experiment:** regular-session low of **22 October 2026 = USD 84.64**, from CoinGlass/Investing historical pages. Do not change it after observing future price action.
2. **Square of Nine (modern rotation convention; not claimed as a verified exact formula in Gann's own writing):** `L(theta) = (sqrt(84.64) + theta / 180)^2`. The levels are a *hypothesis under test*, not stock forecasts.
3. **Angle rows:** -90°, -67.5°, -56.25°, -45°, -33.75°, -22.5°, -11.25°, 0°, +11.25°, +22.5°, +33.75°, +45°, +56.25°, +67.5°, +90°. Fractions/subdivisions are experimental; keep fixed.
4. **Percentage to level:** `100 * (L(theta)/previous_regular_close - 1)`. Percentages are distances from the last completed US market regular-session close; this reference value changes daily, while the price anchor stays fixed.
5. **Last confirmed direction (descriptive, not a forecast):** if last completed daily bar's HIGH and LOW are both strictly higher than previous completed bar's HIGH and LOW, label `UP`; both strictly lower => `DOWN`; otherwise `MIXED`. This is a **simplified two-bar price-structure classifier** for research, not claimed to be Gann's exact patented swing algorithm.
6. **Current-session direction:** mark `PENDING` until that day has actually traded. Do not infer a forecast from planets or the last confirmed direction.
7. **Planet positions:** Swiss Ephemeris (Moshier fallback), geocentric tropical ecliptic longitudes, **10:00 Europe/London** every day (check BST/GMT automatically). Compute smallest interplanetary separation `min(|a-b|, 360-|a-b|)`; identify 0°/45°/60°/90°/120°/180° aspects only if within **3°** orb. Planetary angles are measurements, not automatically UP/DOWN signals; Friday/Venus is a tradition, not a tested conversion rule.
8. **Gann price-time 1x1:** leave `NOT_CALCULATED` until a historically grounded price unit per day and origin point are fixed **before** the test. No free selection to fit prices.
9. **Testing:** A level is touched if the verified subsequent actual *regular-session* high-low range crosses it, or if the nearest range boundary is within 0.25% of the level. Touch does NOT equal reversal. Mark a reversal only if a timestamped sequence of intraday prices establishes a move >=1% *after* touching the level within two trading sessions. If timestamped intraday data missing, mark `UNVERIFIED`, never a success.
10. **Baseline:** prior day actual high/low (same touch measurement). Keep daily historical context and report successes and misses, including the baseline.
11. **No hindsight edits:** save the pre-session snapshot with creation timestamp; future result updates may append an evaluation but must never overwrite the pre-session values. Days when US market is closed: planetary snapshot only and `MARKET_CLOSED` for trading observation.

## Output files

- `daily/YYYY-MM-DD.md`: immutable pre-session formula inputs, measured planets, derived levels and direction status. Add future outcome sections separately.
- `records.csv`: compact per-date rolling 30-day tracker with state and distances.
- All file writes must occur via the authenticated **GitHub connector** to `raghunathbhandari/ASJR`, branch `main`, not a simulated write. Verify tool success. If inaccessible, do not claim the day was saved.

## Initial market-source references

- https://www.coinglass.com/stocks/INTC
- https://it.investing.com/equities/intel-corp-historical-data
- https://astrolog-app.com/en/ephemeris
- https://www.astro.com/swisseph/

**Research only.** W.D. Gann's historically documented work and modern reconstructions must be distinguished, and no astronomical angle is presumed to have predictive power for INTC.
