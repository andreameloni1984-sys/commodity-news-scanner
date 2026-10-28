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


## 2026-10-28 — Fail closed on malformed missed-move audit parameters

- **Finding:** `evaluate_missed_moves()` previously coerced `horizon` and `start` with `int()` (silently truncating fractional inputs and accepting booleans) and clamped negative thresholds to zero. A negative threshold could classify trivial movements as events rather than flagging an invalid experiment.
- **Change:** `_strict_integer_parameter()` accepts integer values only (including integral finite floats and integer strings), rejects booleans/fractions/non-finite values, and validates horizon >= 1 and start >= 0. Non-finite, boolean, malformed, or negative thresholds return `INVALID_PARAMETERS` with zero forecasts. The existing minimum warm-up start of 35 bars remains.
- **Operational path:** OHLC input → parameter validation → causal forecast from prior bars → future excursion count. Invalid configuration is rejected before forecasting; no trade decision or execution path is changed.
- **Regression:** `test_invalid_audit_parameters_fail_closed_without_coercion` covers fractional/boolean/non-finite/zero horizon, invalid start, and malformed/negative thresholds. Existing quiet-series, event, insufficient-data and non-finite threshold tests remain.
- **Validation:** tests added to the branch. No GitHub Actions run or full-suite PASS is visible for this branch; no empirical or OOS result is claimed.
- **Deployment:** research branch only; no PR, merge, Render build or deploy. The separate timestamp-order guard remains on research branch `fix/gagarin-audit-timestamp-order-20261028-r7` and is not claimed to be in `main`.
- **Safety:** PAPER/DEMO ONLY; no secrets, Telegram test messages, broker connection or orders.


## 2026-10-28 — Verification snapshot for missed-move parameter guard

- **Base:** `main` at `99ad72b69cddbed0f80ef9f671c5b70deb9df024`; branch is 3 commits ahead, 0 behind.
- **Code:** `12106e1517eaae2753b94c8434fe74740c74a6f6` (`engine/missed_move_validation.py`).
- **Regression test:** `8b3b5cd8c56d096e21c4c7f9630c60ea84c55245` (`tests/test_missed_move_validation.py`).
- **Prior log commit:** `17f28beec75d3d34df9472c59f172f8b8d9db914`.
- **Checks:** GitHub combined status is empty and the available commit-workflow query returned no runs for the branch; CI is therefore **not verified**. An independent Python smoke harness rejected 10 malformed parameter cases and accepted two valid cases; it is not a substitute for running the repository test suite.
- **Deployment:** no PR, merge or deploy. Render workspace is not selected; service/deploy/Telegram logs were not inspected.
- **Limits:** this validates audit configuration only; no market replay, walk-forward, OOS or profitability result is claimed. Timestamp-order validation remains on a separate research branch and is not in `main`.
