print("Thank you Cornor and AI !")

import importlib
import utils.asjr_small_repeatable_v1 as sr

importlib.reload(sr)

cfg = sr.make_config(
    pullback_lookback=4,
    pullback_tolerance_pct=0.15,
    entry_wait_bars=3,
    future_bars=40,
    cooldown_bars=8,
    regime_confirm_bars=3,
    max_signals_per_episode=2,
)

signals = sr.test_small_repeatable(
    ticker="QQQ",
    period="30d",
    cfg=cfg,
    print_signals=True,
    plot=True,
    max_plots=12,
)

print("\nSignals:", len(signals))
