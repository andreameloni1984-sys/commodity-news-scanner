# WTI Overnight Regime — paper research

## Purpose
Measure WTI overnight price/volatility context, and separately test whether
overnight direction predicts the next US session. The literature note motivating
this feature reports improved next-session volatility forecasts when overnight
information is included. That does not establish a persistent overnight price
rise or a profitable LONG/SHORT rule.

## Features
- Overnight return versus the most recent earlier US-session close when complete prior-session bars exist; otherwise the first overnight bar open is used and the fallback basis is explicitly labelled in the report.
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


## Implemented collector additions
The dedicated collector `collect_wti_overnight_sessions()` explicitly requests Yahoo
Finance `CL=F` 5-minute bars and groups them by an America/New_York session date:
18:00 on the previous calendar day through 08:59 on the session date. It also
calculates a descriptive 09:00-14:29 ET open-to-close return for the same date,
so overnight features can be paired with the following US-session outcome.
UTC and ET timestamps are retained, duplicate timestamps are de-duplicated,
OHLC values are sanity-checked, and volume coverage is reported. The collector
uses the previous available US session close as the overnight return reference
only when its bar coverage is complete; otherwise it labels the open-price
fallback. It also passes the first US-session open into the gap feature.

`write_wti_overnight_archive()` can persist the resulting report to
`data/wti_overnight_sessions.json`; collection and writing are explicit calls,
not an automatic signal path. The report documents that CL=F is a continuous
contract proxy and may include roll effects.

## Cost and validation helpers
`evaluate_cost_adjusted_directional_edge()` applies a caller-supplied round-trip
cost in basis points to a hypothetical sign-following diagnostic. It is a
sensitivity analysis, not measured trading costs or a fill simulation. The
reported median uses the conventional midpoint for even-sized samples.
`chronological_walk_forward()` partitions chronologically ordered observations
into train, validation, and untouched OOS slices without shuffling. The caller
must sort by session date and evaluate each slice independently.

## Remaining manual verification
- Confirm the exact overnight window appropriate to the user's intended strategy.
- Inspect provider completeness, bar gaps, settlement price choice and contract rolls.
- Supply realistic spread, commission and slippage scenarios.
- Check EIA/OPEC release timestamps from official calendars; event flags remain caller-supplied.
- Review the saved JSON and out-of-sample statistics before any downstream use.


## Separate volatility-versus-direction evaluation
The collector now also stores the next US session's high-low range and
close-to-close realized volatility, but only when the session passes the
coverage gate. The collector assigns historical QUIET/NORMAL/EXPANDED/SHOCK
labels using only prior complete overnight ranges; the first 20 eligible
sessions remain unclassified, avoiding look-ahead in regime labels.

`research/wti_overnight_evaluation.py` reports the association between
overnight range and next-session realized volatility separately from a
hypothetical sign-following directional diagnostic. It reports Pearson and
Spearman association, descriptive regime splits, and a user-specified
round-trip cost scenario. These are descriptive statistics, not calibrated
forecasts, a profitable strategy claim, or a signal promotion.

Run from the repository root against an existing archive:
```sh
python -m research.analyze_wti_overnight --input data/wti_overnight_sessions.json --cost-bps 5
```
To explicitly fetch fresh public Yahoo CL=F data before evaluating:
```sh
python -m research.analyze_wti_overnight --fetch --cost-bps 5
```
The CLI writes `data/wti_overnight_evaluation.json`. Network access is opt-in
and collection is not scheduled. No tests were run during this change, per the
manual-verification workflow. Results must be reviewed for incomplete sessions,
roll effects, event days, and realistic costs before interpretation.


## Chronological held-out report
The CLI also includes `research/wti_overnight_validation.py`, which sorts
complete sessions by session date, removes duplicate dates, and reports fixed
60% development / 20% validation / final 20% held-out out-of-sample summaries.
The held-out segment is descriptive and must not be used to select thresholds.
No model fitting, significance testing, stop simulation, or signal promotion is
performed. The output archive's `chronological_validation` section records
sample counts, date boundaries, cost-scenario results, and limitations.
This workflow remains PAPER ONLY and should be manually reviewed before use.


## Out-of-sample cost and event diagnostics
The held-out OOS section now includes a fixed cost-sensitivity grid (0, 3, 5,
8, 10, and 15 basis points round-trip). This is a scenario comparison, not a
claim that any cost level matches actual execution. EIA/OPEC splits use only
explicit `event_flags` supplied on each observation; missing flags are shown
as unknown rather than assumed to be non-event days. No calendar scraping,
event inference, or signal promotion is performed.
