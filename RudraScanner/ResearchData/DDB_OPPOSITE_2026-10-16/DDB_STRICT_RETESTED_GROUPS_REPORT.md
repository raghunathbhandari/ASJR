# Rudra-DDB strict repeated range validation across broader US universe

Prices: 64 completed US daily sessions through 2026-10-15. Full original
broad universe is S&P 500 plus supplemental tickers and sector ETFs.
Both support and resistance must have >=2 independent confirmed turning-point tests (>=5 sessions apart),
within 7% price tolerance. At least TWO 25%-50% completed alternating
support-to-resistance or resistance-to-support price legs are required.
The screener uses daily-close zigzag pivots with 6.5% reversal confirmation.
This is deliberately stricter than counting annual 25%+ swing legs.

**Retested ranges passing price gate: 9 / 560**
**Provisional fundamental pass requiring manual audit: 5**
PROVISIONAL_PASS is NOT a verified fundamental pass or trading recommendation.
Missing or weak company data remains SECONDARY. Sector classification from company metadata.
If zero pass, do not weaken rules without user permission.

| Ticker | Sector | Support zone center | Resistance zone center | Bottom tests | Top tests | Completed legs | 25-50% span | Tier |
|---|---|---:|---:|---:|---:|---:|---:|---|
| AEHL | Industrials | $8.55 | $12.29 | 3 | 3 | 4 | 43.7% | SECONDARY |
| FVNNU | Financial Services | $10.67 | $13.73 | 5 | 4 | 4 | 28.7% | SECONDARY |
| CIEN | Technology | $325.01 | $447.47 | 4 | 2 | 3 | 37.7% | PRIMARY_RESEARCH_PENDING_AUDIT |
| DNA | Healthcare | $6.64 | $9.37 | 2 | 2 | 2 | 41.1% | SECONDARY |
| TER | Technology | $331.42 | $446.00 | 4 | 2 | 2 | 34.6% | PRIMARY_RESEARCH_PENDING_AUDIT |
| LRCX | Technology | $260.51 | $343.48 | 2 | 3 | 2 | 31.8% | PRIMARY_RESEARCH_PENDING_AUDIT |
| VRT | Industrials | $228.80 | $293.77 | 2 | 3 | 2 | 28.4% | PRIMARY_RESEARCH_PENDING_AUDIT |
| COHR | Technology | $275.49 | $351.22 | 5 | 3 | 2 | 27.5% | SECONDARY |
| PANW | Technology | $321.31 | $407.96 | 2 | 2 | 2 | 27.0% | PRIMARY_RESEARCH_PENDING_AUDIT |

## Opposite-phase validated-range pairs
Measured negative correlations are exploratory and not assured forward; never assume two sectors consistently alternate.
| A | B | 10d correlation | Opposite days |
|---|---|---:|---:|
| FVNNU | TER | -0.34 | 32% |
| AEHL | COHR | -0.28 | 56% |
| FVNNU | LRCX | -0.28 | 33% |
| FVNNU | PANW | -0.26 | 25% |
| AEHL | PANW | -0.24 | 51% |
| COHR | FVNNU | -0.23 | 36% |
| AEHL | CIEN | -0.21 | 46% |
| FVNNU | VRT | -0.21 | 30% |
| AEHL | TER | -0.14 | 46% |
| AEHL | LRCX | -0.11 | 43% |
| DNA | FVNNU | -0.10 | 24% |
| DNA | VRT | -0.03 | 38% |
| COHR | DNA | 0.07 | 44% |
| AEHL | FVNNU | 0.16 | 27% |
| AEHL | DNA | 0.23 | 40% |
| CIEN | FVNNU | 0.26 | 35% |
| DNA | PANW | 0.31 | 41% |
| CIEN | DNA | 0.31 | 36% |
| CIEN | VRT | 0.39 | 29% |
| PANW | VRT | 0.40 | 46% |
| DNA | TER | 0.45 | 36% |
| DNA | LRCX | 0.46 | 32% |
| TER | VRT | 0.49 | 19% |
| COHR | VRT | 0.63 | 22% |
| LRCX | VRT | 0.70 | 22% |

**Caution:** The 64-day sample may be too short to confirm two full 25-50% cycles among durable large caps.
Do not replace strict tested levels with single-year extreme or simulated AOIs.
Expanded stock universes beyond the original 46 are tracked in DAILY_CLOSES_3M.csv.
Independent fundamental audit, earnings and CHOCH remain necessary before trade.
