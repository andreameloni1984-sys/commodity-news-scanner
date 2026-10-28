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


## 2026-10-28 — Fail closed on inconsistent OHLC geometry in the missed-move audit

- **Finding:** `evaluate_missed_moves()` checked the future high/low pair and entry price, but it did not validate that each bar's close (or supplied open) lay inside its own low/high range. An impossible bar could enter the forecast history or distort the measured excursion without making the audit invalid.
- **Change:** add `_valid_ohlc_geometry()`; before forecasting, reject the entire audit with `INVALID_OHLC` if a row is malformed, non-finite, has low above high, or has open/close outside the bar. No sorting or synthetic repair is performed.
- **Files / operational path:** `engine/missed_move_validation.py` (OHLC input → geometry gate → causal forecast → future excursion count); `tests/test_missed_move_validation.py`.
- **Regression:** replace the old partial-skip expectation for a NaN bar with fail-closed coverage and add open/close-outside-range cases. Each must return `INVALID_OHLC` with zero forecasts.
- **Commits:** code `cd7fc94ed40294ae853062a536c4209d573b1622`; regression test `936f448e3a7a46589a38100f26f6abfa68f89f47`.
- **CI:** pending verification on the draft PR; no full-suite PASS is claimed in this log entry.
- **Deployment / limits:** research branch only; no merge or Render deploy. Build-pipeline minutes remain exhausted. No database credentials were read, no Telegram test was sent, and no broker/order path was touched.
- **Empirical validation:** no market replay, walk-forward, out-of-sample scorecard or profitability claim. This protects the integrity of the audit input; it does not improve a forecast by itself.

### Recovered research crosswalk — actual records only

| Lesson / record | File and operational path | Test / CI status | Deployment / empirical status |
|---|---|---|---|
| **2026-09-26 `data_v4.1_patch.txt`**: proposed freshness threshold `max(420s, bar interval + 60s)` | `engine/data.py::_freshness` and `_finalize` metadata; provider candle timestamp → LIVE/STALE decision | The recovered patch artifact contains no associated test or CI result; do not infer coverage from the proposal | Proposal only; no deployment or measured freshness-distribution result established by this artifact |
| **2026-09-27 `engine_data_agriculture_fix.txt`**: explicit Yahoo futures symbols for rice/sugar/cocoa/coffee | Historical proposal for the agriculture branch in `engine/data.py::load_data` → `YAHOO_SYMBOLS` → Yahoo fetch; those instruments are outside the currently selected eight-instrument active universe | No test/CI evidence is attached to the recovered text; live symbol availability was not checked | Mapping proposal, not proof of a current active instrument or successful live quote |
| **2026-10-06 PR #11**: safety/RR staging | `engine/safety.py`, `soyuz_gagarin/adapter.py` → pre-entry safety; `tests/test_gagarin_core.py` | Historical PR is merged; CI was not re-run in this cycle | No current Render commit confirmation or empirical net-return result |
| **2026-10-07 PR #15**: evidence-backed forecast selection | `engine/daily_forecast.py`, `engine/selector.py`, `engine/trigger.py` → forecast → selection → trigger; tests include `tests/test_daily_forecast.py`, `tests/test_selector.py`, `tests/test_trigger_m5_close.py` | Historical PR is merged; CI was not re-run in this cycle | No current Render commit confirmation or out-of-sample edge established |
| **Point-in-time/no-look-ahead news** (IBKR session 9, 2026-10-20) | `telegram/news_monitor.py`: `event_time`, `available_at`, `decision_time`, `baseline_at` → baseline gate → alert; `tests/test_news_monitor.py`; PR #71/#79 | PR #84's six relevant workflows passed on its own head; this does not prove every point-in-time PR is merged or live | No live Render commit or event-price replay confirmed |
| **Wilder RSI, regime/ATR diagnostics** | `engine/regime.py::_rsi_wilder` → regime diagnostics; `tests/test_pipeline.py`; PR #83 | PR #83 records passing RSI/regime workflows on its own head; no new run here | Not confirmed live; no walk-forward/OOS result from this change |
| **HH/HL, LH/LL, breakout/retest** | `engine/structure.py` → swing pivots/structure; `tests/test_pipeline.py`; PR #74 | PR exists; its CI was not reverified in this cycle | Not confirmed live; no false-breakout event study completed |
| **Entry/SL/TP geometry and RR 1.5R/2R/2.5R** | `telegram/news_monitor.py` → price freshness + finite, direction-aware level geometry + Governor; `tests/test_news_monitor.py`; PR #75 | CI for the exact current head was not reverified here | Not confirmed live; no net-of-costs profitability claim |
| **Costs/slippage, outcome scorecards, walk-forward** | `engine/commodity_research.py`, `engine/forecast_ensemble.py`, `research/wti_overnight_validation.py`; `tests/test_commodity_research.py` and `tests/test_forecast_ensemble.py`; PR #59/#61 | Research tests exist; no new end-to-end or OOS run was performed in this cycle | No deployment or verified net performance reported |
| **Futures sessions, expiry/rollover** | `engine/overnight_wti.py`, `research/wti_overnight_evaluation.py`, `research/wti_overnight_validation.py`, `docs/wti-overnight-regime.md`; PR #59 | Research/validation paths exist; CI not reverified in this cycle | No live-session, expiry or rollover validation claimed |
| **Options/positioning** (IBKR session 9) | No directional production feature is introduced; any candidate must be point-in-time and tested against a price-only baseline | No new options test in this cycle | Not deployed; presentation examples are not empirical proof and no directional edge is claimed |

The canonical 100-rule/100-point catalogue was not found in the retrieved Library records. This crosswalk uses the actual September artifacts, merged October PRs, open PRs, and the 2026-10-20 session-9 register; missing rules have not been reconstructed.
