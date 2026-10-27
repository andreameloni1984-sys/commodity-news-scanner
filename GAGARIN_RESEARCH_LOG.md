# GAGARIN — Research and implementation log

## 2026-10-26 — Validate Telegram entry, stop and target levels

- Finding: the news-to-setup path required non-null price/entry/SL/TP values but did not reject NaN/Infinity or levels ordered on the wrong side of entry. Such values could be formatted into a Telegram alert even though they were not actionable risk levels.
- Implemented on branch fix/gagarin-validate-telegram-risk-levels-20261026: finite-positive numeric validation and direction-aware level ordering before a setup can be sent. LONG requires SL < entry < TP1 (and TP2 > TP1); SHORT requires TP1 < entry < SL (and TP2 < TP1). If TP2 is present but invalid, the alert is suppressed.
- Regression coverage: valid LONG/SHORT examples plus NaN, infinity, inverted stop/target, and incorrectly ordered TP2 cases; integration-level tests ensure these setups are rejected.
- Limits: this is a consistency gate, not a profitability claim or a replacement for price freshness, spread, slippage, or governor checks. PAPER/DEMO only; no order execution or Telegram test message.
- Verification: CI triggered by branch/PR; test result pending. Production Render deploy is currently blocked by the workspace build-pipeline-minute limit, confirmed in service build logs on 2026-10-26.
- Next: wait for CI, then merge only if checks pass; verify deployment when Render build capacity is available without upgrading or increasing spend.


## 2026-10-26 — Guard Gagarin polling against malformed Retry-After headers

- Finding: an upstream response with `Retry-After: NaN` or `Infinity` could pass float parsing, then raise during integer conversion in the source backoff path. That could interrupt a news poll instead of applying a cooldown.
- Implemented on branch `fix/gagarin-safe-retry-after-20261026`: accept only finite, non-negative numeric retry delays and cap the parsed value at `SOURCE_BACKOFF_MAX_SECONDS`; malformed values fall back to normal exponential backoff.
- Regression tests: NaN, positive/negative infinity, negative and non-numeric values; oversized finite values are capped.
- Verification: changes committed to the feature branch. CI must run on the PR before this is considered verified. No production deploy or Telegram test message was sent. Render build quota remains a separate deployment blocker.
- Next: inspect the new CI results and merge only after all relevant checks pass.


## 2026-10-26 — Select Atom article permalinks before source deduplication

- **Finding:** the RSS/Atom reader overwrote its link field in document order. An Atom entry with `rel="alternate"` followed by `rel="self"` could end up with the API endpoint as its source URL, impairing deduplication and making Telegram citations less useful.
- **Implemented:** the reader now prefers explicit alternate links, accepts RSS/default links, and ignores self/enclosure links. Entries with no usable article link are dropped instead of being emitted with a non-article endpoint.
- **Regression tests:** alternate-after-self ordering and self-only Atom entries.
- **Limits:** offline parser tests do not prove current feed availability or live Telegram delivery. Render build-pipeline minutes remain exhausted; no deployment, Telegram test message, or trade order was triggered.


## 2026-10-26 — Preserve valid GDELT articles when a response contains malformed rows

- **Finding:** the GDELT parser called `.get()` on every row without checking its type. One null/string row could raise and discard all valid articles in the same response, then trigger source backoff.
- **Implemented:** validate the response envelope and articles list; skip non-object rows while retaining valid rows. An invalid envelope raises a clear ValueError, so the existing source failure/backoff path handles it without aborting the wider poll.
- **Regression tests:** mixed valid/malformed rows retain the valid article; a non-list articles field is rejected explicitly.
- **Limits:** this improves parser resilience but does not fix upstream GDELT timeouts or guarantee source availability. Render deployment remains blocked by exhausted build minutes; no Telegram test message was sent.
- **Safety:** PAPER/DEMO only; no orders or broker operations.


## 2026-10-26 — Reject non-finite values in the post-alert scorecard

