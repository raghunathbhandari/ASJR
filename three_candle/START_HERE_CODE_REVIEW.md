# START HERE — Reviewing Rudra Strategy Python Code

Updated 31 October 2026. **Only comments were added to the existing Python strategy files**. Trading conditions, thresholds, executions, and calculations were not intentionally changed.

## Gold V2 (independent)

1. [`gold_v2_frozen_three_reference.py`](gold_v2_frozen_three_reference.py) — Start here to understand the **three 30 October reference trades**. Sections: input + reference C2 times; body-edge entry with WICK stop; confirmed swing trailing; output. Historical benchmark: 3/3 observed a later +0.20% favourable price move, 2/3 positive simulated exits, **+2.5764% gross summed historical gain**.
2. [`gold_v2_monthly_frozen_replay.py`](gold_v2_monthly_frozen_replay.py) — October monthly replay of the **same frozen Gold method**. Sections: load/detect; trade loop; swing trail; monthly summary and 30 October consistency assertion. VPS-confirmed historical result: 27 detected, 26 simulated entries, 14 wins, 12 losses, **53.85% simulated win rate, +5.8591% summed gross gain**. Within 0.20% initial wick-stop risk: 8 trades, −0.0016% summed gross gain.
3. [`detect_gold_v2_swings.py`](detect_gold_v2_swings.py) — 15m C2 turning-area detector. Adjustable detection thresholds: lookback, ATR depth/range, C1/C3 body ratio. **C3 confirmation only known after C3 closes**.
4. [`research_gold_v2_early_body_cross.py`](research_gold_v2_early_body_cross.py) — **Different experimental version:** C2 BODY-edge entry and opposite BODY-edge stop, ambiguous 5m order handling. Do **not** compare/merge its return numbers with the frozen wick-stop benchmarks.

## Rudra NQ Three-Candle V2 (independent, not Gold)

1. [`three_candle.py`](three_candle.py) — Existing NQ three-candle setup/detection and separate target research. Section 04: setup rules. Section 04B: breakout entry research. Section 06: ex-post touches.
2. [`export_two_month_signal_matrix.py`](export_two_month_signal_matrix.py) — **Simplest NQ V2 filter-editing location:** `pass_filter(row)`. BUY: C3 body >=0.06%, C3 wick/body <=1.0, C2 lower wick >=0.06%; SELL: C3 upper wick >=0.05%, C2 range >=0.12%. It also prints a fixed summary.
3. NQ Sep+Oct research: 821 raw signals, 198 filtered, 130/198 (65.66%) observed >=1R, 65/198 (32.83%) observed >=2R. These are **ex-post target-reach rates**, not proven realised winning trades. Do not quote scenario gross gain until the revised exporter is rerun and verified on VPS.

## Repeatable SSH checks

```bash
cd /root/trading/ASJR-Synced
git pull --no-rebase --no-edit origin main

# First: syntax check for the documented files
/root/trading/venv_new/bin/python -m py_compile \
  three_candle/gold_v2_frozen_three_reference.py \
  three_candle/gold_v2_monthly_frozen_replay.py \
  three_candle/research_gold_v2_early_body_cross.py \
  three_candle/detect_gold_v2_swings.py \
  three_candle/export_two_month_signal_matrix.py \
  three_candle/three_candle.py

# Gold single-day reference regression
/root/trading/venv_new/bin/python three_candle/gold_v2_frozen_three_reference.py --date 2026-10-30

# Gold monthly baseline / built-in single-day regression
/root/trading/venv_new/bin/python three_candle/gold_v2_monthly_frozen_replay.py --month 2026-10

# NQ V2 matrix + stable research summary
/root/trading/venv_new/bin/python three_candle/export_two_month_signal_matrix.py
```

## Safe editing workflow

- **Change one parameter at a time** and record it in the relevant independent strategy notes; never quietly alter a frozen reference benchmark.
- First check `-m py_compile`, then run the frozen one-day and monthly regression before publishing new performance.
- If the 30 October Gold monthly regression differs from **+2.5764%**, stop and review. That is a version mismatch indicator.
- Keep `c3_confirmed` timing explicit. A C2-body entry executed **during C3** must not use the later C3 close as a prerequisite in a causal live simulator.
- **1R is entry-to-stop risk**, not automatically +0.20%. Price going +0.20% at any later point is not the same as realised 1R.
- Sum of trade % is not an account return. Portfolio overlaps, sizing, fee, slippage and futures multiplier require separate modelling.

More detailed session handoff: [AI_SESSION_HANDOFF_2026-10-31.md](AI_SESSION_HANDOFF_2026-10-31.md).
