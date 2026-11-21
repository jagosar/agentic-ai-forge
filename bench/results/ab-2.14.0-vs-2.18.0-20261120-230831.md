# A/B: 2.14.0 (agentic-flow--v2.14.0) vs 2.18.0 (agentic-flow--v2.18.0)

3 session(s) per arm and fixture, seed 0. Ratios are median(B) / median(A): below 1, B is cheaper, faster or shorter. Differences are B - A. Only OK and REVIEW sessions count.

| Fixture | Cost | Minutes | Output | Mutation | Oracle | Fix cycles | Agent calls | Callers | Confirmed |
|---|---|---|---|---|---|---|---|---|---|
| tally | 1.19 | 1.15 | 1.02 | 0.03 | 0.00 | 1.00 | 4.00 | ? | 0.00 |
| tempconv | 0.73 | 0.86 | 0.79 | 0.01 | 0.00 | 0.00 | 0.00 | ? | 0.00 |

| Metric | Geometric mean | Interval | B better / worse / tie | Sign test p |
|---|---|---|---|---|
| cost_usd | 0.93 | 0.70–1.21 | 1 / 1 / 0 | 1.000 |
| minutes | 0.99 | 0.81–1.16 | 1 / 1 / 0 | 1.000 |
| output | 0.90 | 0.80–1.05 | 1 / 1 / 0 | 1.000 |
