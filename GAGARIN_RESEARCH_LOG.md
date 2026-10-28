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


## 2026-10-28 — Match Gagarin news keywords as whole terms

- **Finding:** `classify_event()` used substring matching for asset-family and directional keyword sets. This let `oil` match inside `spoiled`, and `war` inside `forward`, potentially adding unrelated oil/metals assets or a false provisional directional hit.
- **Change/files:** added `_contains_market_term()` in `telegram/news_monitor.py`; asset-family detection, crop-specific asset selection, and bullish/bearish term matching now use case-insensitive whole-word/phrase boundaries. Hyphen variants are normalized to spaces. The headline itself is not rewritten in output.
- **Regression:** `tests/test_news_monitor.py::test_keyword_fragments_do_not_create_asset_or_direction` rejects both “The deal was spoiled by a routine delay” and “The forward outlook was unchanged after a routine update”. Existing positive tests cover oil inventories, sanctions, crop catalysts and macro terms.
- **Operational path:** public RSS/GDELT title → event classification → provisional impact → baseline capture → existing live price/volume/trigger checks → PAPER alert. This prevents fragment-only matches; it does not make news a confirmed trade.
- **Commits:** code `87c12559fb6b00ef062c2565de1e42d3c35899f5`; test `087b91b66cc81bdd0df1179f1effceb8b939d13c`.
- **CI:** pending GitHub Actions validation; any positive-control failure must be corrected before calling this verified.
- **Deployment/limits:** new research branch from `main`; no merge/deploy. Synthetic classifier tests only; no live-feed replay, event study, or out-of-sample performance claim. No durable-journal claim while runtime `DATABASE_URL` is unverified. PAPER/DEMO ONLY.


## 2026-10-28 — Verify whole-term matcher escaping before CI

- **Review correction:** a source inspection found that the first generated helper had over-escaped the regular-expression backslashes. Corrected the helper to use literal Unicode dash characters and a real `\w` word-boundary class before opening the PR. The initial branch commit is superseded by this correction and must not be treated as verified.
- **Corrective code commit:** `d1bc48ac8da6d3513f13edb4008d2d28a50e8bca`; regression test remains `087b91b66cc81bdd0df1179f1effceb8b939d13c`.
- **Next verification:** open the draft PR to trigger CI and require all existing positive controls plus the fragment-negative regression to pass. No merge/deploy.
