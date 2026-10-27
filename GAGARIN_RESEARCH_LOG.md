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

