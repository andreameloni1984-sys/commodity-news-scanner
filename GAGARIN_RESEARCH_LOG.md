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

## 2026-10-27 — Reject ambiguous RSI Wilder periods

- **Finding:** `engine/regime.py::_rsi_wilder` used `int(period)`, which silently truncated fractional periods such as 14.5 and accepted booleans; infinity could raise an uncaught `OverflowError`.
- **Change:** reject booleans, non-finite and fractional periods; catch type, value and overflow conversion errors. Positive integer periods and integral numeric values preserve the existing Wilder calculation.
- **Files:** `engine/regime.py`; `tests/test_pipeline.py`.
- **Regression coverage:** fractional, boolean, NaN, positive/negative infinity, malformed text, zero, negative, an integer too large to convert to float, and a valid integral float. Existing rising/falling/flat reference cases remain covered.
- **Operational path:** OHLC closes → `_rsi_wilder()` → regime diagnostics; invalid configuration yields `None`, not a guessed period.
- **CI:** PASS on PR head `0de6e53b0d2be0d4ce0a49960e4a35a1d32eda12`: Public Event Brain `40469309164`, PAPER `40469309231`, NEWS alert `40469309091`, Execution Layer `40469309175`, and main tests `40469309188`.
- **Deployment:** no merge or deploy. Render workspace build-pipeline minutes are exhausted. Latest observed Gagarin cloud logs explicitly reported `DATABASE_URL missing` and `GAGARIN PERSISTENCE DISABLED`; the journal is not confirmed durable. GDELT emitted `ReadTimeout` with a 300-second retry.
- **Empirical validation:** no out-of-sample or profitability test; this is indicator-input integrity only.
- **Safety:** PAPER/DEMO ONLY; no broker, order, or Telegram test message.

## 2026-10-27 — Reject overflowed price deltas in Wilder RSI

- **Finding:** validating each close as finite is insufficient: subtracting opposite extreme finite floats (for example, -1e308 and +1e308) overflows to infinity. The previous RSI calculation could then return a plausible endpoint or NaN from invalid intermediate arithmetic.
- **Change:** `engine/regime.py::_rsi_wilder` now rejects non-finite close deltas and non-finite smoothed gain/loss values, checks the denominator, and uses the algebraically equivalent `100 * avg_gain / (avg_gain + avg_loss)` formula to avoid an unnecessary gain/loss ratio overflow.
- **Regression:** `tests/test_pipeline.py::test_rsi_wilder_rejects_overflowed_close_differences` checks both signs of extreme finite closes.
- **Operational path:** OHLC closes → `_rsi_wilder` → regime diagnostics. Invalid arithmetic returns `None`; no directional value is fabricated.
- **CI:** code and test have been committed to PR #83; the new CI run is pending at time of this log entry. Prior PR head checks passed, but they do not validate this new change.
- **Deployment:** no merge/deploy; Render build-pipeline minutes remain exhausted.
- **Empirical limit:** numerical-integrity regression only; no OOS profitability claim.
- **Safety:** PAPER/DEMO ONLY; no broker, order, or Telegram test message.

## 2026-10-27 — Recover the late-September agricultural-data diagnostic record

- **Historical source:** prior conversation record from 2026-09-25 says the GitHub Actions run executing `python main.py` marked four Yahoo-backed agricultural feeds STALE: Caffè, Cacao, Riso and Zucchero.
- **Artifacts named in the historical record:** repository-root `diagnostic_agri.py` (v1.0, with v2.0/v3.0 variants supplied in the same chat) and `engine/data.py` v5.0; the prior record cites `de28b59` as the earlier v5.0 commit and says v5.1 later broke data loading. The actual diagnostic output resolving symbols/titles was not recovered, so this is not a current reproduction of the stale-data result.
- **Current code mapping:** `engine/data.py` provider routing → OHLC/timestamp/history validation → freshness and market-status classification → Gagarin engine; `diagnostic_agri.py` is a separate Twelve Data catalog/symbol/freshness diagnostic. The current `main` file header still identifies `engine/data.py` as v5.0 and the diagnostic file exists.
- **Tests / CI:** no agriculture-feed diagnostic was executed in this run; the RSI overflow regression is a separate numeric-integrity change. A follow-up should replay the diagnostic with non-secret, timestamped provider responses and assert that STALE data never enters the decision path.
- **Empirical limit:** the historical note establishes that a stale-data incident was reported, not that the same feeds are stale now or that any agricultural signal was profitable.
- **Safety:** PAPER/DEMO only; no provider secrets read, no broker, no orders, no Telegram test message.

