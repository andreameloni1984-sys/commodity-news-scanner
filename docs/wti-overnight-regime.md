# WTI Overnight Regime — paper research

## Purpose
Measure WTI overnight price/volatility context, and separately test whether
overnight direction predicts the next US session. The literature note motivating
this feature reports improved next-session volatility forecasts when overnight
information is included. That does not establish a persistent overnight price
rise or a profitable LONG/SHORT rule.

## Features
- Overnight return versus prior close (or first bar open if absent).
- Overnight high-low range as a percentage of reference price.
- Realized volatility from intranight close-to-close log returns.
- Gap from last overnight close to supplied US-session open.
- Aggregate volume only when bar volumes are present.
- QUIET/NORMAL/EXPANDED/SHOCK classification using prior range percentiles:
  below 25th percentile QUIET, 25th–75th NORMAL, 75th–90th EXPANDED,
  90th percentile and above SHOCK. Requires at least 20 prior observations.
- EIA/OPEC event flags are passed through as caution context; event schedules
  are not guessed and event causality is not implied.
- Forward directional evaluation compares overnight-return sign with the next
  session return. It reports sample size/hit rate but never promotes a signal.

## Data contract and limitations
Caller must supply timestamped overnight OHLCV bars, prior close, US open,
historical ranges available before the current session, and event flags. The
caller remains responsible for contract rolls, timezone/session boundaries,
stale/missing bars, and trading costs. No external data fetch is added here.
Missing inputs remain null/unknown rather than inferred.

## Safety
PAPER ONLY. Not connected to final_decision, alert promotion, broker, or order
execution. Require chronological walk-forward and untouched out-of-sample
validation, costs/spread/slippage, event splits, and enough observations before
any later integration into signal scoring.