- **Finding:** Python accepts `NaN` and `Infinity` as floats. Without finite-value checks, a corrupted alert or reaction price could contaminate directional accuracy; invalid SL/TP geometry could be counted as an outcome.
- **Implemented in PR #67:** filter non-finite/non-positive alert and reaction prices; count TP1/SL only when finite positive levels are ordered correctly around the alert price for LONG/SHORT.
- **Files:** `telegram/news_monitor.py`, `tests/test_news_monitor.py`.
- **Code commit:** `fc5b67c77bb6a9076e2d7be15bf57d5cec40db8b`; regression-test commit `16aa670f4e8571b57995c41f45c8af543f7b4386`.
- **CI:** NEWS alert, public-event-brain, PAPER, general tests, and execution-layer workflows passed on the branch. The `Workers Builds: telegram-github-bridge` check was still in progress at the last check, so merge is held until it resolves.
- **Deployment / limits:** no Render deployment triggered; build-pipeline minutes are exhausted. This affects the scorecard's integrity, not the trading decision path. No durable-journal claim is made while `DATABASE_URL` is absent.
- **Safety:** scorecard hygiene only; PAPER/DEMO, no broker or order execution.

## 2026-10-27 — Fail closed when duplicate timestamps disagree on OHLCV

- **Finding:** `engine/data.py::_validate_candles` silently kept the first candle for a timestamp and discarded all later rows, even when a duplicate carried different valid OHLCV values. The chosen price then depended on provider row order, which can alter RSI, ATR and downstream structure without a visible data-quality error.
- **Change:** keep an OHLCV signature per timestamp. Exact duplicate rows are deduplicated as before; a second valid candle at the same timestamp with conflicting OHLCV returns an empty result and `CONFLICTING_DUPLICATE_TIMESTAMP`, allowing the normal fail-closed provider/data-error path to handle it.
- **Regression tests:** `tests/test_data_finite_values.py::test_validate_candles_deduplicates_identical_timestamp_rows` preserves exact deduplication; `test_validate_candles_fails_closed_on_conflicting_duplicate_timestamp` asserts that conflicting bars do not enter the indicator pipeline.
- **Operational path:** provider candles → `_normalize` → `_validate_candles` → freshness/ATR/regime → structure/setup/risk. The validation is data-integrity protection, not a directional signal.
- **CI:** code commit `e0600cc2a63cf0d625e27d447fba241a59ba2ac3`; test commit `f39ad794dfbe26f7d0908935d637e4e6e1d36ec3`. New PR workflows are pending; do not count this change as CI-verified until they complete.
- **Deployment:** branch only; no merge/deploy. Render build-pipeline minutes remain exhausted.
- **Empirical limit:** synthetic regression only; no market replay or profitability claim.
- **Safety:** PAPER/DEMO only; no broker, orders, or Telegram test messages.

## Historical record recovered — 2026-09-25 agricultural feed freshness

- A prior conversation record says the GitHub Actions run of `python main.py` marked four Yahoo-backed agricultural feeds STALE: Caffè, Cacao, Riso and Zucchero.
- The recorded artifacts were repository-root `diagnostic_agri.py` (v1.0, with v2.0/v3.0 variants in the same chat) and `engine/data.py` v5.0; the record references prior commit prefix `de28b59` and says a later v5.1 broke data loading. The exact diagnostic output with resolved symbols/titles was not recovered.
- Current mapping: `engine/data.py` provider routing and candle validation → freshness classification; `diagnostic_agri.py` checks Twelve Data catalog/symbols/freshness separately. No current stale-feed result is inferred from the old incident, and no agricultural feed replay was run in this change.
- Follow-up required: reproduce provider response timestamps without secrets, verify stale candles remain excluded from decision logic, and compare current provider coverage against the historical incident.

## Historical Gagarin records recovered from late September / early October 2026

