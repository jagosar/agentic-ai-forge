# A/B: 2.18.1 (agentic-flow--v2.18.1) vs 2.19.0 (design/0026-fewer-tokens)

5 session(s) per arm and fixture, seed 0. Ratios are median(B) / median(A): below 1, B is cheaper, faster or shorter. Differences are B - A. Only OK and REVIEW sessions count.

| Fixture | Cost | Minutes | Output | Mutation | Oracle | Fix cycles | Agent calls | Callers | Confirmed |
|---|---|---|---|---|---|---|---|---|---|
| tally | 1.02 | 0.96 | 0.99 | 0.01 | 0.00 | 0.00 | 0.50 | 0.00 | 0.00 |

| Metric | Geometric mean | Interval | B better / worse / tie | Sign test p |
|---|---|---|---|---|
| cost_usd | 1.02 | 0.64–1.16 | 0 / 1 / 0 | 1.000 |
| minutes | 0.96 | 0.81–1.17 | 1 / 0 / 0 | 1.000 |
| output | 0.99 | 0.87–1.17 | 1 / 0 / 0 | 1.000 |

Note: the run was stopped by a two-hour limit while session 5 of arm B was being scored, so the figures above cover 5 sessions of A and 4 of B. That session's run record is in `b/tally-5.json` (result OK, no fix cycle); its oracle and mutation scores were not taken.
