# Gagarin research log — cost-aware universe evaluation (2026-10-23)

## Change
- `engine/forecast_universe_validation.py` now accepts `round_trip_cost_bps` and passes it to each instrument's walk-forward evaluator.
- It adds `observation_weighted_mean_net_signed_return_pct` alongside the existing gross aggregate, and records the scenario cost.
- `tests/test_forecast_validation.py` now verifies that a positive cost is propagated to each instrument and lowers aggregate net return versus the zero-cost scenario.
- Instruments remain evaluated separately. The weighted aggregate is descriptive only and is explicitly not a portfolio backtest.

## Rationale
The evaluator previously supported a cost scenario per instrument, but the universe wrapper did not expose it. That mismatch could make cross-instrument comparisons appear gross-only even when the caller wanted cost sensitivity. The change closes that interface gap without changing forecasts, regime logic, or signal weights.

## Commits
- Universe propagation: `24ab0737cff0a0913f02d5145388a25f2d955777`.
- Regression test: `e3a98b35cc08d6b315fb7ac320b3fd303930084f`.

## Verification
- Re-fetch the changed files before relying on them; automated pytest execution and CI status are not confirmed by the available GitHub status endpoint.
- Production deployment is not verified.
- PAPER ONLY; no broker orders are placed.
