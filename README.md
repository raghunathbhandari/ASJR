# ASJR Trading

Research repository for ASJR trading strategies.

## Current strategy

**ASJR Small Repeatable V1**

Purpose: signal detection and visual validation first.

Current workflow:

1. Detect
2. Print
3. Analyse
4. Plot
5. Visually confirm good/bad signal locations
6. Refine only after chart review

Current 5-minute setup uses:

- Session VWAP
- EMA9 / EMA20
- Pullback into the EMA area
- Confirmation candle
- Break of confirmation high/low for entry
- Directional episode control
- Maximum first 2 signals per episode
- MFE / MAE diagnostics
- No capital or profit optimisation yet

## Run

From the repository root:

```powershell
python tests/test_small_repeatable.py
```

The default test runs QQQ over 30 days and plots the latest 12 signals.
