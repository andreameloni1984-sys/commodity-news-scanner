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

## 2026-10-27 05:44 UTC — Exclude future observations from news scorecard

- **Finding:** `build_alert_scorecard()` accepted any reaction timestamp inside the four-hour post-alert window, including rows whose `observed_at` was later than the scorecard's `now`/evaluation time. A historical evaluation could therefore use information not yet available at the decision point.
- **Change:** ignore reaction observations later than `now`; alerts with no eligible observation remain pending until the evaluation horizon expires.
- **Files:** `telegram/news_monitor.py`; `tests/test_news_monitor.py`.
- **Operational path:** journal rows → `build_alert_scorecard(rows, now)` → post-alert reaction filtering → outcome/coverage counters.
- **Regression test:** an alert at 04:00 with a reaction timestamp at 04:20, evaluated at 04:10, remains unscored/pending and is not counted as expired.
- **CI:** all five workflows passed on branch commit `c7249afc80abd215f5cd8ef8ae976498ca50d1d5` (code/tests plus initial research-log entry): [main tests](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40451611095), [NEWS alert](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40451611183), [Public Event Brain](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40451611229), [Execution Layer](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40451611150), and [PAPER](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40451611218). Subsequent documentation-only commits were not associated with workflow runs.
- **Deployment:** branch only; no deploy triggered. Render read-only check: last live `gagarin-cloud` commit `86068d701c860670a9d9e0e4e65af98860a57cfa` (2026-10-21); latest attempt `57916b6d792cd7e65776f483d71ad0a50df1ab01` (2026-10-26) failed with `pipeline_minutes_exhausted`. Telegram v2's latest attempted commit also failed for the same quota condition. This PR is not live.
- **Empirical validation:** no historical replay or out-of-sample performance test performed. This fixes temporal eligibility, not predictive accuracy.
- **Safety:** scorecard-only change; no entry authorization or order execution changed. PAPER/DEMO ONLY.

## 2026-10-27 — Fail closed on ambiguous scorecard timestamps

- **Finding:** the shared `_parse_datetime()` assumed UTC for naive values. That is unsafe for historical scorecards: both alert time and observed reaction time must represent unambiguous instants, and the evaluation clock (`now`) must also be timezone-aware.
- **Change:** add an opt-in `require_timezone` parser mode and use it for scorecard `sent_at` and `observed_at`. A naive/invalid decision clock returns an explicitly invalid, empty scorecard (`decision_time_valid=False`) rather than scoring with an invented UTC interpretation. Existing non-scorecard callers retain their prior parsing behavior.
- **Files/path:** `telegram/news_monitor.py::_parse_datetime`; journal rows → `build_alert_scorecard(rows, now)` → strict timestamp eligibility → outcomes.
- **Regression:** `tests/test_news_monitor.py::test_scorecard_rejects_naive_timestamps_and_decision_clock` verifies naive alert/observation timestamps are excluded, valid alert remains pending, and naive `now` is rejected.
- **Commits:** code `56c8ef2b41b6bf4d8dad677e1d878cd749740a3d`; test `44f162c19827054714c93ce37bfd7f89c17fa88f`.
- **CI:** pending after these commits; no new result claimed yet.
- **Deployment:** PR #79 branch only; no merge/deploy. Render build-pipeline minutes remain exhausted.
- **Empirical limits:** no historical replay, cost/slippage model, or out-of-sample profitability evaluation. This is temporal data-integrity work only.
- **Safety:** PAPER/DEMO ONLY; no broker, orders, secret-value inspection, or Telegram test messages.

## 2026-10-27 — Research provenance: session 9 and early-October records