- **2026-09-21:** a recorded `commodity_bot.py` v6.1.9 run reported Shadow failing for all 21 commodities with `extract_structure_ok() missing ... direction`. The exact full traceback is not present in the recovered context.
- **2026-09-22:** the recorded `commodity_bot.py` v6.2.0-SOYUZ-GAGARIN-CANONICAL run showed Rame with RR1=1.50, RR2=2.00, RR3=2.50, `SETUP NONE`, `TRIGGER False`, `REGIME UNKNOWN`; the Telegram delivery was recorded as confirmed (message ID 1375). This is a historical simulated run, not a current signal.
- **2026-09-25 20:04:33.764771 UTC:** a recovered `main.py` paper-only run logged a WTI LONG candidate with scores 80/71/70, entry 91.357, SL 91.1224, TP1 91.709, TP2 91.8263, TP3 91.9436 and RR3=2.50. The retrieved record did not contain a completed outcome, so this cannot be counted as a win/loss or evidence of profitability.
- **2026-10-06 — merged PR #11:** [Apply lessons from 15 days of Gagarin testing](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/11), merge commit `3c783ea698ee40f61b5ee873cc97031d48ee04df`, changed the legacy `engine/safety.py` path to enforce RR1 >= 1.5, RR2 >= 2.0 and RR3 >= configured minimum, and added stale-analysis-timestamp gating in `soyuz_gagarin/adapter.py`; regression coverage was added to `tests/test_gagarin_core.py`. Current `main` still has staged RR checks in `engine/safety.py`, but the adapter/legacy path must not be assumed to be the sole canonical runtime.
- **2026-10-07 — merged PR #15:** [Gagarin daily evidence-backed forecast](https://github.com/andreameloni1984-sys/commodity-news-scanner/pull/15), merge commit `c86a3ac3de05f60ae8be09a34832b0423ade0b24`, introduced an outcome-first daily forecast that uses context-matched analogues only when supplied and otherwise recorded validation samples; heuristic scores are not calibrated probabilities.
- **100-point catalog:** no separate Gagarin 100-point/100-rule catalog, exact lesson-title list, or retrievable PR #11 research appendix was found in the available historical context. Do not reconstruct one from these PRs.
- **Mapping to this PR:** the historical lesson that provider data quality must be explicit maps to `engine/data.py::_validate_candles`; conflicting duplicate bars now fail closed before ATR/RSI/structure. Tests are synthetic; no recovered historical WTI outcome or agriculture diagnostic output was replayed.

## Mapping from the retrieved IBKR session 9 record to current code

Source: Library file `Registro Studio IBKR - aggiornato 2026-10-20 sessione 9.md` (updated 2026-10-20).

| Recovered lesson | Current mapping | Test / status | Evidence limit |
|---|---|---|---|
| Historical API pacing: 10 requests/sec global; historical endpoint 10/sec and 50/min; maximum 1,000 bars/request; HTTP 429 requires backoff | Potential future IBKR data adapter only. Current `engine/data.py` uses Twelve Data, Biquote and Yahoo; do not apply IBKR quotas to those providers as if they were the same API. | No IBKR API call or adapter implemented in this PR. Existing provider request/backoff tests are separate. | Documentation fact, not a current Gagarin rate-limit measurement. |
| Vectorized research must not execute at the same close used to create the signal; use chronological/event-driven replay with costs, slippage and execution timestamps | `engine/trigger.py` closed-candle checks and existing scorecard/backtest work; this PR changes only candle ingestion integrity. | No new backtest or OOS metric in this PR. | No profitability claim. |
| Futures: expiry, physical delivery, certified inventories and calendar spreads can matter for coffee/energy; spot alone is insufficient near expiry | Instrument/contract metadata and expiry-aware provider routing remain a separate gap; current `engine/data.py` normalizes OHLCV but this change does not add a futures calendar. | No expiry/rollover test added here. | Required contract/inventory historical series were not validated in this run. |
| Options effects (positioning, skew/tail protection, dealer hedging, activity/dispersion, implied/spot dislocation and directional pressure) are context, not automatic direction | No options feed is currently validated in the operational path; no options-based direction rule was added. | Not implemented; must be tested as one feature against the baseline only if reliable point-in-time data are available. | The session 9 presentation explicitly says its visuals are illustrative, not a backtest; no predictive edge is inferred. |
| For every feature require `available_at <= decision_time` and keep event time separate from availability time | News/forecast timestamps and closed-candle trigger checks exist in current code; source-specific availability and decision-time auditing still needs end-to-end validation. | Existing timestamp tests plus PR #84 candle-conflict tests; no full end-to-end point-in-time replay in this PR. | Current tests prove local invariants, not global absence of look-ahead bias. |

