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

## 2026-10-27 — Exact spot-symbol matching for news baselines

- **Finding:** `_asset_matches()` used substring checks such as `"XAU" in symbol`, which could match unrelated symbols (for example `XAUTUSDT` or `NOTXAUUSD`) and contaminate a news baseline. Futures symbols must not be silently mixed with spot prices before contract metadata/rollover is modeled.
- **Change:** normalize separators and match a finite allowlist of complete known spot aliases for WTI, Brent and precious-metal spot pairs; retain commodity-name matching. Futures tickers such as `GC=F` remain unmatched by symbol alone until an explicit contract/calendar mapping exists.
- **Files:** `telegram/news_monitor.py`; `tests/test_news_monitor.py`.
- **Regression coverage:** standard slash/no-slash spot symbols match; substring lookalikes and a futures ticker without contract metadata do not.
- **Code commit:** `5ddc3df2053132a54efca94eb27a5ee434b1edf7`; **test commit:** `f80f595f7f9a812074564b0b457bf6fc6e90cfd7`.
- **CI:** PASS on PR head commit `298715530e50ff549a8cde5d765083404a9463a6`: NEWS alert run `40460787644`, Execution Layer `40460787647`, Public Event Brain `40460787728`, PAPER `40460787705`, general tests `40460787744`. No empirical signal-performance test was run.
- **Deployment / limits:** research branch only; no Render deploy. No empirical signal-performance test was run.
- **Safety:** PAPER/DEMO ONLY; no secrets read, Telegram test message, broker or order.

## 2026-10-27 — Reject boolean prices in news outcome scorecard

- **Finding:** Python converts `True` to `1.0` and `False` to `0.0`; the scorecard's direct float conversions could therefore admit a boolean alert price or reaction price, corrupting the outcome ledger.
- **Change:** reject boolean values before numeric conversion for both alert-entry prices and later reaction prices; treat overflow as invalid input.
- **Regression test:** a boolean alert price is excluded; a boolean reaction price does not score the valid alert and leaves it pending while the evaluation window remains open.
- **CI:** code and test committed to the existing exact-symbol PR branch; a fresh Actions run must confirm the new revision. No local execution or live-market replay is claimed.
- **Limits:** data-integrity fix only; no profitability claim. No merge or deploy. Render quota remains a deployment constraint; no Telegram test message or order was sent.

## 2026-10-27 — Audit of the historical 100+ point register

- **Recovered directly from prior conversation context:** point 100, “Execution Regime: Volatility × Liquidity” (Calm/Liquid, Thin, Fast/Liquid, Stress; proposed module `EXECUTION_REGIME_ENGINE`); point 101, “Overnight Risk Engine / Next-Session Volatility Forecast” (overnight WTI returns/range/realized volatility/volume/jumps as a next-session volatility input, explicitly not direction); point 102, “Setup Transferability / Instrument-Specific Edge”; point 103, “Sweep Validity / Continuation-vs-Reversal” (an isolated sweep is not proof of reversal; distinguish break, follow-through, acceptance/rejection and wait for structure/trigger).
- **Source audit:** the Library file “Registro Studio IBKR - aggiornato 2026-10-20 sessione 9.md” is the IBKR study register, with numbered session material through 32; it is not the original 100+ point register. Points 1–99 are not fully present in the retrieved historical context and are not reconstructed here.
- **Implementation mapping:** the current regime engine uses normalized price movement versus ATR, but it does not yet provide a verified volatility × liquidity state matrix (point 100). The scorecard boolean-price guard is data-integrity hygiene, not implementation of points 100–103. Overnight next-session volatility forecasting, instrument-specific out-of-sample transferability and sweep continuation/reversal classification remain open work.
- **Validation boundary:** do not promote options positioning or a volatility regime into a directional signal without a measured baseline and out-of-sample validation. PAPER/DEMO only; no merge, deploy, broker, or orders.
