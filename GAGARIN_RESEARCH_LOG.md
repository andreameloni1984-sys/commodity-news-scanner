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

## 2026-10-27 — Fail closed on invalid news baseline prices

- **Finding:** `_capture_baseline()` accepted positive infinity and booleans as prices because it converted with `float()` and only checked `value > 0`. Python treats `True` as 1.0; infinity is positive.
- **Implemented:** route baseline capture through `_finite_positive()`; explicitly reject booleans and retain finite-positive validation for numeric prices.
- **Files:** `telegram/news_monitor.py`; `tests/test_news_monitor.py`.
- **Regression tests:** True/False, NaN, positive/negative infinity, zero, negative, malformed string, and a valid 80.25 baseline.
- **Commit:** code `63f8234a30b6fa09bae2580646e1e534810b5099`; tests `33089074a762b7c8a187ba25b451ee0dbcce8af4`.
- **CI:** PASS on PR head `c02abdb07c1e1b8fefdbf4eee8c097eb4c3589e3`: Gagarin integration run 40461251707, PAPER run 40461251833, NEWS alert run 40461251773, Public Event Brain run 40461251764, and Execution Layer run 40461251955. The research-log-only commit follows those test runs.
- **Deployment:** research branch only; no merge/deploy. Render pipeline minutes are exhausted.
- **Empirical validation:** no live replay or out-of-sample test; baseline input integrity only.
- **Persistence:** live `DATABASE_URL` not verified; journal durability is not claimed.
- **Safety:** PAPER/DEMO ONLY; no broker, orders, secrets or Telegram test messages.


## 2026-10-27 — Revalidate persisted news baselines before creating setups

- **Finding:** capture-time validation rejected booleans and non-finite prices, but `_confirmed_setups()` still coerced the event's persisted `baseline_prices` with `float()`. Corrupted state could therefore bypass the earlier guard: `True` becomes 1.0 and NaN can evade a simple `<= 0` check.
- **Change:** `telegram/news_monitor.py::_confirmed_setups` now applies the shared finite-positive validator at the final decision boundary and skips invalid baselines.
- **Regression:** `tests/test_news_monitor.py::test_confirmed_setups_rejects_corrupt_persisted_baselines` covers booleans, NaN, infinities, zero, negative, and malformed values while retaining the valid-signal path.
- **Operational path:** stored event baseline → news catalyst classification → live Gagarin setup gate → baseline move check → PAPER alert eligibility.
- **Validation limit:** integrity guard only; no profitability or live-delivery claim. Await CI on the final PR head. No merge, Render deploy, Telegram test message, broker, or order. DATABASE_URL and durable journal are not verified.
- **Safety:** PAPER/DEMO ONLY.


## 2026-10-27 — CI and Render verification for persisted news baseline guard

- **Code commit:** `be218a518c61a7ea7c7b4a8ca2471d9bc2cea872`; **final regression-test commit:** `f864b6431a3ef44a677fa2ffda3bae55d6fb4864`; **research-log update before this entry:** `00f60e2c41384086a71307c7cead9613a336a66e`.
- **CI:** all five relevant workflows PASS on the final code/test revision: general tests [40525930346](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40525930346), Public Event Brain [40525930379](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40525930379), NEWS alert [40525930399](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40525930399), Execution Layer [40525930428](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40525930428), and PAPER [40525930437](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40525930437).
- **PR:** #82 remains open/unmerged; no merge or deployment.
- **Render:** last observed live Gagarin Telegram deployment is commit `86068d701c860670a9d9e0e4e65af98860a57cfa` (2026-10-21). Latest build attempt on main commit `99ad72b69cddbed0f80ef9f671c5b70deb9df024` failed at 2026-10-27 12:48 UTC; Render logs explicitly say the workspace exhausted build-pipeline minutes. No deploy was triggered by this PR.
- **Telegram/runtime evidence:** logs at 2026-10-27 13:32 UTC show webhook verified/active and startup welcome delivered; an /aggressivo212 command was logged as delivered. Subsequent news polls (13:38–13:47 UTC) fetched 150–162 items but reported `new_relevant=0`, `pending=0`, `analysis=NO`, `alerts=0`. This verifies the observed runtime path but does not prove alert coverage or predictive performance. DATABASE_URL/durable journal status remains unverified.
- **Empirical limit:** input integrity only; no live replay or out-of-sample profitability test.
- **Safety:** PAPER/DEMO ONLY; no secrets, broker, orders, or Telegram test messages.


## 2026-10-27 — Fail closed on overflowing NEWS scorecard values

- **Finding:** the baseline/setup boundary rejects booleans and overflowing numeric inputs through `_finite_positive()`, but the NEWS scorecard independently converted alert prices, reaction prices, stop and TP1 with `float()`. A very large integer can raise `OverflowError`; booleans can silently become 1.0 in paths that do not reject them first.
- **Change:** `telegram/news_monitor.py::build_alert_scorecard` now routes all four numeric fields through the shared finite-positive validator. Invalid alert prices are excluded; invalid reaction observations are skipped; invalid SL/TP levels leave the outcome unclassified instead of crashing or fabricating a stop/target result.
- **Regression:** `tests/test_news_monitor.py::test_alert_scorecard_rejects_boolean_and_overflowing_prices_and_levels` covers boolean/overflowing alert and reaction prices and overflowing SL/TP levels while retaining a valid directional observation.
- **Operational path:** NEWS_ALERT_SENT / NEWS_REACTION journal rows → scorecard parsing → directional and TP/SL outcome counters.
- **Verification:** code commit `1b4d72bb9304283c9574a94ae0c4b2d707ca556c`; test commit `712c6222d22801441a02bd3823670c89a9e52ff8`; all five relevant workflows passed on final PR head `748343028bc2cdda90e4326b3588ebe2d98fe02f`: general tests [40526403036](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40526403036) (366 passed), NEWS alert [40526402888](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40526402888), Execution Layer [40526402917](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40526402917), PAPER [40526402881](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40526402881), and Public Event Brain [40526402873](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40526402873).
- **Limits:** deterministic input-integrity regression only; no market replay or profitability claim. PR #82 remains draft/unmerged. No Render deployment, Telegram test message, broker, or order. `DATABASE_URL`/durable journal remain unverified.
- **Safety:** PAPER/DEMO ONLY.