This mapping distinguishes documented lessons from implemented and empirically validated behavior. The recovered session 9 file is a study register; it is not a Gagarin 100-rule catalog.



## 2026-10-27 — Reject boolean values at candle ingestion

- **Finding:** Python treats `bool` as a numeric subtype; `float(True)` becomes `1.0`. The candle normalizer and direct validator could therefore accept boolean timestamps, OHLC values, or volume as numeric market data. This is the same class of coercion that earlier scorecard fixes addressed for prices, now fixed at the market-data boundary.
- **Change:** `engine/data.py::_normalize()` rejects boolean inputs before coercion; `_validate_candles()` independently rejects rows with boolean timestamp/OHLCV fields for callers that bypass normalization.
- **Operational path:** provider payload → normalization → direct candle validation → duplicate/timestamp/OHLC checks → downstream ATR/RSI/structure.
- **Regression:** parameterized tests cover all six fields in both the normalizer and direct validator.
- **CI:** corrected code commit `d8b1c83d58ca0dc2e68f21f59398b3a8af3c3d1c` passed NEWS and Execution Layer; the latest PR head `a6c45d208d46f9cf4ca92c82070c3cef22864210` then passed all five workflows: general tests [40549192069](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549192069), Execution Layer [40549192068](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549192068), NEWS alert [40549192023](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549192023), Public Event Brain [40549191997](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549191997), and PAPER [40549191992](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549191992).
- **Deployment:** PR #84 branch only; no merge/deploy. Render build-pipeline quota remains exhausted.
- **Empirical limit:** ingestion-integrity tests only; no historical OHLCV replay or trading-performance claim. PAPER/DEMO only; no secrets, broker, orders, or Telegram test messages.


## 2026-10-27 — Reject boolean numerics in candle ingestion

- **Finding:** `_validate_candles()` is an ingestion boundary that may be called independently of `_normalize()`. Python treats `bool` as a subclass of `int`, so `float(True)` silently becomes `1.0`; a boolean timestamp, volume or internally consistent all-boolean OHLC row could otherwise pass numeric checks.
- **Change:** `engine/data.py::_validate_candles` now rejects boolean values in timestamp, OHLC and volume fields before float conversion. Existing identical-duplicate deduplication and conflicting-duplicate fail-closed behavior are unchanged.
- **Regression:** `tests/test_data_finite_values.py::test_validate_candles_rejects_boolean_numeric_values` checks boolean timestamp, volume, and all-boolean OHLC cases while retaining the minimum required valid history.
- **Commits:** code `1fb0a53a711c1305390ed668436b7d9dfe4e9845`; tests `e3a06af954e4fb6404032aaf2d2018d534ac3ef6`.
- **CI:** PASS on latest PR head `0ff2f410698f3ae16f6fd81221c1650e66957381`: general tests [40549301985](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549301985), NEWS alert [40549302495](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549302495), Execution Layer [40549302019](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549302019), Public Event Brain [40549302466](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549302466), PAPER [40549302098](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549302098). The first general run failed because a concurrent boolean guard used wrong parameter names; commit `d8b1c83d58ca0dc2e68f21f59398b3a8af3c3d1c` corrected them, and the latest full run passed.
- **Operational path:** provider response → `_validate_candles` → freshness/market status → indicator and setup calculation. Invalid rows are dropped before indicators; no trade direction is inferred.
- **Empirical limit:** synthetic regression tests only; no live-provider replay or OOS P&L result. This is data-integrity work, not a profitability claim.
- **Deployment:** PR #84 branch only; no merge/deploy. PAPER/DEMO only; no broker, real orders, secrets, or Telegram test messages.


### Follow-up CI correction — boolean candle guard

