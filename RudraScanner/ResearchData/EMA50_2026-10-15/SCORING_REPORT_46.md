# Rudra 46 — Swing and Momentum Technical Research Ranking
*Research date: 16 October 2026. Data cutoff: completed US regular session 15 October 2026. Baseline: exact 46 symbols from IBKR HIGH_LAST_VS_EMA50 discovery at 20:15 UK, 15 October.*

> **Status: preliminary, rule-based technical research index — NOT a probability of winning a trade. Not a buy recommendation.** We have **NOT backtested the scoring weights** or matched historical winners and failures. The source collector does **NOT** retrieve historical market caps, sector ETF histories or dated catalysts. Those two fundamental/sector areas are a separate qualitative audit.

## Data coverage and source integrity

- **46/46** stocks have valid downloaded daily history; **45/46** have downloaded recent 5-minute bars. **43/46** have a computed 20-session *same-time-of-day* volume reading. **MAMK has zero last-day daily volume and no 5-minute bars**; exclude as a usable trade setup.
- Exact stored data: [research_metrics_46.csv](research_metrics_46.csv), [daily and five-minute historical CSV.gz folder](./), [initial collector report](RESEARCH_REPORT.md).
- The measured `rvol5bar` and `rvol20bar` compare the **last recorded five-minute candle** to its previous 5 or 20 bars respectively, **not** the historical 5-day/20-day cumulative RVOL from the original Chakra project. The measured `rvol20day_same_slot` compares the last bar to the prior 20 occurrences at the same 5-minute clock slot. Daily RVOL compares Oct 15 volume with previous 20 daily candles.
- **Candle-pattern flags are for the most recent 5-minute bar** (plus daily inside bar); this is *not* a complete historical pre-breakout pattern backtest. Same-slot comparisons are subject to Yahoo coverage, trading halts and corporate actions. Exclude missing measurements from their individual denominator, and always report coverage.

## Verified >=$2B mid-/large-cap shortlist

Top **12 among the 20 symbols with independently checked dated capitalization**. This is a *technical-only* ranking, before sector and catalyst overlay:

| Rank | Symbol | Technical /100 | Approx. cap | 20-day return | Last RVOL5bar | Same-time RVOL20 | Above EMA20 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | **SHOP** | 71 | 229.20B | 38.5% | 2.85× | 1.01× | 11.4% |
| 2 | **TEAM** | 71 | 54.96B | 12.8% | 4.19× | 1.39× | 10.4% |
| 3 | **SIG** | 68 | 4.53B | 16.5% | 3.29× | 2.41× | 13.6% |
| 4 | **CDNA** | 67 | 3.45B | 22.8% | 3.49× | 1.19× | 7.3% |
| 5 | **MPC** | 67 | 133.93B | 13.0% | 5.42× | 0.81× | 9.4% |
| 6 | **CVI** | 66 | 6.23B | 13.9% | 4.21× | 0.86× | 10.3% |
| 7 | **NTSK** | 65 | 8.36B | 18.8% | 6.01× | 1.09× | 8.3% |
| 8 | **VEEV** | 65 | 50.68B | 18.7% | 2.63× | 1.08× | 9.7% |
| 9 | **ACN** | 62 | 134.05B | 19.1% | 2.63× | 0.72× | 12.8% |
| 10 | **VIA** | 62 | 2.74B | 20.6% | 10.86× | 0.72× | 10.3% |
| 11 | **DXC** | 61 | 2.20B | 20.5% | 5.22× | 1.12× | 15.3% |
| 12 | **GME** | 61 | 14.14B | 23.1% | 3.16× | 1.19× | 12.1% |

