# MES v2 — Outcome first, fit structure rules second

Date: 2026-11-04. **User decision:** replay every existing v1 candidate (GOOD and WAIT) on genuine 5m MES IBKR data BEFORE fitting new market structure or liquidity filters. Preserve locked v1.

## Source code / run
- `three_candle/mes_v2_validate_all_outcomes.py`
- [Successful GitHub Actions run](https://github.com/raghunathbhandari/ASJR/actions/runs/41814938471)
- [Full signal-by-signal replay CSV and logs](https://github.com/raghunathbhandari/ASJR/actions/runs/41814938471/artifacts/13313079852)

## Replay methodology
MES 15m C3 timestamp denotes BAR START, hence entry eligible only C3 start +15 min. Assumed first contiguous 5m bar OPEN as entry, 5 MES index points SL, 10 points TP, first touched within 240 min (4h). If both brackets touched on one bar, mark ambiguous; if next 5m bar missing, mark unavailable. Ignore commission, slippage, executable fills, position overlap; **these are hypothetical signal outcomes, not real brokerage trades**.

## Real 29–30 Oct 2026 results
- 51 raw v1 core candidates, 50 resolved, 1 NO_NEXT_5M_BAR.
- **15 TP wins, 35 SL losses**, TP-first fraction **30%** of resolved.
- v1 GOOD: **1 TP and 1 SL** (30 Oct SELL 15:00 UK = SL; SELL 16:45 UK = TP).
- v1 WAIT: **14 TP, 34 SL**, one unavailable.
- Nominal gross sum across 50 independently considered resolved signals = 15×2R −35×1R = **−5R**, but this must NOT be presented as portfolio P&L due to overlapping entries and ignored costs.
- 2R/1R gross break-even fraction = 33.3%.

## Exploratory cross-tabs — TP/SL, unresolved excluded
- Side: BUY 5/18; SELL 10/17 (1 unavailable).
- Trend: BEARISH 9/18; BULLISH 4/9 (1 unavailable); RANGING 2/8.
- V patterns: V_BOTTOM_DEVELOPING 1/8; V_TOP_DEVELOPING 2/3 (1 unavailable); NONE 12/24.
- Events: BEARISH_BOS 3/5; BEARISH_CHOCH 1/2; BULLISH_BOS 1/1; BREAK_DOWN 2/4; BREAK_UP 0/2; NONE 8/21 (1 unavailable).

Some candidate events overlap or use the same C3; a V label can repeat, so these counts must NOT be treated as statistically independent. Do not claim shape or BOS causes profit. A 4h maximum hold and 5/10-point brackets are research assumptions, not user-approved execution rules.

## Mandatory research workflow
1. Replay and label every candidate TP / SL / ambiguous / unavailable (done for two days).
2. Compare rejected winners and rejected losers, and chart-review event/price context.
3. Freeze pre-declared hypotheses about structure, meaningful sweeps, V shapes, room-to-target.
4. Test on other date ranges without re-tuning using a fixed historical replay method; evaluate expectancy, transaction costs, overlap and session stratification.
5. ONLY after independent validation may a rule be proposed as a mandatory v2 filter. Never alter locked MES v1.

## VS Code/Jupyter (same folder, ALWAYS reload)

```python
import importlib
import mes_v2_validate_all_outcomes as replay
importlib.reload(replay)

records = replay.validate_all("2026-10-29", "2026-10-30")
replay.print_summary(records)
replay.save_csv(records)
```