- The first general Gagarin integration run failed because the new guard referred to parameter names `high_price`/`low_price`/`close_price`, while `_normalize()` names them `high`/`low`/`close`. The failure was observed in the CI log (14 failures, 366 passed), not hidden.
- Corrected the identifier list in `engine/data.py` in commit `d8b1c83d58ca0dc2e68f21f59398b3a8af3c3d1c` (parameters are `high`, `low`, `close`). The initial general test run failed with 14 failed and 366 passed; after the correction, the general suite and all four other workflows passed on PR head `0ff2f410698f3ae16f6fd81221c1650e66957381`: general [40549301985](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549301985), NEWS [40549302495](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549302495), Execution [40549302019](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549302019), Public Event Brain [40549302466](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549302466), PAPER [40549302098](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40549302098). No runtime deployment was triggered.


## 2026-10-27 — Reject negative Unix timestamps at candle ingestion
- **Finding:** `_validate_candles()` rejected non-finite and future timestamps but could retain a finite negative epoch timestamp. That row is not a plausible market-candle timestamp for currently supported live instruments and could contaminate chronological indicator history if enough rows remain.
- **Code/test commit:** `1feff11fae8ada2f61c4b351bd530629f60ece65` updates `engine/data.py` and `tests/test_data_finite_values.py`.
- **Change:** reject `timestamp < 0` before duplicate/future checks. Valid non-negative timestamps continue through the existing OHLCV, duplicate, and future-time checks.
- **Operational path:** provider candles → numeric timestamp validation → negative/future/duplicate checks → OHLCV validation → freshness/ATR/RSI/regime. Invalid rows do not become directional signals.
- **Regression:** `test_validate_candles_drops_negative_epoch_timestamps` checks that the negative row is discarded while the remaining minimum valid history is retained.
- **CI PASS on code/test head:** general tests [40561191706](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40561191706); NEWS [40561191756](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40561179712); Public Event Brain [40561191868](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40561191868); Execution Layer [40561193144](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40561193144); PAPER [40561192144](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40561192144). Push and PR-triggered runs both passed.
- **Historical mapping:** IBKR session 9 requires explicit handling of malformed/missing/delayed market data and point-in-time timestamps; this change addresses only negative numeric epoch values, not session calendars, contract expiry/rollover, or stale positive timestamps.
- **Empirical limit:** synthetic regression only; no provider replay, outcome scorecard, OOS P&L, or profitability claim. It does not replace instrument-specific session/futures-calendar validation.
- **Deployment:** PR #84 branch only; no merge/deploy. PAPER/DEMO only; no broker, orders, secrets, or Telegram test messages.

## 2026-10-27 follow-up — reject epoch-zero market-candle timestamps

- **Finding:** the candle validator rejected negative Unix epochs but accepted timestamp `0`. For the currently supported live market instruments, epoch zero is not a plausible candle time and should not be allowed to proceed into freshness/indicator processing.
- **Change:** `engine/data.py::_validate_candles` now rejects `timestamp <= 0`, while retaining existing finite-value, future-time, duplicate/conflict, and OHLCV checks.
- **Regression:** `tests/test_data_finite_values.py::test_validate_candles_drops_non_positive_epoch_timestamps` is parameterized for both `-1.0` and `0.0`.
- **Commits:** code `25a4462af08abe2c16b2132a980bf25827826556`; test `2aba50c686f9e18719b471a8a343a8aaf92b2fd6`.
- **CI at log update:** five relevant workflows were triggered and were in progress: General tests [40566882116](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40566882116), Public Event Brain [40566882441](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40566882441), PAPER [40566882541](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40566882541), NEWS alert [40566882660](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40566882660), Execution Layer [40566882513](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40566882513). Recheck before treating the revision as validated.
- **Operational path:** provider candles → timestamp validation → duplicate/OHLCV validation → freshness/regime/ATR/RSI. This does not validate instrument-specific sessions or futures expiry/rollover.
- **Deployment/empirical limits:** PR #84 branch only; no merge/deploy. Synthetic regression only; no provider replay, OOS scorecard or profitability claim. PAPER/DEMO ONLY.

## 2026-10-27 — Diagnose epoch-millisecond timestamps at candle ingestion