## 2026-10-27 — Historical research source audit and mapping

- **Direct Library source:** `Registro Studio IBKR - aggiornato 2026-10-20 sessione 9.md` contains numbered study entries through **36**. Its session 9 records item 32 as an options-data presentation; the presentation itself states that its illustrations are not empirical data or a backtest. Search found no literal “100 punti” or “punto 100” in that file, so it is not the missing 100-rule catalog.
- **Recovered only from historical conversation context:** point 100 “Execution Regime: Volatility × Liquidity”; point 101 “Overnight Risk Engine / Next-Session Volatility Forecast”; point 102 “Setup Transferability / Instrument-Specific Edge”; point 103 “Sweep Validity / Continuation-vs-Reversal”. The original points 1–99 were not recovered in full and are not reconstructed.
- **Mapping/status:** point 100 — Gagarin has regime/ATR diagnostics, but no fully validated volatility × liquidity matrix; point 101 — no verified next-session volatility forecast; point 102 — instrument-transferability needs explicit cross-instrument walk-forward evidence; point 103 — no dedicated sweep/continuation-vs-reversal detector is claimed. Options positioning remains optional context only when reliable data exist and must be tested against the existing baseline, never used as automatic direction proof.
- **Current code increment:** persisted NEWS baseline validation in `telegram/news_monitor.py::_confirmed_setups`, with regression coverage in `tests/test_news_monitor.py`; it is a fail-closed data-integrity guard, not implementation of points 100–103.
- **Validation/deployment:** relevant CI workflows passed on code/test commit `f864b6431a3ef44a677fa2ffda3bae55d6fb4864`; PR #82 is open and unmerged. Render live code is older; latest build failed due exhausted build-pipeline minutes. No out-of-sample profitability test or durable-journal claim.


## 2026-10-27 — Historical notes recovered from prior conversation context (not a reconstructed catalog)

- **Exact names recovered:** `ORDER_FLOW_DATA_INTEGRITY_GATE`; `ORDER_FLOW_PROVIDER_AUDIT`; `SELECTIVE_LLM_ARCHITECTURE`. The recovered architecture note says LLMs are for ambiguous text/context, while deterministic code owns calculations, sizing, stop loss, exposure, and final authorization. The recovered experiment discipline is: preregister → full grid → costs → falsification → out-of-sample (OOS) → promote/reject.
- **Numbered catalog boundary:** no original complete 100-point file is available in the retrieved context. Points 51–99 are not retrievable; only the titles of 100–103 are explicitly recoverable, without their verbatim original explanations. The Library file `Registro Studio IBKR - aggiornato 2026-10-20 sessione 9.md` contains numbered study entries through 36 and explicitly treats its options presentation as illustrative, not a backtest. Do not present paraphrases as the original catalog.

- **Gagarin mapping/status:** `telegram/news_monitor.py::_confirmed_setups` now revalidates persisted baseline prices at the final decision boundary; tests cover bool/NaN/infinity/non-positive/malformed values. This is a data-integrity sub-gate, not a complete `ORDER_FLOW_DATA_INTEGRITY_GATE` or provider audit. No LLM owns arithmetic, sizing, SL, exposure or final authorization in this change. The full preregistered grid/cost/falsification/OOS promotion process is not claimed complete.
- **Architecture records recovered:** `DATA → REGIME → STRUCTURE → SETUP → TRIGGER → EXECUTION → RISK → SAFETY → VALIDATION`; an expanded Gagarin version is `DATA → CONTRACT → LIQUIDITY → VOLATILITY → REGIME → SESSION → STRUCTURE → SETUP → TRIGGER → EXECUTION → RISK GOVERNOR → SAFETY → PAPER TEST`. Treat these as architecture maps, not proof every gate is wired into the deployed decision path.
- **Validation/deployment:** relevant CI passed on the code/test revision (five workflows listed in the preceding verification entry); PR #82 remains open. Render's latest build failed because build-pipeline minutes were exhausted; live commit is older. No out-of-sample profitability claim, durable-journal claim, broker or order.


## 2026-10-27 — Audit of the original 100-point research catalog

- **Recovery attempt:** searched the Library (including `Registro Studio IBKR - aggiornato 2026-10-20 sessione 9.md`) and retrieved prior-conversation summaries dated 2026-10-03.
- **Verified result:** the earlier conversation explicitly recorded that the original numbered 1–100 catalog and complete list of roughly 100 points had not been recovered; only incremental summaries were available. The IBKR session-9 file is a separate study register, with numbered study items through item 32 and later hypotheses; it is not evidence of the missing 100-point catalog.
- **Decision:** do not reconstruct or relabel missing items as original lessons. Apply only directly retrievable, source-backed findings and record inferred hypotheses separately. Items 100–103 appearing in recent implementation notes remain implementation hypotheses, not proof that the original catalog has been recovered.
- **Scope:** this is a provenance/research-integrity finding, not a code feature or empirical trading result.
