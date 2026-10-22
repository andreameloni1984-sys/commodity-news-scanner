# Data prerequisite for missed-move measurement — 2026-10-22

The offline missed-move evaluator accepts normalized OHLC candles for any symbol, but per-asset rates require an actual aligned historical sample.

Repository inspection found explicit provider routing for Brent (UKOIL / BZ=F), gold (XAUUSD / GC=F) and silver (XAGUSD / SI=F) in `engine/data.py`. No Heating Oil symbol/provider mapping was found in the searched repository paths (including `HO=F`). The evaluator therefore must not report a Heating Oil missed-move rate until a validated Heating Oil OHLC feed is explicitly configured and tested.

Do not substitute gasoline, WTI or Brent for Heating Oil. Instrument mismatch would invalidate thresholds and the reported missed-move rate.
