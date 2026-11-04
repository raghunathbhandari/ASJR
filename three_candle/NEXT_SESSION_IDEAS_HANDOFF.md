# THREE-CANDLE — SHARED STANDARD AND NEXT-SESSION HANDOFF

Updated 2026-11-04 (UK). **Applies to EVERY Three-Candle strategy:** MES, MNQ, NQ, GC, INTC, and future instruments/versions. This is a cross-strategy user-approved contract, not MES-specific.

## 1. LOCKED PUBLIC METHODS AND CALL FLOW

```python
result = three_candle_signal(tiker, datefrom, dateTo)
plot_candidates(result)
plot_signal_passed(result)
```

**Do not rename these public functions, change their input conventions, or swap the chart types in a future version without explicit user approval.** New versions may provide their own implementations, but preserve this interface. The `result` must retain everything both plotters need (all core candidates, GOOD/WAIT classification, metadata, and historical candles).

## 2. LOCKED NINE METHOD STAGES

Ordered internal analysis methods:

1. `candle_detect_core()` — C1/C2/C3 BUY and SELL hypotheses independently, C2 liquidity sweep and C3 confirmation. Keep ALL CORE-TRUE results even if filters later reject them.
2. `market_structure()` — confirmed swing HH/HL/LH/LL, bullish/bearish/range context, no future data.
3. `swing_sr_lines()` — confirmed swing support/resistance and nearby price levels.
4. `volume_detect()` — volume, relative volume and confirmation participation.
5. `wicks_detect()` — C2 rejection wick and last-five-candle wick congestion.
6. `daily_range_check()` — developing futures session range, previous completed session and directional room to go.
7. `display_other_metrics()` — diagnostic candle and technical indicator measurements for analysis.
8. `higher_timeframe_support()` — confirm higher-timeframe contextual direction using only closed candles.
9. `Liquidity_area_detect()` — identify historical liquidity/sweep areas, without treating OHLC as actual institution order data.

The scanner processes candles in chronological `for` loops and evaluates BUY/SELL separately. Market structure must inform direction and quality; a wick pattern alone is not proof of trend.

## 3. LOCKED CHART DESIGN

- `plot_candidates(result)`: **ONE full-range dark candlestick chart** of ALL CORE-TRUE candidates with **PURPLE dots on their C2 sweep candles** (below BUY C2, above SELL C2). Green/red candles; confirmed swing S/R; **EMA20 in gold**, **EMA200 in lavender/purple**; UK date/time. Do NOT turn this into one chart per candidate.
- `plot_signal_passed(result)`: **ONE focused detailed chart PER GOOD candidate**, clearly label C1/C2/C3, C2 highlighted, **ENTRY blue**, **SL red**, **TP purple**, numeric prices, confirmed swing S/R, **EMA20 gold / EMA200 lavender**, UK time and surrounding price action. Multiple pages may be exported as a PDF.
- Reference prices and simulated fills must be explicitly distinguished. The charts do not by themselves prove trade profitability.
- Keep these visual rules consistent between instruments and versions unless changed by explicit instruction.

## 4. DATA AND WARM-UP

Use instrument-appropriate available local CSV data (IBKR 5-minute CSV preferred where available), merge monthly history by timestamp, resample only complete 15-minute candles, use UTC for processing and Europe/London for labels. **Read earlier historical CSV bars BEFORE filtering to the requested dates**. Calculate EMA20/EMA200 and other indicators on full chronological history, never on only visible chart candles. EMA200 is unavailable until 200 bars have closed; show N/A rather than an inaccurate immediate value. Do not add Yahoo/IBKR network dependencies without a specific need and approval.

## 5. USER-REQUIRED SIGNAL PRINTING

`three_candle_signal()` prints each signal regardless of GOOD or WEAK/WAIT:
- signal number, UK date/time, BUY/SELL, price, GOOD/WEAK/WAIT;
- true/false and required/informational status for **each of the nine methods**;
- separate candle quality checks; clear rejection reasons;
- **ALL available metrics / indicators**, as in original `three_candle_learing.py` learning approach;
- study-only versus mandatory filters are clearly distinguished.

Diagnostic inventory from first learning version: C1/C2/C3 OHLC+volume, candle range/body/wicks %, sweep in ticks/points, C3/C2 volume ratio, RVOL20, EMA20/EMA200 distance and EMA20 slope, RSI14, ATR14, BB20 width, session VWAP/distance, prior20 high/low and sweep, rolling 10/20 range, price approach/recovery, confirmed S/R room, session time classification, current/previous futures-session range. More ideas can be discussed, but should not become mandatory checks automatically.

## 6. CODE WRITING STANDARD — MANDATORY ACROSS STRATEGIES

- Python must be **human-readable and easy to edit**, not clever/over-abstracted; descriptive variables, simple loops, and clear separation between core/structure/filters/metrics/plotting.
- Comment all major code blocks to explain purpose and reasoning; add docstrings for every named method.
- Group settings/thresholds near top; document units and defaults.
- Preserve audit trail for every candidate including failed ones; no hindsight/lookahead/repainting.
- Do NOT edit original notebooks, source data, old masters, or unrelated strategy versions without authorization.
- Prefer adding an isolated new research version rather than breaking an old one.

## 7. FUTURE SESSIONS — IDEAS FIRST, NOT UNREQUESTED IMPLEMENTATION

**Next session should focus on trading ideas, chart evidence and structure validation** rather than re-discussing the established API and plot formats. Transfer only approved research concepts between strategies. New signal logic, thresholds, files, or plotting changes require explicit user direction. Clearly differentiate implemented, proposed, and runtime-validated functionality. Avoid claiming backtest results without replaying historical data.

## 8. CURRENT MES REFERENCE AND VERIFICATION

Current MES research code:
- `three_candle/mes_relax_pipeline_v1.py`
- `three_candle/mes_relax_structure_first_v1.py`
- Detailed historical working notes: `three_candle/MES_RELAX_V1_CORE_AND_RESEARCH_HANDOFF.md`
- Input MES CSV files: `three_candle/data/MESZ2026_IBKR_5m_2026-09.csv`, `2026-10.csv` (both full filenames start MESZ2026_IBKR_5m_).

Current MES quality hypotheses: C2 directional wick >=2x body; sweep >=2 MES pts; strong C3 directional close; WAIT if >=2 of last 5 candles have excessive both-sided wicks. Independent market structure alignment is in current experimental code. These parameters are NOT validated cross-instrument defaults.

The GitHub changes have been committed. **Python compile/execution and chart generation still require verification** after local/VPS sync:
```bash
cd /root/trading/ASJR
git fetch origin
git merge --ff-only origin/main
python3 -m py_compile three_candle/mes_relax_pipeline_v1.py
python3 three_candle/mes_relax_pipeline_v1.py --date 2026-10-29 --plot-both --show-wait
```