- **Finding:** `_validate_candles()` treated an epoch-millisecond value (~1e12 today) as an ordinary future timestamp and skipped it. If enough second-based rows remained, a mixed-unit provider response could pass without an explicit unit-mismatch diagnostic.
- **Change:** `engine/data.py::_validate_candles` now fails closed with `TIMESTAMP_UNIT_MISMATCH_OR_OUT_OF_RANGE` for numeric timestamps >= 100,000,000,000, a conservative boundary well above plausible current Unix seconds. It does not silently divide by 1000 or guess provider units.
- **Regression:** `tests/test_data_finite_values.py::test_validate_candles_fails_closed_on_millisecond_epoch_timestamps` supplies a millisecond epoch alongside otherwise valid candles and asserts an empty result plus the explicit error.
- **Operational path:** provider payload → timestamp parsing/unit sanity → future/duplicate/OHLCV checks → freshness/ATR/RSI/regime. The provider fallback/error path can now distinguish this case from a merely short history.
- **Commits:** code 5dc0e5a629bed4f414a9d7f5f3dec4e0cfa23032; regression test 248dbab453d9ee28b66b584115fe4a2a48b5d849.
- **CI verified:** code/test commit `248dbab453d9ee28b66b584115fe4a2a48b5d849` passed the Gagarin NEWS alert workflow [40569414697](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40569414697) and Execution Layer workflow [40569414736](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40569414736). The other three previously relevant workflows were not triggered for this commit/path combination, so this is not a claim that all five ran on this revision. The subsequent commit only updates this log.
- **Deployment:** PR #84 branch only; no merge/deploy. Render runtime/workspace logs are not accessible through this run's connected tools, so the live deploy commit and Telegram/GDELT runtime status cannot be freshly confirmed.
- **Empirical limit:** synthetic regression only; no live provider replay, futures contract calendar/rollover validation, OOS scorecard or P&L result. PAPER/DEMO only; no broker or orders.


## Historical research recovery — IBKR session 9 and 100-point catalog status (2026-10-27)

- **Library source actually retrieved:** `Registro Studio IBKR - aggiornato 2026-10-20 sessione 9.md`. It records the options webinar as a PDF/presentation consulted, not a watched recording; the slides are explicitly illustrative and not a backtest. Positioning, skew, dealer hedging and options activity therefore cannot be treated as automatic directional proof and must be tested against the existing baseline only when reliable point-in-time data exist.
- **Futures lesson:** the record proposes comparing 12-month carry, front-month carry and curve-slope momentum with expiry, seasonality, liquidity, rollover costs and slippage. This applies only to actual futures curves/contracts, not automatically to spot/CFD instruments. No contract calendar or rollover engine was added in this change.
- **API lesson:** session 9 documents IBKR Web API pacing (global 10 req/s; historical endpoint 10 req/s and 50/min; up to 1,000 bars/request). These limits apply to an IBKR adapter, not automatically to the current Yahoo/Twelve Data/Biquote providers.
- **Mapping to this branch:** `engine/data.py::_validate_candles` rejects epoch-millisecond/out-of-range numeric timestamps rather than silently treating them as ordinary future seconds; `tests/test_data_finite_values.py::test_validate_candles_fails_closed_on_millisecond_epoch_timestamps` covers the case. Code/test commit `248dbab453d9ee28b66b584115fe4a2a48b5d849` passed NEWS alert [40569414697](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40569414697) and Execution Layer [40569414736](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40569414736); other three relevant workflows did not trigger for this path/commit, so they are not claimed as passed on this revision.
- **Historical records:** the available record includes the 2026-09-21 Shadow error `extract_structure_ok() missing ... direction`, 2026-09-22 Rame `SETUP NONE / TRIGGER False / REGIME UNKNOWN`, and 2026-09-25 PAPER WTI LONG levels without a recovered outcome. None is counted as a completed win/loss or proof of edge.
- **100-point catalog:** no complete original 1–100 catalog was found in the Library or repository search. The session-9 file is a study register, not that catalog. Missing lessons are not inferred.
- **Deployment/empirical status:** PR #84 branch only, no merge/deploy. Render runtime/workspace logs are not accessible through this run, so the live commit, GDELT logs and `DATABASE_URL` state cannot be freshly confirmed here. Synthetic test only; no OOS scorecard or profitability result.


