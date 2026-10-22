# Gagarin PAPER: commodity forecast audit

## Scope
`engine/commodity_research.py` is an offline, read-only research utility. It
does not fetch prices, write trading state, connect to a broker, or place orders.
Use historical OHLC CSV files supplied by the operator.

## Data contract
CSV header must contain `timestamp,open,high,low,close`; `volume` is optional.
Timestamps are Unix epoch seconds or ISO-8601 with a timezone. Duplicate or
non-monotonic timestamps, non-finite values, invalid OHLC and negative volume
are rejected. Never splice different contracts/providers without documenting
roll handling and corporate/action adjustments.

## Research workflow
For each instrument and timeframe, keep separate files and record source,
symbol/contract, timezone, timeframe, adjustment/roll method, and retrieval date.
Run `load_ohlc_csv(path)`, then `audit_missed_moves(candles, horizon=4,
threshold_pct=...)`. Thresholds must be calibrated per asset/timeframe using
training data only. Compare parameters on a later untouched holdout period.
The audit reports high/low excursions, missed directions, false directional
signals and directional hit rate. Horizons overlap, so windows are not
independent observations; raw percentages are not confidence estimates.

## Ambiguous OHLC windows
When both up and down excursion thresholds are crossed within the same forecast
window, OHLC alone cannot establish which happened first. Such windows are
counted as ambiguous and excluded from the directional hit/false-signal rate
denominator. Event-window missed-rate counts each directional excursion and
is still descriptive, not a probability or profitability estimate.

## Instrument identity / source hints
Common Yahoo Finance continuous-futures symbols are often written as `BZ=F`
(Brent), `HO=F` (Heating Oil), `GC=F` (Gold), and `SI=F` (Silver).
These are symbol hints, not verified data availability or recommendations.
Confirm the actual instrument, contract roll methodology, rights, timestamps,
and whether the series is continuous futures before use. Missing data is a data
failure, not a zero move. This utility deliberately does not download data.

## Limitations
A heuristic direction is not a calibrated probability. Thresholds and horizons
are research choices. No claim of predictive improvement is made without
instrument-specific walk-forward and holdout results. PAPER ONLY.
