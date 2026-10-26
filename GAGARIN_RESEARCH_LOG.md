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

## 2026-10-26 — Preserve swing-pivot point-in-time availability

- **Finding:** the structure engine confirmed pivots only after the configured right-side candles, but each pivot record exposed only the pivot candle's time. A historical evaluator could mistakenly treat that earlier event time as the time the pivot became knowable.
- **Implemented:** `engine/structure.py` now records `event_time`, UTC-normalized `available_at` from the confirmation candle, and `confirmation_index` for both swing highs and lows. The legacy `datetime` field is preserved with timestamp-key fallback. Missing, malformed, naive, or non-monotonic timestamps produce no usable `available_at`; the index still identifies when the confirmation bar arrives.
- **Regression tests:** `tests/test_pipeline.py` checks that a pivot is absent before right-side confirmation, becomes available only at the confirmation bar, and fails closed on invalid timestamps.
- **CI validation on final branch head `3919ec8c49a22d2db8a24e361be8f0d4744d0a56`:** all five workflows passed — [SOYUZ GAGARIN Tests](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40397488899), [SOYUZ GAGARIN PAPER](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40397488894), [NEWS alert tests](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40397488943), [Public Event Brain](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40397488786), and [Execution Layer](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40397488813). No local test run is claimed. This is not live-market or profitability validation. Any offline evaluator must use `available_at`/`confirmation_index`, not `event_time`, when deciding whether a pivot was knowable.
- **Deployment/safety:** no Render deployment, Telegram test message, broker, or order was triggered. PAPER/DEMO ONLY.



## 2026-10-26 — Require a post-breakout candle before confirming a retest

- **Finding:** `engine/structure.py::_detect_retest` scanned the last three candles and could label a touch that occurred before the breakout as a current retest. This can make the structure/setup path treat a pre-breakout event as if it were a later confirmation.
- **Implemented in PR #74:** retest validation now inspects only the current candle, requires the previous candle to have closed beyond the ATR breakout buffer, checks finite numeric inputs, and fails closed on malformed values. LONG and SHORT use mirrored conditions.
- **Files:** `engine/structure.py`; `tests/test_pipeline.py`.
- **Regression tests:** a historical touch before breakout no longer counts; valid post-breakout retests are checked for both directions; non-finite prices are rejected.
- **CI on code/test commit `adc7eb82a2decd49fb273490dab5feecc12e986d`:** all five workflows passed — [SOYUZ GAGARIN Tests](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40404825468), [PAPER](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40404825654), [NEWS alert](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40404825404), [Public Event Brain](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40404825326), and [Execution Layer](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40404825395).
- **Validation limits:** deterministic synthetic regression only; no live-market or out-of-sample profitability claim. This change intentionally favors false negatives over retests that cannot be shown to occur after a breakout. No Render deploy or Telegram test message was triggered. PAPER/DEMO ONLY.


## 2026-10-26 — Retest OHLC integrity gate (run follow-up)

- **Finding:** `_detect_retest()` checked finiteness of high/low/close, but it did not require an open price or validate that each candle's OHLC range contained its open and close. A malformed provider bar could therefore be interpreted as a valid breakout retest.
- **Implemented:** `engine/structure.py` adds `_validated_ohlc_bar()`. Both the previous breakout-confirmation bar and current retest bar must have finite open/high/low/close and internally consistent geometry (`high >= low`, `high >= max(open, close)`, `low <= min(open, close)`). Missing or inconsistent OHLC fails closed; no directional decision is created from the malformed bar.
- **Regression tests:** `tests/test_pipeline.py` now supplies full OHLC for LONG/SHORT valid retests and tests missing-open/inconsistent-range rejection plus the existing non-finite-price rejection.
- **Code/test commit:** `b9faf45074a970c500110771ea9c9f32c0b13145`.
- **CI:** all five PR workflows passed on that commit: SOYUZ GAGARIN Tests (run 40411139215), PAPER (40411139173), NEWS alert (40411139393), Public Event Brain (40411139212), Execution Layer (40411139264).
- **Validation limit:** deterministic regression tests only; no replay against live provider bars, no out-of-sample P&L result, and no profitability claim. A stricter gate may reject provider data that omits open; this is intentional fail-closed behavior pending data-quality validation. No Render deployment, Telegram test message, broker or order. PAPER/DEMO ONLY.