## 2026-10-27 — Reject timezone-naive candle timestamps outside an explicit UTC adapter

- **Finding:** `engine/data.py::_parse_time` silently interpreted every naive ISO datetime as UTC. That is only justified when the provider request explicitly declares UTC; for other providers it can shift candle times and contaminate freshness/session diagnostics.
- **Implemented on PR #84 branch:** generic parsing now rejects naive datetime strings (and boolean timestamp values). The Twelve Data adapter may attach UTC to naive response timestamps only because its request explicitly sends `timezone=UTC`; other provider timestamps with no timezone are rejected so the normal provider fallback can try another source.
- **Files:** `engine/data.py`; regression coverage in `tests/test_data_finite_values.py`.
- **Tests:** naive ISO rejected; explicit UTC accepted; mocked Twelve Data response proves the adapter requests UTC and normalizes the naive response without network access.
- **CI:** pending for this commit. Prior PR #84 CI passed on head `a9da3012fbb9bc63e7471811299d40203b4f6b66` for its earlier duplicate/millisecond/boolean checks; that result does not cover this new timezone change.
- **Runtime/deployment:** no merge/deploy; Render build-pipeline minutes are exhausted. Runtime logs at 2026-10-27 20:02 UTC show GDELT ReadTimeout backoff (300/600/1200s) and `LOCAL_CSV_NO_DATABASE_URL` / `DATABASE_URL missing`; the journal is not claimed durable. Telegram webhook was active in that sample, but that does not prove market-alert delivery.
- **Limits:** mocked adapter test only; Biquote's live timestamp format was not re-queried, and may now fall back if it returns naive timestamps. No OHLCV replay, OOS scorecard or profitability claim. PAPER/DEMO ONLY.


## Final verification — explicit candle timezone handling (2026-10-27)

- **Code/test head:** `9ce15f6e0534bd97387d818657002584910aacb6`.
- **CI PASS on that head:** general tests [40577234473](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40577234473), Public Event Brain [40577234537](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40577234537), NEWS alert [40577234544](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40577234544), Execution Layer [40577234662](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40577234662), and PAPER [40577234793](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40577234793). The following commit is documentation-only; no code changed after the tested head.
- **Runtime evidence:** at 2026-10-27 20:02 UTC, Render logs recorded GDELT `ReadTimeout` backoff of 300/600/1200 seconds, Telegram webhook active and a command received. The same log window reports `LOCAL_CSV_NO_DATABASE_URL` / `DATABASE_URL missing`; the journal is not durable on the observed configuration.
- **Deployment:** latest observed Gagarin deploy attempt for main SHA `99ad72b69cddbed0f80ef9f671c5b70deb9df024` failed at 2026-10-27 12:48:24 UTC with `pipeline_minutes_exhausted`. No merge/deploy was performed for PR #84.
- **Empirical limit:** timezone tests use a mocked Twelve Data response and explicit `timezone=UTC` request parameter. Biquote's current timestamp format was not re-queried; a naive timestamp from that provider will now be rejected so provider fallback can proceed. No market replay, OOS scorecard or profitability claim. PAPER/DEMO ONLY.


## Implementation-ledger cross-check — separate candle and feedback timestamp paths (2026-10-27)

- Added `DATA-004` to `docs/gagarin-implementation-ledger.md` for the tested `engine/data.py` candle timestamp policy: generic naive ISO strings are rejected; the Twelve Data adapter attaches UTC only because the request explicitly sets `timezone=UTC`.
- **Unresolved:** existing `DATA-002` describes a different path in `engine/feedback.py` that still assumes UTC for naive timestamps. PR #84 does not change that feedback path; it needs its own strict parser and regression test. This distinction avoids claiming a system-wide timezone fix from a data-engine change.
- CI for code/test head `9ce15f6e0534bd97387d818657002584910aacb6` passed all five workflows; this commit changes documentation only. No merge/deploy; no OOS or profitability result.
