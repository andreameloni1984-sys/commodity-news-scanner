# Trading-course implementation ledger (Gagarin)

This ledger deliberately distinguishes implemented code from concepts that have only been discussed or still need source-by-source verification. It is not a claim that 100+ course lessons have all been completed.

## Implemented and regression-tested in this change

- PAPER-only action allowlist; no live broker execution from this portfolio.
- Required symbol and LONG/SHORT direction.
- Positive finite entry, stop and TP1/TP2/TP3 prices.
- Directional bracket geometry for LONG and SHORT.
- Minimum staged R multiples: TP1 >= 1.5R, TP2 >= 2R, TP3 >= 2.5R.
- Optional declared R multiples must agree with price geometry.
- Position size derived from stop distance and risk budget.
- Per-position notional cap.
- Duplicate open position prevention per symbol.
- Maximum three open positions.
- Aggregate open stop-risk capped at 2% of initial capital.
- Daily realized-loss circuit breaker at 2.5% of initial capital (UTC day).
- Stop-loss exit priority over targets when the sampled quote is beyond the stop.
- Staged one-third exits at TP1, TP2 and TP3.
- Reject malformed/NaN/infinite prices without reserving cash.
- No order is sent to a broker by this paper portfolio.

## Existing controls that remain in the upstream Gagarin signal governor

- PAPER_ONLY enforced by the risk governor.
- Data quality and freshness gates, including timestamp age.
- Instrument allowlist/contract, liquidity, volatility, regime, session and curve gates.
- Trigger confirmation and trend-continuation structure/MTF alignment.
- Stop side, target order, R:R geometry and declared-vs-calculated R:R checks.
- ATR stop minimum/maximum, probability, quality and confidence thresholds.

## Not certified by this ledger

- Full transcription of every Trading 212 and IBKR lesson/source into an itemized catalogue.
- IBKR Paper Trading end-to-end connection and bracket-order acceptance.
- Trading 212 demo order acceptance end-to-end.
- Slippage, commissions, financing, gaps, partial fills and intrabar SL/TP sequencing in realistic backtests.
- Empirical profitability or out-of-sample validation.
- Automatic live execution (intentionally disabled).

The next audit pass must attach each individual lesson/source concept to a rule ID, code location and test. No lesson is marked implemented solely because it was read.
