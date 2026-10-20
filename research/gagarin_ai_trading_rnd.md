# SOYUZ GAGARIN — AI TRADING R&D LOG

## 2026-10-07 — AI trading experiments + execution economics

### Research rule
External videos, papers and trading experiments are treated as hypotheses, not as validated strategy rules. A method enters Gagarin only after: (1) required inputs are actually available; (2) the formula is deterministic and testable; (3) look-ahead/data leakage is excluded; (4) results are measured net of explicit execution costs when those costs are known; (5) the change does not merge the morning forecast with the intraday trigger.

### Current external study
- YouTube experiment supplied by the user: https://youtu.be/7A9O15nq5Yw
- CME material confirms that futures/spot basis is an observable price difference and that contango/backwardation describe the relationship between forward/futures prices and spot/curve structure.
- CME also warns that continuous futures series can create artificial returns at contract rolls if contracts are spliced without appropriate adjustment.

### Implemented in this cycle
soyuz_gagarin/execution_economics.py
- bid/ask spread and spread in basis points;
- executable entry price from an actual bid/ask quote;
- price-based R/R;
- break-even win rate;
- net expectancy after an explicitly supplied cost in R;
- cost in R from an explicitly supplied price cost and stop distance;
- position sizing from explicit equity, risk fraction, stop distance and contract multiplier;
- futures/spot basis and basis percentage;
- near/deferred curve classification: CONTANGO / BACKWARDATION / FLAT.

All functions fail closed (None) when required evidence is missing or internally inconsistent.

### Integration rule
MarketSnapshot now carries optional bid and ask evidence. The adapter copies these fields only when present in the source state. Gagarin exposes the resulting execution metrics as diagnostics only.

This cycle deliberately does NOT:
- create an ENTRY from bid/ask;
- replace the existing intraday trigger;
- treat the morning forecast as an intraday trigger;
- estimate missing spread, slippage, commission or liquidity;
- enable live trading.

### Tests
Added tests/test_execution_economics.py covering valid/invalid bid-ask data, LONG/SHORT executable prices, R/R and break-even, net expectancy with explicit costs, fail-closed behavior, position sizing, basis and curve state.

The repository workflow currently defines the test suite but is not configured for manual dispatch from this branch. Therefore no GitHub CI pass is claimed until an actual workflow run is observed.
