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


## 2026-10-27 — Respect provider Retry-After on HTTP 429
- **Finding:** `engine/data.py::_request_json` used fixed exponential sleeps after HTTP 429 and ignored a provider's `Retry-After` header. This can retry too early or keep the synchronous monitor waiting when the server requests a long cooldown.
- **Change:** parse numeric and HTTP-date `Retry-After`; honor delays up to 30 seconds; when the requested delay is longer, return a typed 429 cooldown error so provider fallback can proceed without retrying early. Missing/malformed headers retain the prior exponential fallback.
- **Operational path:** provider request → HTTP status handling → bounded retry or provider fallback → normal data validation. No market direction is inferred from rate limits.
- **Files:** `engine/data.py`; regression coverage in `tests/test_data_retry_after.py`.
- **Tests:** four tests cover numeric seconds, HTTP-date, long cooldown/no premature retry, and malformed header fallback. CI PASS on code/test head b5a00833410ddd637489e7c657236e856c9d27bd: NEWS run 40559762340, Public Event Brain 40559762342, general tests 40559762420, PAPER 40559762284, Execution Layer 40559762374. The follow-up commit in this log is documentation-only.
- **Research mapping:** IBKR session 9 documents API pacing limits and HTTP 429; this implementation applies the general backoff principle to Gagarin's existing data-provider client, not IBKR-specific numerical limits to other providers.
- **Deployment:** research branch only; no merge/deploy. Render build-pipeline quota remains exhausted.
- **Empirical limits:** tests are mocked; no live provider call or measured reduction in throttling has been claimed. PAPER/DEMO ONLY.


## Recovered historical records — 2026-10-27
- **Library source:** “Registro Studio IBKR - aggiornato 2026-10-20 sessione 9.md” records API pacing, the distinction between observed facts and author interpretations, point-in-time availability, spread/liquidity, futures expiry/rollover and the need to compare optional features with a baseline. It explicitly states that options webinar material was a presentation consulted, not a backtest.
- **API limits in the IBKR record:** 10 requests/second globally; historical endpoint 10 requests/second and 50/minute; up to 1,000 bars per historical response and documented concurrency limits. These limits are IBKR-specific and are not copied numerically to Yahoo/Twelve Data/Biquote.
- **Session 9 priorities:** test Wilder RSI against a simple-average reference and edge cases; record event_time, available_at, decision_time; compare options/positioning features against baseline; study futures expiry/rollover; use spread/liquidity and costs in empirical validation.
- **Recovered late-September note (2026-09-25):** a historical PAPER run recorded a WTI LONG candidate with entry 91.357, SL 91.1224, TP1 91.709, TP2 91.8263, TP3 91.9436, RR3 2.50. No subsequent outcome was recovered; this is not counted as a win or loss.
- **Recovered historical PRs:** PR #11 (merged 2026-10-06) recorded RR1/RR2/RR3 thresholds 1.5/2.0/configured minimum and a legacy timestamp-freshness check; PR #15 (merged 2026-10-07) recorded a contextual historical-analog forecast, not a calibrated probability.
- **Current code mapping:** engine/data.py::_request_json → HTTP 429 handling → bounded retry or provider fallback; regression file tests/test_data_retry_after.py; PR #85. CI passed on code/test head b5a00833410ddd637489e7c657236e856c9d27bd (five workflow runs listed above). No live provider experiment or return uplift claimed.
- **Catalog status:** the complete original 100-point numbered catalog was not found in the retrievable records; no missing entries are reconstructed or presented as original.


## 2026-10-28 — honor HTTP-date Retry-After in source cooldowns
- **Finding:** `engine/data.py::_request_json` supports numeric and HTTP-date `Retry-After`, but the separate exception-driven news-source cooldown `telegram/news_monitor.py::_source_failed` parsed numeric seconds only. A valid HTTP-date could be ignored and a 429 source retried after the default cooldown rather than the provider's requested time.
- **Change/files:** `telegram/news_monitor.py::_source_failed` now parses timezone-aware HTTP-date values using the existing `email.utils` import; invalid/naive values keep the exponential fallback and valid delays remain capped at `SOURCE_BACKOFF_MAX_SECONDS`.
- **Regression:** `tests/test_news_monitor.py::test_source_failed_honors_http_date_retry_after` uses a mocked 429 with a future HTTP-date and verifies the source cooldown is near 40 minutes rather than the 15-minute default.
- **Operational path:** feed request exception → source failure cooldown → next eligible poll. No market direction is inferred from rate-limit metadata.
- **Validation:** mocked regression only; no live provider call or measured reduction in throttling. CI result and commit SHA will be recorded in PR #85 after the run completes.
- **Deployment/safety:** research PR #85 only; no merge/deploy. If runtime `DATABASE_URL` is absent, journal persistence is not considered durable. PAPER/DEMO ONLY.


## 2026-10-28 — Make local journal fallback visible

- **Finding:** `telegram/news_monitor.py::_journal` fell back to local JSONL when `state_store.append_event_journal` returned false, but that path was silent unless the database call raised. This could obscure that a local file, whose persistence depends on the runtime filesystem, is being used instead of the database journal.
- **Change/files:** `telegram/news_monitor.py` now emits one warning per process when the JSONL fallback is used, explicitly saying durability depends on local-storage persistence configuration. The fallback still writes the audit rows; no database or secret values are inspected.
- **Regression:** `tests/test_news_monitor.py::test_news_monitor_warns_once_when_journal_uses_local_fallback` verifies the warning appears once and both records are written to the temporary JSONL file.
- **Commits:** code `6dbb94378764c1d5126e326083a0a03ad0792f2d`; test `dfe962b335ae789e42f7d54b7bef8e915c8bbe29`.
- **CI:** NEWS alert tests passed on the test commit, run [40611279839](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40611279839). Execution Layer, Public Event Brain, PAPER and general tests were still running when this entry was written; no all-green claim is made for those runs here.
- **Operational path:** event → `_journal()` → PostgreSQL append if configured → explicit local JSONL fallback warning → file append. The warning does not prove runtime `DATABASE_URL` is absent; it makes fallback visible when the DB append returns false.
- **Deployment/limits:** PR #85 only; no merge/deploy. Render runtime logs were not accessible in this run. Local file durability is not guaranteed without persistent storage. Mocked regression only; no trading performance claim. PAPER/DEMO ONLY.
