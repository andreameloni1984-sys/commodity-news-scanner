# Quant R&D follow-up — 2026-10-22

## Techniques reviewed

- `ruptures` is BSD-2-Clause and explicitly targets offline change-point detection. Its methods may be useful for historical regime segmentation, but its offline design is not a drop-in real-time trigger. No upstream source code was copied and no dependency was added.
- `pyforesight` is published under MIT and its 0.1.2 release is dated 2026-09-30. It selects among forecasting candidates using replayed out-of-sample errors and observed error intervals. It is a recent beta package with a Rust-backed implementation and generic-series focus; defer integration until benchmarked on Gagarin's actual bar frequencies and per-asset histories.
- Chronological validation remains mandatory: forecasts at origin t must only see bars through t; outcomes are assessed on subsequent bars. Random shuffling is inappropriate for time series.

## Implemented this cycle

- Added `engine/missed_move_validation.py`, an offline PAPER utility that counts significant future high/low excursions not anticipated by the forecast direction.
- Added `tests/test_missed_move_validation.py` for a large excursion that reverses before the horizon close, a quiet series, and insufficient history.
- Important-move threshold is configurable (default 0.5%). It must be calibrated per asset/timeframe. Overlapping forecast horizons can count the same market swing more than once.
- This utility is not connected to alert generation and cannot create or authorize orders. No live-trading behavior changed.

## Validation limits

The committed tests were run against an isolated copy of the repository modules: 12 tests passed. This is not a verified GitHub Actions result. No real per-asset missed-move rate is reported because a timestamp-aligned historical OHLC sample for Brent, Heating Oil, gold and silver was not loaded in this run.
