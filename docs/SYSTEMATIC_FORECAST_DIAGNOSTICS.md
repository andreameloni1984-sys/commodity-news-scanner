# GAGARIN — systematic forecast diagnostics

The adapter now calculates a separate systematic-futures diagnostic from the
existing candle state. It is inspired by systematic futures research and uses
only existing OHLC/ATR inputs:

- EWMAC trend: EMA(16) versus EMA(64), normalized by ATR.
- Breakout: close versus the preceding 20-bar high/low.
- Mean reversion: contrarian 20-bar z-score, enabled only when regime is RANGE.

The composite is displayed in Telegram as a diagnostic score from -20 to +20.
Missing components are excluded and active weights are renormalized. At least
65 valid closes and a finite positive ATR are required.

Safety boundary: this diagnostic does not alter probability, quality,
confidence, setup direction, trigger, Governor, risk sizing, entry, stop,
targets, PAPER authorization, or order execution. It is not a calibrated
probability or proof of an edge. Strategy promotion requires out-of-sample
backtests with realistic spread, slippage, fees, contract rolls, and a
sufficient historical sample.
