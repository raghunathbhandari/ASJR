# ThreeCandle relax mode v1 — NQ gain points and realized drawdown

2026-11-03. Inputs: `NQ_2026-09_10_V3_RAW_CANDIDATES_UNIFIED_MASTER.csv`, all 584 core candidates; simulated `netR`, `entry`, `exit_time_uk`. **Research replay only.**

### Method and limits

- NQ point contribution per trade approximated as **netR × entry × 0.002**. Differences from exact exchange-tick-based exit points are possible because persisted netR is rounded.
- Closed-trade maximum drawdown: the maximum prior peak less subsequent running cumulative **realized net points**, ordering closed trades by UK close timestamp. This does NOT capture intratrade floating drawdown.
- Capped replay: ascending signal C3 times; enter immediately after C3, one open trade at a time, max 4 trades/day, stop after 2 consecutive negative exits per UK day. Exit on existing master result. Entry times and exits are measured in UK calendar clock; DST transition handling and simultaneous fill ordering should be independently checked.
- Independent per-signal results also available; overlapping hypothetical trades are *not* executable with one position.
- No fees, spread, slippage, mark-to-market adverse excursions, or contract-level sizing. +NQ points across multiple trades is **not** a single continuous NQ price move or a portfolio's cash P/L.
- The comparisons are in-sample and selected after reviewing Sep–Oct; no out-of-sample performance claim.

### Capped replay (one position; max 4/day; stop after two consecutive losers)

| Profile | Sep trades | Sep net points | Sep maximum realized DD points | Oct trades | Oct net points | Oct maximum realized DD points | Combined trades | Combined net points | Combined max realized DD points | Combined net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Core raw | 74 | +1.75 | 677.00 | 72 | +688.26 | 501.75 | 146 | +690.01 | 677.00 | +11.23 |
| Body<0.10% | 70 | +838.75 | 491.00 | 67 | +25.26 | 623.75 | 137 | +864.01 | 623.75 | +14.58 |
| Body<0.10%; wick>=0.25; RVOL>=0.3 | 58 | +1306.25 | 370.75 | 67 | +666.27 | 312.50 | 125 | +1972.52 | 370.75 | +32.59 |
| **Body<0.10%; wick>=0.5; RVOL>=0.5** | 51 | **+1348.00** | 312.00 | 59 | **+1040.02** | 312.25 | 110 | **+2388.02** | 312.25 | **+39.56** |
| Body<0.10%; wick>=1 and <10 | 47 | +616.00 | 266.25 | 58 | +1519.76 | 296.24 | 105 | +2135.76 | 296.24 | +35.07 |

### Independent-signal (overlapping) comparison for reference

| Profile | Sep net points | Sep realized DD points | Oct net points | Oct realized DD points |
|---|---:|---:|---:|---:|
| Core raw | +2629.25 | 1081.50 | -671.24 | 1651.00 |
| Body<0.10% | +3419.50 | 657.75 | +1145.26 | 1105.50 |
| Balanced wick>=0.25, RVOL>=0.3 | +3305.50 | 530.75 | +1849.26 | 758.49 |
| Quality wick>=0.5, RVOL>=0.5 | +2406.25 | 354.25 | +1812.76 | 695.24 |
| Wick 1–10 | +1903.25 | 325.50 | +1909.99 | 477.75 |

Research selection: Quality leads capped net gain in this two-month sample, but the 110-trade count, execution and missing September zero-volume bars require more verification. Retain broad and balanced as separate variants. Do not replace original core or notebook.
