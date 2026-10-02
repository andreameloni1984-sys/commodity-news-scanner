# SOYUZ GAGARIN v1

Isolated research/trading engine inside the existing commodity repository.

**PAPER ONLY. No broker order execution is implemented.**

Architecture:

DATA → CONTRACT → LIQUIDITY → VOLATILITY → REGIME → SESSION → CURVE → STRUCTURE → SETUP → TRIGGER → EXECUTION → RISK GOVERNOR → SAFETY → SIGNAL FALSIFICATION → PAPER TEST

The first version deliberately contains the safety shell and validation gates before strategy modules are promoted.

## Design rules
- Never send live orders.
- A technical setup is not a trade until risk gates approve it.
- No setup is promoted without out-of-sample validation.
- Failed/insufficient signals are logged as first-class research outcomes.
- Old Commodities Bot code remains untouched.
