# Rudra Three-Candle — September + October 2026 learning and filter proposal

**Scope:** NQ futures 15m extended-hours, resampled from archived 5m. 821 retrospective candidates (Sep 401; Oct 420). Recorded outcome classes: GOOD=2R or more before initial stop, WEAK=1R only, BAD=below 1R; R floor=max(actual entry-stop distance, 0.20% of entry). September 80/70/251 GOOD/WEAK/BAD; October 93/88/239; total 173/158/490.

## Findings from full two-month matrix (in-sample, do not claim live predictive validity)

BUY 340 (69 GOOD, 79 WEAK, 192 BAD): most promising GOOD-vs-BAD metrics:
- C3 body%: median GOOD 0.0862 vs BAD 0.0272; in-sample discrimination AUC 0.773
- C3 lower-wick/body: 0.255 vs 1.088; AUC 0.735 (lower favorable)
- C3 total-wick/body: 0.716 vs 2.161; AUC 0.730 (lower favorable)
- C2 lower-wick %: 0.0807 vs 0.0497; AUC 0.718
- C2 full range %: 0.1612 vs 0.1079; AUC 0.703

SELL 481 (104 GOOD, 79 WEAK, 298 BAD):
- C3 upper wick %: median GOOD 0.0536 vs BAD 0.0341; AUC 0.654
- C2 range %: 0.1428 vs 0.1149; AUC 0.614
- C2 body %: 0.0720 vs 0.0514; AUC 0.595
- SELL trigger is C4 and C4 body/MA9 deserves future research.

All signal metrics retained for evaluation: C1,C2,C3 OHLCV, candle range/body/upper/lower wick%, upper/lower/total wick-to-body ratios, ATR14 and ATR%, ADX14, RSI14, SMA9/SMA20/SMA200 signed distance%, RVOL5 cumulative, ASJR modeled 12-zone B/S/N activity/pressure and buy share. RVOL/ADX/RSI/ASJR raw levels showed substantial GOOD/BAD overlap. ASJR from OHLCV is **not** real bid/ask delta. Missing data stays blank, not zero.

## Experimental filters, NOT installed in production

BUY: C3 bullish body >=0.06% of price AND C3 total wick/body <=1.0 AND C2 lower wick >=0.06% of price.
SELL: C3 upper wick >=0.05% of price AND C2 full range >=0.12% of price.

Filter evaluation on the **same** Sep-Oct dataset used to identify these ranges (overfit risk):

| Set | Signals | GOOD | WEAK | BAD | Reached 1R+ |
|---|---:|---:|---:|---:|---:|
| Original BUY | 340 | 69 | 79 | 192 | 43.5% |
| Filtered BUY | 63 | 25 | 27 | 11 | 82.5% |
| Original SELL | 481 | 104 | 79 | 298 | 38.0% |
| Filtered SELL | 135 | 40 | 38 | 57 | 57.8% |
| **Original combined** | **821** | **173** | **158** | **490** | **40.3%** |
| **Filtered combined** | **198** | **65** | **65** | **68** | **65.7%** |

By month filtered BUY: Sep 28 (13/10/5), Oct 35 (12/17/6) GOOD/WEAK/BAD.
By month filtered SELL: Sep 44 (12/15/17), Oct 91 (28/23/40).

Average **maximum favourable underlying price change**, not net realized gain: original combined approx +0.303% per signal; filtered BUY +0.516%, SELL +0.427%, combined ~+0.455% per signal. Summed favourable excursions ~+90.1 percentage points (not an account return). Previously discussed **+12.4%** is a purely indicative **1R wins/losses × fixed 0.20% per trade** shortcut ((130-68)*0.20%), not a verified return; actual stop-distance, fees, slippage, fills, overlapping trades, and lookahead make it unusable as profit assertion. 2R+ historical hit rate filtered: 65/198=32.8%.

## Scientific cautions and next steps

The current strategy confirms green C3 / red C4 **after** hypothesizing entry during that candle: serious lookahead/fill problem. Stop-first OHLC may be conservative for some bars; targets not necessarily fillable. 5m source archive has partial days and historical gaps. This was an independent reconstructed scan rather than parity-certified execution of Python strategy. Signal count includes potentially overlapping setups. Indicators may vary slightly from source pandas implementation, especially smoothing and RVOL on incomplete sessions.

Do not turn on these filters in live code. To validate: fix executable post-confirmation entry, inspect true 5m order of entry/SL/TP, add C4 SELL research, run unseen next-period holdout, separate BUY/SELL and time/session, compare confirmed net P/L and GOOD retention, audit missing data.

## CSV design

One row per detected signal with a **single** status (GOOD/WEAK/BAD), signal datetime UK and UTC, side, entry, SL, max R, max favourable gain %, each C1/C2/C3 feature (numeric) and 12-band ASJR profile. Separate columns `proposed_filter_pass` and `proposed_filter_name` are *research tags only*, never replace signal status or original trigger logic.
