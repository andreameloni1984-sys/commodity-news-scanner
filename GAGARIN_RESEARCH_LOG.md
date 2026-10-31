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


## 2026-10-28 — Trim Gagarin's active commodity universe

- User asked to remove unnecessary commodities. Active commodity set is now Gold, Silver, Copper, WTI, Brent, Wheat, Corn, and Soybean. The eight Forex instruments are retained as a separate group.
- Removed Platinum, Palladium, Rice, Sugar, Cocoa, Coffee, Gasoline, and Natural Gas from the active universe.
- Added explicit Yahoo fallback mappings for Copper (`HG=F`), Wheat (`ZW=F`), Corn (`ZC=F`), and Soybean (`ZS=F`), and registered Wheat/Corn/Soybean in the agriculture symbol/term maps and provider order.
- Added regression tests for the eight retained commodities, removed symbols, preserved Forex group, and explicit provider routing.
- This verifies configured routing only; live availability and data freshness still require the scheduled run to confirm. CI must pass before merge.
- Change is on branch `chore/gagarin-trim-commodity-universe-20261028`. No merge/deploy, no Telegram test message, PAPER/DEMO only.


## 2026-10-31 — Add free SILV spot references for Gagarin gold and silver

- **Finding:** Gagarin had a Yahoo futures execution quote and an optional delayed Narwhal futures reference, but no separately recorded spot reference for its two precious-metal futures instruments.
- **Provider verification:** the official SILV DATA documentation states that its JSON endpoint is free and requires no authentication; precious-metal spot observations are published on a 15-minute schedule. The public JSON endpoint was opened successfully during this run. The returned snapshot had response timestamp `2026-10-31T21:50:08.963Z` and gold/silver `last_updated` timestamps around `21:46Z`; at the time of this run (22:42Z) those values were older than the bot's 30-minute reference limit and are not used as current prices.
- **Implemented on branch** `feat/gagarin-silv-spot-reference-20261031`: add SILV DATA as a reference-only provider for XAU/USD and XAG/USD. A single response is cached for 900 seconds and shared between gold and silver. The code uses the provider's `last_updated` field—not its response-generation timestamp or rounded `data_age_minutes`—to calculate age.
- **Per-price provenance:** record provider, returned symbol, source timestamp, response timestamp, local receipt time, USD, `troy_oz`, price, bid/ask, age, status, and raw provider-reported component quotes with their own timestamps/ages/status. Component names are recorded as provider-reported and are not asserted to be independently audited.
- **Basis rule:** SILV is SPOT and Yahoo execution is FUTURES_CONTINUOUS. The code never writes SILV into execution price/ATR/entry/SL/TP. It keeps `deviation_pct` null and reports any same-unit/currency comparison separately as `basis_spot_minus_futures_pct`, only when both reference and execution quotes are within their permitted freshness states and execution status is LIVE.
- **Scope:** copper is deliberately excluded from SILV integration because the inspected endpoint response listed Yahoo among copper's component sources, which would overlap the Yahoo execution provider. No averaging across source components is performed.
- **Files:** `engine/data.py`; `tests/test_silv_spot_reference.py`; `tests/test_narwhal_futures_reference.py`.
- **Commits:** configuration `c18aecf75c68cd9377769260bfc93223ba9721cf`; implementation `b88236a631b352f0512a5632df9fe00f48cf6a7c`; existing-test isolation `291d726c427be01a74cbb3d15bf99de5c9db421e`; new tests `1bfab4259c31519168db47b8bb197677ff1ba9b4`.
- **Tests:** six new offline mocked regressions cover no-auth request/provenance, component metadata, shared cache, source-timestamp freshness, separate spot/futures basis, timeout behavior, and execution-price isolation. Existing Narwhal finalizer test is isolated from the new provider. GitHub Actions must pass on the PR before this is considered verified.
- **Limits:** the endpoint response inspected during this run is an old snapshot, not a current trading quote. No direct Gagarin monitor request, live Telegram delivery, deploy, or trade is claimed. PAPER/DEMO only; no paid API or real order.
