# Gagarin quantitative research log — 2026-10-23 (cost-aware walk-forward)

## Evidence checked
- scikit-learn TimeSeriesSplit documentation explains that time-ordered splits avoid training on future observations and supports a configurable gap: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- A 2026 regime-aware walk-forward study reports the use of chronological folds, purge windows, cost sensitivity, calibration and ablation analysis. Its results concern its own equity universe and are not assumed to transfer to commodities: https://www.mdpi.com/2079-9292/15/6/1334
- A 2026 horizon-specific forecasting study reports that return-space performance can remain weak even where price-level fit looks strong, supporting simple baselines and careful OOS comparison: https://doi.org/10.3390/forecast8020034

## Implemented
- `engine/forecast_validation.py`: optional `round_trip_cost_bps` parameter (default 0 to preserve existing behavior); subtracts the hypothetical round-trip cost from LONG/SHORT signed returns, reports `mean_net_signed_return_pct` overall and by regime, and rejects negative/non-finite cost or move threshold.
- `tests/test_forecast_validation.py`: tests zero-cost equivalence, positive-cost degradation, regime-level net metrics and invalid parameter rejection.
- This is an offline diagnostic only. Cost is a scenario parameter, not a broker quote or a full execution model. It does not model position sizing, spread variability, financing, market impact, gaps, or intrabar path.

## Commits
- Cost-aware evaluator: `8c67c23ed51d9500acbded23b7c1fc6bfc3d48b0`.
- Regression tests: `03e667d694bd495aa8d088138e2eab822eebc7a1`.
- Output-schema/note compatibility fix: `bb7c9156c0e09038adb2349250207b7f960a7e1b`.

## Verification status
- Re-fetch of the engine and test files confirmed the changes are present on the default branch.
- The commit status endpoint returned no checks for the previous validation commit; workflow run listing is limited to PR-associated runs. Automated execution of pytest is therefore unverified, and no test-pass claim is made.
- Production deployment is not verified. PAPER ONLY remains in force; no real orders were sent.