# Quant research note — 2026-10-22

- Keep the forecast evaluation chronological; never shuffle bars.
- Measure large intrahorizon excursions using future highs/lows, not only the horizon-end close, to identify missed moves that reverse before the close.
- Treat thresholds as instrument- and timeframe-specific; keep all evaluation PAPER-only.
- Candidate upstream method: `ruptures` (BSD-2-Clause), but its documented focus is offline change-point detection, so it should not be placed directly in the live streaming path without a separate causal adaptation.
