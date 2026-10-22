# Gagarin PAPER: commodity forecast audit

## Scope
`engine/commodity_research.py` is an offline, read-only research utility. It
does not fetch prices, write trading state, connect to a broker, or place orders.
Use historical OHLC CSV files supplied by the operator.

## Data contract
CSV header must contain `timestamp,open,high,low,close`; `volume` is optional.
Timestamps are Unix epoch seconds or ISO-8601 with a timezone. Duplicate or
non-monotonic timestamps, invalid OHLC and negative volume are rejected.
Never splice different contracts or providers without documenting roll handling.

## Research workflow
For each instrument and timeframe, keep separate files and record source,
symbol/contract, timezone, timeframe, adjustment/roll method, and retrieval date.
Run `load_ohlc_csv(path)`, then `audit_missed_moves(candles, horizon=4,
threshold_pct=...)`. Thresholds must be calibrated per asset/timeframe using
training data only. Compare parameters on a later untouched holdout period.
The audit reports high/low excursions, missed direction, false directional
signals and directional hit rate. Horizons overlap, so windows are not
independent observations; do not treat raw percentages as confidence estimates.

## Instrument identity / source hints
Common Yahoo Finance continuous-futures symbols are `BZ=F` (Brent), `HO=F`
(Heating Oil), `GC=F` (Gold), and `SI=F` (Silver). Confirm availability,
contract roll methodology, data rights, timestamps, and whether the series is
continuous futures before use. A missing symbol is a data failure, not a zero
move. This utility deliberately does not download data automatically.

## Limitations
A heuristic direction is not a calibrated probability. OHLC bars cannot reveal
the order in which a high and low occurred inside the same candle. Excursion
thresholds and horizons are research choices, and overlapping windows inflate
event counts. No claim of predictive improvement is made without instrument-
specific walk-forward and holdout results. PAPER ONLY.