- **Library source:** `Registro Studio IBKR - aggiornato 2026-10-20 sessione 9.md`, lines 473–483 and 520–525. The options presentation was consulted as slides only, not watched as a video; its visuals are illustrative and explicitly not a backtest. Options/positioning may be tested only as one feature against a baseline, when reliable data exist; preserve `event_time`, `available_at`, `decision_time`, and require `available_at <= decision_time`.
- **Recovered early-October context (2026-10-03/06):** Sputnik's actual recorded research emphasized evidence quality, transaction/document normalization, deduplication, recency, disclosure lag, concentration and event correlation. The historical 0–100 score was a ranking concept, not 100 separate lessons.
- **Catalog status:** no authentic numbered 100-rule list was found in the searched Library or prior-conversation retrieval. Do not repeat unverified component weights as if they were present in the source document.
- **Current code path:** `telegram/news_monitor.py::_parse_datetime(require_timezone=True)` → `build_alert_scorecard()` now rejects naive alert/observation times and invalid naive decision clocks. CI on the code/test commit passed all five workflows; no empirical profitability claim.
- **Safety/deployment:** PR #79 only, not live; Render build quota remains exhausted; PAPER/DEMO ONLY.

## 2026-10-27 — Reject boolean values in scorecard prices and risk levels

- **Finding:** Python converts `True` to `1.0`. The scorecard accepted boolean alert/reaction prices and boolean stop/TP1 levels, potentially turning a type error into a false price move or risk outcome.
- **Change:** explicitly reject boolean alert prices, observed prices and stop/TP1 values in `build_alert_scorecard`; preserve the existing finite/positive checks and point-in-time observation cutoff.
- **Files/path:** `telegram/news_monitor.py::build_alert_scorecard`; `tests/test_news_monitor.py`.
- **Regression:** covers boolean alert price, boolean reaction price and boolean TP1; valid numeric observation remains scorable, invalid reaction remains pending, and boolean TP1 cannot trigger SL/TP outcome classification.
- **Commits:** code `7ecd582c8383473ea6acdf583d6163d0304d6566`; test `bf44f0a4a8adb4b151a7d7844453553c6a6f521e`.
- **CI:** PASS on code/test commit `bf44f0a4a8adb4b151a7d7844453553c6a6f521e`: NEWS alert `40468967173`; Execution Layer `40468967152`; general tests `40468967131`; PAPER `40468967155`; Public Event Brain `40468967142`. The following commit updates this log only.
- **Deployment/empirical limits:** branch/PR #79 only; no merge/deploy, live replay or out-of-sample profitability test. Render build capacity remains constrained.
- **Safety:** PAPER/DEMO ONLY; no broker/orders or Telegram test messages.

## 2026-10-27 09:33 UTC — Exclude future-dated alerts from point-in-time scorecards

- **Finding:** the scorecard rejected future price observations but still admitted an alert row with `sent_at > now` into its denominator and marked it pending. A historical evaluation could therefore count an alert that had not yet been sent at the decision time.
- **Change:** `telegram/news_monitor.py::build_alert_scorecard()` now requires `cutoff <= sent_at <= now` before admitting an alert. Future alerts are excluded from alert, pending, coverage and outcome counts.
- **Files:** `telegram/news_monitor.py`; `tests/test_news_monitor.py`.
- **Regression:** `test_scorecard_excludes_alerts_sent_after_decision_time` uses an alert five minutes after the evaluation clock and verifies zero eligible alerts/outcomes.
- **Commits:** code `49b2a76aa3d6f82f191e15ca2a2bd1c2fb2736d4`; tests `fbf5cc4fe18c7c6a418d6c7d07156dfc62644a28`.
- **CI:** all five workflows PASS on the code/test head: [general tests](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40474540731), [NEWS alert](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40474540785), [Public Event Brain](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40474540826), [Execution Layer](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40474540782), [PAPER](https://github.com/andreameloni1984-sys/commodity-news-scanner/actions/runs/40474540755).
- **Deployment:** PR #79 only, not merged. Render workspace was not selected in this run; no deploy was triggered and live commit was not re-verified. `DATABASE_URL` was not inspected; journal durability is not asserted.
- **Empirical limit:** temporal eligibility fix only; no replay, cost/slippage model or out-of-sample profitability validation.
- **Safety:** PAPER/DEMO ONLY; no broker, orders, secrets or Telegram test messages.