**Research judgement, not part of numeric index:**
- **CDNA**: 52% Q2 year-over-year revenue growth, raised 2026 outlook. Technical score 67; 20-day return 22.8%; EMA20 distance 7.3%. Consider among first for dated breakout/base analysis. [CareDx release](https://www.caredx.com/newsroom/press-releases/caredx-announces-second-quarter-2026-financial-results).
- **VEEV**: reported flat-base breakout and earnings/guidance improvement; Oct 13 IQVIA partnership expanded. Technical score 65. Study *prior* base candles, not merely the move after the breakout. [Investor news](https://www.investors.com/research/veeva-stock-veev-ai-software-medical-markets-investing-tech/) and [IQVIA announcement](https://ir.iqvia.com/press-releases/press-release-details/2026/IQVIA-Selects-Veeva-Clinical-Operations-Applications/default.aspx).
- **TEAM, SHOP**: top technical momentum candidates. Technology-sector softness and recent AI-risk rotation require caution; this is not all-weather confirmation. [Reuters](https://www.reuters.com/business/nasdaq-futures-dive-1-ai-rout-deepens-debt-concerns-2026-10-15/).
- **SIG**: strongest observed same-time 20-session RVOL among leading verified mid-/large-caps. Examine volume ahead of the Oct 15 advance, not assume latest candle predicts continuation.
- **MPC and CVI**: strong raw trend readings but the wider *energy sector lagged* on Oct 15; confirm multi-session sector-relative strength before treating as leaders. [Sector recap](https://www.tipranks.com/news/sp-500-top-stock-gainers-today-10-15-26).
- **FIGS, IOVA, MRNA, BSP, KOD**: large recent advances or catalyst gaps require separate *extended / event-driven* labels; their patterns are not automatically fresh entries. FIGS is $3.25B (mid-cap) as of Oct 15, but 26.3% above EMA20 after a 49.6% 20-day gain.
- **PD** is **excluded** from the $2B+ shortlist: Oct 15 capitalization approx. $1.34B despite leading the raw technical board. Other unverified caps are *not* silently classified eligible.

## Complete all-46 raw technical ranking

The order below includes excluded, special-event and unverified-cap stocks for audit. **Only the separate verified-cap shortlist above is aligned with our mid/large-cap restriction.**

| # | Symbol | Technical /100 | Coverage | 5D | 20D | 63D | RVOL5bar | RVOL20bar | Same-slot20 | EMA20 distance | Cap scope |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | **PD** | 71 | 100% | 9.2% | 19.5% | 67.5% | 3.79× | 9.80× | 1.78× | 11.1% | No |
| 2 | **SHOP** | 71 | 100% | 8.3% | 38.5% | 44.2% | 2.85× | 5.26× | 1.01× | 11.4% | Yes |
| 3 | **TEAM** | 71 | 100% | 6.7% | 12.8% | 132.7% | 4.19× | 6.55× | 1.39× | 10.4% | Yes |
| 4 | **EFOR** | 69 | 100% | 10.0% | 20.0% | 111.0% | 8.68× | 12.96× | 1.29× | 11.0% | Check |
| 5 | **SIG** | 68 | 100% | 11.6% | 16.5% | 29.4% | 3.29× | 7.26× | 2.41× | 13.6% | Yes |
| 6 | **CDNA** | 67 | 100% | 7.2% | 22.8% | 67.8% | 3.49× | 8.20× | 1.19× | 7.3% | Yes |
| 7 | **MPC** | 67 | 100% | 2.9% | 13.0% | 53.0% | 5.42× | 6.67× | 0.81× | 9.4% | Yes |
| 8 | **CVI** | 66 | 100% | 3.6% | 13.9% | 76.1% | 4.21× | 9.22× | 0.86× | 10.3% | Yes |
| 9 | **NTSK** | 65 | 100% | 4.3% | 18.8% | 50.5% | 6.01× | 8.12× | 1.09× | 8.3% | Yes |
| 10 | **VEEV** | 65 | 100% | 9.9% | 18.7% | 60.2% | 2.63× | 4.04× | 1.08× | 9.7% | Yes |
| 11 | **VNCE** | 64 | 100% | 15.5% | 35.7% | 107.0% | 3.34× | 6.25× | 1.30× | 21.9% | Check |
| 12 | **ACN** | 62 | 100% | 8.8% | 19.1% | 57.9% | 2.63× | 4.52× | 0.72× | 12.8% | Yes |
| 13 | **RCEL** | 62 | 100% | 0.6% | 19.5% | 162.9% | 4.42× | 7.05× | 1.12× | 8.2% | Check |
| 14 | **VIA** | 62 | 100% | 8.6% | 20.6% | 87.0% | 10.86× | 15.07× | 0.72× | 10.3% | Yes |
| 15 | **DXC** | 61 | 100% | 11.5% | 20.5% | 45.6% | 5.22× | 8.52× | 1.12× | 15.3% | Yes |
| 16 | **GME** | 61 | 100% | 10.8% | 23.1% | 28.0% | 3.16× | 5.43× | 1.19× | 12.1% | Yes |
| 17 | **KSS** | 61 | 100% | 11.4% | 34.2% | 30.4% | 4.24× | 7.72× | 1.06× | 14.0% | Yes |
| 18 | **IBTA** | 60 | 100% | 13.1% | 16.9% | 55.1% | 4.80× | 5.63× | 0.85× | 15.7% | Check |
| 19 | **PRGO** | 59 | 100% | 13.7% | 22.3% | 56.9% | 5.08× | 7.46× | 1.39× | 11.0% | Yes |
| 20 | **IOVA** | 58 | 100% | 10.6% | 46.9% | 194.4% | 4.37× | 8.21× | 0.83× | 13.9% | Yes |
| 21 | **SG** | 58 | 100% | 10.8% | 55.0% | 49.7% | 5.17× | 5.48× | 0.59× | 17.6% | Check |
| 22 | **TBCH** | 58 | 100% | 27.0% | 28.6% | 24.3% | 2.62× | 3.64× | 2.44× | 19.3% | Check |
| 23 | **CBRL** | 56 | 100% | 21.8% | 54.0% | 25.7% | 3.45× | 6.65× | 1.23× | 19.4% | Check |
| 24 | **DNA** | 55 | 100% | 3.7% | 50.0% | 48.7% | 5.40× | 10.29× | 1.25× | 5.9% | Check |
| 25 | **SUJA** | 55 | 100% | 11.0% | 36.4% | 25.4% | 8.25× | 12.64× | 1.48× | 14.8% | Check |
| 26 | **CAI** | 54 | 100% | 15.5% | 2.7% | 92.6% | 3.75× | 7.68× | 0.77× | 8.6% | Yes |
| 27 | **MRNA** | 53 | 100% | 20.1% | 49.6% | 282.6% | 7.22× | 9.34× | 1.54× | 19.9% | Check |
| 28 | **ODD** | 53 | 100% | 18.5% | 20.2% | 41.9% | 4.52× | 5.30× | 0.65× | 17.7% | Check |
| 29 | **OPCH** | 52 | 100% | 0.6% | 27.4% | 43.6% | 3.32× | 4.82× | 0.36× | 13.1% | Yes |
| 30 | **PTC** | 51 | 100% | -0.3% | 43.7% | 55.3% | 4.22× | 7.04× | 0.80× | 12.4% | Special |
| 31 | **PMI** | 49 | 100% | 3.3% | 78.6% | 42.9% | 1.85× | 1.50× | 10.86× | 18.8% | Check |
| 32 | **RGC** | 49 | 100% | 24.8% | 59.7% | 89.6% | 3.56× | 2.00× | 6.31× | 32.8% | Check |
| 33 | **RXO** | 49 | 100% | 0.5% | 44.2% | -0.8% | 8.72× | 11.75× | 1.03× | 14.1% | Check |
| 34 | **BSP** | 48 | 100% | 46.7% | 44.7% | 72.1% | 8.30× | 9.10× | 1.35× | 40.2% | Special |
| 35 | **NVAX** | 48 | 100% | 16.4% | 28.2% | 56.1% | 2.70× | 5.75× | 0.81× | 11.8% | Check |
| 36 | **FIGS** | 46 | 100% | 30.4% | 49.6% | 89.5% | 3.78× | 7.52× | 1.10× | 26.3% | Yes |
| 37 | **XP** | 45 | 100% | -0.6% | 48.8% | 80.2% | 3.77× | 7.76× | 1.10× | 13.9% | Yes |
| 38 | **GRAL** | 44 | 100% | 2.1% | 69.4% | 86.5% | 6.23× | 12.82× | 0.75× | 6.6% | Yes |
| 39 | **PICS** | 40 | 100% | 10.8% | 39.4% | 15.3% | 1.25× | 1.47× | 0.82× | 15.6% | Check |
| 40 | **PCRX** | 38 | 100% | -0.2% | 48.4% | 41.9% | 2.83× | 5.16× | 0.99× | 20.4% | Check |
| 41 | **KOD** | 36 | 100% | -6.5% | 168.3% | 106.7% | 2.95× | 5.39× | 0.57× | 13.0% | Check |
| 42 | **MAMK** | 35 | 44% | 0.0% | 0.0% | 0.0% | —× | —× | —× | 0.0% | No |
| 43 | **AEHL** | 34 | 100% | 0.6% | -7.1% | -14.0% | 3.22× | 4.18× | 1.84× | 16.5% | Check |
| 44 | **GIBO** | 33 | 94% | 9.0% | 93.3% | 121.2% | 0.33× | 0.30× | —× | 34.6% | Check |
| 45 | **SVRN** | 29 | 100% | 6.8% | 194.4% | 422.3% | 0.79× | 0.85× | 0.23× | 9.7% | Check |
| 46 | **FVNNU** | 22 | 91% | -15.0% | 97.1% | 170.6% | 1.79× | 0.89× | —× | 43.4% | Check |

## Scoring specification and interpretation

The user-approved **seven-area proposal** is RVOL25 + momentum20 + moving averages15 + candles15 + consolidation10 + sector/market5 + catalysts10 = 100.

This **version scores only the five OHLCV-supported areas, out of 85 possible points**, applies a transparent extension-risk penalty, then reports a normalized **technical index**: `round(100 × max(0, earned_technical_points − penalty) / available_technical_points)`. Missing measurements reduce the denominator and are explicitly shown by Coverage; missing values are not automatically treated as zero. **Sector (5) and catalysts (10) remain unscored** until systematic, dated evidence exists for all eligible stocks. The normalized technical index is **not** the proposed complete seven-factor 100-point score and **not** a calibrated probability.

Detailed technical inputs:
- **RVOL, 25 points:** last-bar RVOL5 (5), last-bar RVOL20 (5), 20-day same-time-slot RVOL (5), 5-day same-time-slot RVOL (3), daily RVOL20 (5), five-day-vs-twenty-day volume contraction (2). RVOL5/20 scales: 5pts for >=2.0x, 4 for >=1.5x, 3 for >=1.0x, 2 for >=0.75x, 1 for >=0.5x. Same-slot20: 5pts >=2x, 4 >=1.5x, 3 >=1.1x, 2 >=0.8x. Same-slot5: 3 >=2x, 2 >=1.4x, 1 >=0.9x. Daily RVOL20: 5 >=1.8x, 4 >=1.3x, 3 >=0.9x, 1 >=0.65x. Five-day volume mean / twenty-day mean: 2pt below 0.8, 1pt below 1.0.
- **Momentum, 20:** forward-looking values are NOT used; last completed close vs 5, 10, 20, 63 sessions previously, 5pts each using bounded bands to limit rewards for overextension. This measures momentum, not future returns.
- **EMA/MA, 15:** daily EMA9 > EMA20 > SMA50 (5), price above EMA20 (2), 5-day positive EMA9 & EMA20 slopes (3), latest 5-minute close above 5m EMA9 & EMA20 (2), 5m EMA9 > 5m EMA20 (1), positive five-bar EMA slopes (2).
- **Candles, 15:** last-bar 12-low sweep/reclaim (4), bullish engulfing (3), high-20 breakout (3), inside bar including daily (2), tight bar (1), lower wick >=40% of candle range (2). These are *last-bar observations* and are not yet studied for predictive lead time.
- **Consolidation, 10:** daily 10-day high/low range bands (5; <=10% gives 5, <=18% gives 4, <=25% gives 2, <=35% gives 1), five-day volume contraction (3), 10-bar 5m trading range (2).
- **Overextension penalty:** 20-day rise >40% -2; >60% -5; >100% -8. Distance above daily EMA20 >10% -1; >15% -3; >25% -5. Ten-day range >30% -2; >50% -4. These are **research heuristics**, not optimized or validated.

## Company capitalization verification and exclusions

Market-cap figures are approximate **Oct 15, 2026** snapshots from public market profiles. CAP_UNVERIFIED means *not fully checked in this run*; it does not mean small-cap. See cited profile URLs in the companion score CSV metadata and individually:
- [TEAM](https://stockanalysis.com/stocks/team/market-cap/): ~$54.96B
- [SHOP](https://stockanalysis.com/stocks/shop/market-cap/): ~$229.2B
- [SIG](https://stockanalysis.com/stocks/sig/market-cap/): ~$4.53B
- [CDNA](https://stockanalysis.com/stocks/cdna/market-cap/): ~$3.45B
- [MPC](https://stockanalysis.com/stocks/mpc/market-cap/): ~$133.93B
- [CVI](https://www.financecharts.com/stocks/CVI/summary/market-cap): ~$6.23B
- [NTSK](https://stockanalysis.com/stocks/ntsk/market-cap/): ~$8.36B
- [VEEV](https://stockanalysis.com/stocks/veev/market-cap/): ~$50.68B
- [ACN](https://stockanalysis.com/stocks/acn/market-cap/): ~$134.05B
- [GME](https://stockanalysis.com/stocks/gme/market-cap/): ~$14.14B
- [KSS](https://stockanalysis.com/stocks/kss/): ~$2.54B
- [DXC](https://stockanalysis.com/stocks/dxc/market-cap/): ~$2.2B
- [PRGO](https://stockanalysis.com/stocks/prgo/market-cap/): ~$2.21B
- [IOVA](https://stockanalysis.com/stocks/iova/market-cap/): ~$6.67B
- [CAI](https://stockanalysis.com/stocks/cai/market-cap/): ~$8.98B
- [OPCH](https://stockanalysis.com/stocks/opch/statistics/): ~$4.68B
- [GRAL](https://stockanalysis.com/stocks/gral/market-cap/): ~$6.05B
- [FIGS](https://stockanalysis.com/stocks/figs/): ~$3.25B
- [XP](https://stockanalysis.com/stocks/xp/market-cap/): ~$15.24B
- [VIA](https://stockanalysis.com/stocks/via/): ~$2.74B
- [PD](https://stockanalysis.com/stocks/pd/market-cap/): ~$1.34B

## Next research steps for credible probability estimates

1. Reconstruct each qualifying stock's **historical** breakout, tight base, sweep and before-move RVOL sequence (not only last-bar flags) using the 93 saved evidence files.
2. Include a historical non-winner/control universe, with *point-in-time* company caps and scanner membership; today's EMA50 scan alone has survivorship/selection bias.
3. Compute precision, lift versus unconditional 20–50% move base rate, drawdown, lead-time and chronological out-of-sample results. Separate biotech event gaps, takeovers and extended momentum from fresh bases.
4. Add as-of-dated sector index/ETF and catalyst evidence with verified links; then test seven-factor full scores and avoid overfitted threshold claims.

**Evidence file and scores prepared for research, not trading execution. Chakra and the live Discord bot remain untouched.**
