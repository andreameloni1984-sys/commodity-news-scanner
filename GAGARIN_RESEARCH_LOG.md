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

## 2026-10-26 — Enforce minimum reward/risk and reject late news alerts

- **Research basis:** the IBKR study register records that volatility and news are not directional proof, and that target geometry, execution costs, and out-of-sample validation must be tested. The existing Gagarin risk path uses TP1/TP2/TP3 targets, but the news-alert boundary only checked positive finite values and directional ordering.
- **Implemented on branch `fix/gagarin-news-alert-minimum-rr-20261026`:** `telegram/news_monitor.py` now requires TP1 >= 1.5R, TP2 >= 2.0R when present, TP3 >= 2.5R when present, monotonic directional target order, and a live price still inside the stop/TP1 bracket. It also checks that remaining R/R from the current quote to TP1 is at least 1.5R to suppress late entries.
- **Operational path:** `poll_news_once -> _confirmed_setups -> _valid_signal_levels -> _format_news_alert`. News impact remains a hypothesis; the gate also requires the existing live Gagarin trigger, matching direction, measurable post-baseline reaction, and known price source.
- **Files:** `telegram/news_monitor.py`, `tests/test_news_monitor.py`, this log.
- **Regression coverage:** LONG/SHORT valid brackets, TP1/TP2/TP3 below their R minima, quote already beyond TP1, and TP3 without TP2.
- **Limits:** deterministic tests only; no claim of improved profitability or out-of-sample validation. This gate does not account for spread/slippage and does not replace the main Risk Governor. PAPER/DEMO ONLY; no orders or Telegram test messages. Render deployment remains intentionally untouched while build minutes are exhausted.

## 2026-10-27 — Fail closed on invalid news-reaction threshold configuration

- **Finding:** GAGARIN_NEWS_MIN_REACTION_PCT was parsed inline through max(0.0, float(...)). NaN can silently become a zero threshold, while malformed text can raise during setup classification; either behavior makes configuration handling unreliable.
- **Implemented:** _configured_news_min_reaction_pct() accepts only finite, non-negative values. An invalid value suppresses news setups and logs the setting name only (never a secret or its value).
- **Files / path:** telegram/news_monitor.py, tests/test_news_monitor.py; poll_news_once -> _confirmed_setups -> _valid_signal_levels -> alert formatting.
- **Regression:** NaN, positive/negative infinity, negative and malformed settings suppress an otherwise valid PAPER setup; 0.05% still allows the valid fixture.
- **Validation:** code commit 4710d7ceb7233d67fe810b8c350dd84f1a3a2b84; test commit fa9c315c6e6b4728be3ca8eaa689e43f60ec64d2. CI must be checked on the final PR head.
- **Limits:** configuration validation only; no market replay, spread/slippage model or out-of-sample profitability claim. No Render deployment, Telegram test, broker or order. PAPER/DEMO ONLY.
