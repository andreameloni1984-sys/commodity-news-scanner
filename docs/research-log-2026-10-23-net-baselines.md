# Gagarin research log — net-return baseline comparison (2026-10-23)

## Public evidence reviewed
- scikit-learn documents chronological time-series validation and the `gap` parameter to avoid training on future observations: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- Fanelli, Fontana and Rotondi (Journal of Banking & Finance, 2026) study regime-switching statistical arbitrage in Brent/WTI/Shanghai crude futures. The findings are specific to their contracts/data and are not treated as evidence that a similar signal works in Gagarin: https://doi.org/10.1016/j.jbankfin.2026.107714
- A 2026 study of climate variables and commodity futures reports that statistical forecast accuracy and portfolio economic value can rank models differently, and that simple autoregressive benchmarks can outperform more complex specifications on statistical metrics: https://doi.org/10.1016/j.econlet.2026.113028

## Concrete changes
- `engine/forecast_validation.py`: added net-return baselines for always-LONG, always-SHORT and always-FLAT over the same forecast horizons. LONG/SHORT baselines pay the same configured hypothetical round-trip cost; FLAT has zero return/cost. Added net edge versus each baseline and retained gross/net ensemble metrics.
- Kept baseline fields in early-return schemas to reduce output-shape surprises for invalid/insufficient data.
- `engine/forecast_universe_validation.py`: added observation-weighted baseline returns to the descriptive multi-instrument summary. It remains explicitly not a portfolio backtest.
- `tests/test_forecast_validation.py`: added tests for baseline fields/edge arithmetic and aggregated baseline availability.

## Commits
- Walk-forward baseline metrics: `68fa83bb54dafdfb3f25324f501d66d48b7c646a`.
- Baseline regression tests: `e0dc8714aba0ebfd4b1c709c79e8390b894ed5a4`.
- Universe baseline aggregation: `0f447651f67bf78791095f6d2a815248eee3882c`.
- Aggregate tests: `82e4ceb831aec5f772394efb9cc1451e69ede715`.
- Stable early-return schema: `2e32433c4ed0b76f909aad1c55d9732d624072c2`.

## Limits and verification
- Baselines are diagnostics, not investment recommendations; the always-long/short baselines pay one hypothetical cost per evaluated horizon and do not model portfolio compounding, sizing, margin or overlapping position management.
- Changed files should be re-fetched for verification; automated pytest/CI status is not confirmed here. No claim that tests passed.
- No production deployment verification. PAPER ONLY; no real orders sent.