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


### CI follow-up for the 2026-10-31 SILV reference change

- First PR run `41249703393` found one test-only assertion error: the test assumed provider component order, while the implementation preserves the source response order. The other 450 tests passed. No production-code failure was reported.
- Corrected the assertion to compare the component-provider set in commit `d6f916a6567ecc047cb346bd752d4ef94f9d003d`.
- Final PR-head integration run `41249739091`: **451 passed in 1.64s**.
- Additional PR-head workflows: NEWS alert `41249739042` SUCCESS; Execution Layer `41249739083` SUCCESS; Public Event Brain `41249739135` SUCCESS; PAPER `41249739204` SUCCESS.
- CI is green on the current PR head. The PR remains open and unmerged; no deployment or live Telegram delivery was performed.


## 2026-11-01 — Measure Narwhal reference age at response receipt (rebased branch)

- **Finding:** the Narwhal adapter previously captured the age clock before HTTP I/O, understating quote age by request latency.
- **Change:** preserve the provider's original `source_timestamp`, record UTC `observed_at` after a valid JSON response arrives, and calculate `age_seconds` from that receipt time. Narwhal remains reference-only; Yahoo remains the execution-price basis.
- **Regression:** a mocked seven-second HTTP request verifies a source timestamp 60 seconds old is recorded as 67 seconds old at receipt.
- **Files:** `engine/data.py`, `tests/test_narwhal_futures_reference.py`.
- **Branch:** `fix/gagarin-narwhal-observed-at-receipt-main-20261101`, created from current `main` commit `2ae68eb2ddbb800c3f68f60b91c02d64977174f3` to avoid the stale-base conflict on PR #108.
- **Limits:** mocked HTTP only; no live Narwhal credential or quote was inspected. Contract month and upstream-source independence remain undisclosed, so no futures deviation is calculated. PAPER/DEMO only; no paid provider or real order.

## 2026-11-01 — Publish Gagarin catalyst bias before technical confirmation

- Finding: `telegram/news_monitor.py` only sent a news alert after a live matching quote, an aligned `setup_direction`, `trigger_confirmed`, a PAPER decision, valid entry/SL/TP, and a minimum post-detection price reaction. When quote/ATR or the trigger was missing, the event stayed pending without a Telegram direction; when the technical side opposed the catalyst, the catalyst hypothesis disappeared from the user-facing flow.
- Implemented on branch `feat/gagarin-news-early-bias-states-20261101-0652`: send one deduplicated early catalyst message for every fresh mapped event. Supported bullish/bearish impacts remain LONG/SHORT hypotheses; mixed or unsupported evidence is explicitly NEUTRAL/NO_DIRECTION with matched-term reasoning. Each instrument reports EARLY_BIAS when validated live price/ATR is missing, EARLY_SETUP when both exist but the trigger/risk chain is not confirmed, and D-L-A as ALIGNS, CONTRASTS, or NOT_CONFIRMED. A later fully validated aligned setup may still produce a separate confirmed alert.
- Safety: early messages always say TRADE PAPER: NOT_EXECUTED and omit entry/SL/TP. Confirmed alerts also say no order was sent. Confirmed setup eligibility now additionally requires `data_ok` and finite positive ATR; baseline and current prices use finite-positive validation. Stale/future/unverifiable publication timestamps are suppressed before any bias message.
- Evidence limitation: D-L-A remains an OHLCV/structure proxy; no DOM/footprint feed is claimed. This change does not create prices, ATR, sizing, or orders.
- Regression coverage: preserve LONG when technical state is SHORT and quote/ATR are missing; emit NEUTRAL/NO_DIRECTION for mixed tariff headlines; require validated data and ATR for confirmed setup; ensure one early bias is delivered once and a later confirmed alert is distinct. Existing alert scorecard behavior remains separate: only `NEWS_ALERT_SENT` enters directional outcome scoring.
- Verification: GitHub Actions on the PR head is required before merge. No live Telegram message, provider quote, deploy, or trade order was sent by this code change.
- Open: verify deployed NEWS monitor uses the new format; verify Render/Actions persistence and Telegram delivery; build a real historical sample toward 100 setups; add independent same-contract futures references.

### Final verification — PR #112 merged

- PR #112 was merged by squash into main as `6e3f7e83536e87990fff967231ca5373c1d75821`.
- Final PR head: `a9f4d5d7a5ce6dfb98f0449d25a19a0b87aae726`.
- The first PR CI attempt exposed one fixture omission (`data_ok` and `atr` missing in the EARLY_SETUP test state). The fixture was corrected; no production-code change was needed for that failure.
- Final PR-head GitHub Actions: NEWS alert tests SUCCESS (68 passed); Public Event Brain SUCCESS (82 passed); GAGARIN integration SUCCESS (455 passed); Execution Layer SUCCESS (3 passed); PAPER smoke SUCCESS.
- Post-merge Actions for the squash commit were not yet returned by the commit-run lookup. Render deploy and live Telegram delivery were not verified in this run.
- Remaining: the canonical safety engine still writes `final_decision=WAIT` for blocked execution states; this PR changes the NEWS-to-Telegram hypothesis flow only. Narwhal free quota/rotation metadata and FinzData free-key activation remain open.


## 2026-11-01 — Replace default WAIT with explicit BIAS / SETUP / PAPER status

- Finding: the canonical safety engine still initialized final_decision to WAIT and rewrote every blocked state to WAIT. This obscured whether the market had a directional hypothesis and conflated a blocked PAPER authorization with a market-neutral view.
- Change: default and safety-blocked canonical decisions now use BLOCKED; the safety veto remains intact and still prevents an unauthorized PAPER entry. Added engine/decision_status.py to expose the directional state separately: BIAS (setup/pre-move/opportunity direction), SETUP (EARLY_BIAS, EARLY_SETUP, CONFIRMED, or NEUTRAL), and TRADE PAPER (BLOCKED_NOT_EXECUTED, NOT_EXECUTED, or ENTRY_AUTHORIZED_PAPER_ONLY).
- Telegram: /classifica, /setup, /intraday, and single-instrument /analisi now render the three states separately and show up to three blocking reasons. Missing/stale quote or ATR leaves a supported direction visible as EARLY_BIAS; fresh price/ATR without full safety approval is EARLY_SETUP; no supported direction is NEUTRAL / NO_DIRECTION.
- Tests added: six deterministic tests cover missing quote, fresh quote without trigger/safety approval, safe PAPER authorization, neutral direction, legacy WAIT normalization, and preservation of LONG while safety remains BLOCKED. No price, ATR, entry, SL, TP, size, or order is created by the display helper.
- Limits: this is state-labeling and Telegram-formatting only. News-specific catalyst BIAS continues to be generated by the NEWS monitor; the canonical engine fallback direction is explicitly sourced from setup/pre-move/opportunity fields. CI and deployment are pending. No live Telegram delivery or Render deployment is claimed. PAPER ONLY.

- CI correction: the first PAPER safety run exposed one legacy assertion in tests/test_canonical_governor_pipeline.py that still expected WAIT for a stop-distance blocker. Updated that expectation to BLOCKED; production safety criteria were unchanged. The failing run had 25 passed and 1 failed before this test-only correction; rerun is pending.

- Integration CI follow-up: the first full GAGARIN integration run found seven legacy assertions expecting WAIT/IN ATTESA after the status contract changed (8 failed, 453 passed, including one earlier governor test already corrected). Updated pipeline, opportunity-priority, and Telegram formatter tests to expect BLOCKED and the explicit BIAS/SETUP/TRADE PAPER labels. No further runtime logic was changed in this correction; fresh CI is pending.


## 2026-11-01 — Multi-source execution audit; no unverified provider added

- **Inspected main:** `71884cf38abf16e1dbc96e928750edd5ddaee175`.
- **Current commodity execution route:** Yahoo Finance continuous futures is still the sole active execution provider for XAU, XAG, copper, WTI, Brent, wheat, corn and soybeans. BiQuote commodity CFD/MT5 prices are deliberately excluded as futures fallbacks; Twelve Data commodity helpers remain isolated from the active route. FX uses BiQuote then Yahoo spot.
- **Reference feeds:** SILV DATA is spot-only for gold/silver and cannot replace futures execution. Narwhal remains optional/free-plan reference-only; this run did not verify a live credential/response, exact contract month or upstream source independence, so it was not promoted to execution or treated as a confirmed independent same-contract futures check.
- **Candidate review:** Gold API documents free, no-key spot prices for precious metals, but direct endpoint response and provider-source independence were not verified from the bot runtime in this run. It was not integrated or counted as a validated third source. No paid service or paid key was used.
- **GitHub Actions on inspected main:** GAGARIN integration run `41281237547`, execution safety `41281237569`, NEWS alerts `41281237535`, Telegram menu `41281237540`, PAPER safety/smoke `41281237572`, and paper monitor `41281581613` all completed with SUCCESS. This confirms CI/workflow completion, not market-data quality or user-facing Telegram delivery.
- **Code changes this run:** none in Gagarin. The single code improvement for this run was made in SPUTNIK; this entry records the Gagarin provider audit and why no unsafe/unverified feed was added.
- **Open:** obtain a verifiable free source with comparable futures contract/expiry and documented provenance; verify Narwhal free-plan activation/rotation and independence; close residual WAIT labels in convergence conflict/no-catalyst paths in favour of explicit CONFLICT/NEUTRAL; continue real historical setup diary toward 100 out-of-sample cases. PAPER ONLY; no real orders.

## 2026-11-01 — Remove residual WAIT from the legacy Telegram signal formatter

- **Finding:** the canonical /classifica, /setup, /intraday and single-instrument status helper had already separated BIAS / SETUP / TRADE PAPER, but the older telegram/signals.py channel still rendered a literal WAIT when there was no authorized PAPER entry. Its top board also defaulted missing decisions to WAIT, and the risk guide taught WAIT as a user-facing state.
- **Change:** telegram/signals.py now uses engine.decision_status.market_decision_status() as the single source for BIAS, SETUP and TRADE PAPER. When there is no PAPER entry, the board preserves supported LONG/SHORT hypotheses with EARLY_BIAS or EARLY_SETUP and explicit blockers; unsupported direction is NEUTRAL / NO_DIRECTION. Confirmed signals, watch cards, top ranking and guides display the three states separately. The old format_wait() name remains only as a compatibility alias and now renders BLOCKED / NOT EXECUTED.
- **Files:** telegram/signals.py; test_signal_channel.py.
- **Code commit:** e90b9d3a30be6d865ee4206aaef79ed7b12b9c9f.
- **Regression tests:** added coverage for LONG preserved without PAPER authorization, neutral direction, legacy formatter compatibility, separate BIAS/SETUP/TRADE PAPER labels, and absence of WAIT in rendered messages/guides.
- **GitHub Actions:** GAGARIN integration 41297831312 SUCCESS — 463 passed in 2.11s; Execution Layer 41297831232 SUCCESS; NEWS alert 41297831281 SUCCESS; PAPER safety and smoke 41297831265 SUCCESS.
- **Safety/verification limits:** no order, live quote, Telegram delivery, or Render deploy was performed or claimed. PAPER ONLY.
- **Open:** convergence_engine.py still returns a WAIT decision for missing Sputnik thesis and opposite-direction conflict; cloud_api.py, main.py, and telegram/render_runner.py retain WAIT fallbacks when no decision object exists. Internal WAIT_LIVE/legacy test fixtures are separate from the user-facing Telegram status contract and should be reviewed without weakening safety. Sputnik still has a fallback action=WAIT in trump_tracker.py when the Gagarin action field is absent. Continue free same-contract futures-source verification and the real historical journal toward 100 valid setups; no third comparable execution source or 100-case out-of-sample result is verified yet.


## 2026-11-01 — Preserve catalyst direction through Sputnik/Gagarin convergence conflicts

- **Finding:** `convergence_engine.py` still returned a user-facing `WAIT` when Sputnik had no directional thesis or when Gagarin pointed in the opposite direction. It also reduced same-direction cases to `WATCH`, without distinguishing whether fresh price and ATR were available.
- **Implemented:** missing/unsupported Sputnik direction now returns `NEUTRAL / NO_DIRECTION`; a supported LONG/SHORT thesis remains visible when Gagarin has not analyzed the instrument, is neutral, or indicates the opposite direction. Opposite direction is reported as `D-L-A: CONTRASTS` and never becomes a PAPER entry. Same-direction states are graded `EARLY_BIAS` when live/data_ok/finite-positive price and ATR are not all present, `EARLY_SETUP` when those inputs are present but no PAPER entry is authorized, and `CONFIRMED` only when Gagarin's existing PAPER-entry checks pass. The formatter now prints BIAS, SETUP, D-L-A and TRADE PAPER separately.
- **Files:** `convergence_engine.py`; `tests/test_convergence_engine.py`.
- **Code commit:** `9ed35b784e1c43bcacba4e9fc75007d4bb5e2916`. **Test expectation correction:** `e971c1a9623bc6ef4dfaf4bce9e75d609ea53952`.
- **Tests:** first CI run on the code commit exposed one stale test expectation (it expected the old `PAPER_CANDIDATE` decision label). The suite otherwise reported 464 passed; the corrected contract is `decision=CONFIRMED` plus `trade_paper=PAPER_CANDIDATE`. Final integration run `41300103871`: **465 passed in 2.02s**. Execution Layer `41300103883`, PAPER safety/smoke `41300103846`, and NEWS alert `41300103831` all SUCCESS.
- **Safety/limits:** no price, entry, SL or TP is added by this convergence layer; no order or Telegram test message is sent. PAPER ONLY. The `EARLY_SETUP` classification relies on Gagarin's existing `live` and `data_ok` flags plus finite-positive price and ATR; it is not a new independent feed-freshness check.
- **Open:** `cloud_api.py`, `main.py` and `telegram/render_runner.py` still have fallback `WAIT` defaults when a decision object is absent; SPUTNIK's `trump_tracker.py:gagarin_confirmation_message()` still has an action fallback `WAIT`. The free multi-source audit still lacks a verified third independent same-contract futures execution/control feed; Narwhal's upstream independence/contract mapping remains unverified. No live Telegram delivery, production monitor, or Render deploy was verified. The historical real-setup journal has not yet reached 100 valid out-of-sample cases.

## 2026-11-01 — Remove missing-decision WAIT fallbacks from CLI and Render monitor

- **Finding:** the current main runner and scheduled Render feedback monitor still wrote the literal `WAIT` when `evaluate_states()` returned no decision object. This hid the distinction between a supported market bias, a missing governor result, and an actual PAPER safety block.
- **Implemented:** added `attach_runtime_decision_metadata()` to `engine/cloud_api_status.py` and wired both `main.py` and `telegram/render_runner.py` to it. Missing decisions now become `NO_DECISION` while retaining any LONG/SHORT BIAS, setup maturity, blockers and `TRADE PAPER: NOT_EXECUTED`. A legacy WAIT action is normalized to `BLOCKED` / `BLOCKED_NOT_EXECUTED`; it is not treated as NEUTRAL and cannot authorize an entry. The shared freshness adapter downgrades stale/malformed PAPER_ENTRY metadata to PAPER_WATCH before it reaches the forecast journal.
- **Files:** `engine/cloud_api_status.py`, `main.py`, `telegram/render_runner.py`, `tests/test_cloud_api_decision_status.py`.
- **Implementation commits:** `0e1746a4881e4f0e091df46c3381938dd2e05292` (shared helper), `fca8fdec89ef621c530b2e2aa9827ecba7e68de6` (main runner), `dc24e4ae5922a7a3de502453ef107ec2d2e9074b` (Render monitor), `7c0c12e05312fe580c1de8169c3d5975bc28f970` (regressions).
- **Tests added:** missing decision preserves SHORT as EARLY_BIAS; legacy WAIT becomes a safety block while preserving LONG; both runtime paths are wired to the shared adapter and no longer use an `else "WAIT"` fallback. GitHub Actions verified on PR head b264a4216169b94dcdaa59ae105a95c8588e27f3: full GAGARIN suite 473 passed (run 41314830807); PAPER safety/smoke 26 passed (41314830853); commodity trade-plan 34 passed (41314830784); Public Event Brain 82 passed (41314830826); Execution Layer 3 passed (41314830832); NEWS alert 68 passed (41314830760). All six workflows SUCCESS.
- **Safety/limits:** metadata-only change; no prices, entry, SL or TP are generated; no broker order, live quote, Telegram test message or Render deploy was performed. PAPER ONLY.
- **SPUTNIK cross-check:** PR #82 remains OPEN and mergeable, not merged into main; its handoff fallback correction is already covered by the branch's reported 169 ranking and 39 item-intelligence tests. Main still needs that PR integrated before the SPUTNIK handoff fix is active.
- **Merge:** PR #116 merged into main by squash as `b7e570abbaec7519497d1273b9e6897d6431f40f` after all six GitHub Actions workflows passed. Main read-back confirms both missing-decision WAIT fallbacks are gone from `main.py` and `telegram/render_runner.py`.
- **Open:** SPUTNIK PR #82 integration; remaining free same-contract futures source and Narwhal key/independence verification; real 100-setup out-of-sample journal; complete Telegram delivery and monitor runtime verification.

## 2026-11-01 — Post-merge monitor and provider-activation audit

- **Runtime monitor:** latest visible scheduled Gagarin Paper Monitor run `41312993151` at 2026-11-01 13:47:53Z completed SUCCESS. Its application log says `Run pianificato completato senza analisi; non è un errore del motore.` No outgoing Telegram send or message_id was recorded in that run, so delivery is NOT confirmed. The workflow is configured for every 15 minutes; at audit time no newer scheduled monitor run was visible (approximately a 20-minute gap). The run occurred on Sunday; the no-analysis path is consistent with a closed market, but the schedule gap still needs monitoring.
- **Narwhal activation:** the same monitor log shows `NARWHAL_REFERENCE_ENABLED=1` but an empty `NARWHAL_API_KEY`. The free-tier adapter therefore cannot authenticate and must be treated as NOT_CONFIGURED; do not count Narwhal as a live reference source until a free key is present and an actual response is verified.
- **Current price-basis status:** Yahoo remains the futures execution basis; SILV DATA is spot-only for gold/silver; Narwhal is optional, delayed, and currently unconfigured in the monitor runtime. No third independently verified same-contract futures source is established. No spot/futures averaging or replacement of execution levels is allowed.
- **Post-merge CI:** PR #116 was squash-merged as `b7e570abbaec7519497d1273b9e6897d6431f40f`. All six PR-head Actions passed: full suite 473 (run 41314830807), PAPER 26 (41314830853), trade-plan 34 (41314830784), Public Event Brain 82 (41314830826), Execution Layer 3 (41314830832), NEWS alert 68 (41314830760). Push workflows on the merge commit and the subsequent log commit also completed SUCCESS.
- **Safety:** the merged runtime status change is metadata-only. The monitor run cited above predates the merge; post-merge scheduled runtime behavior and Telegram delivery are not yet confirmed. No Render deployment, live quote, Telegram test send, broker order or real trade is claimed.
- **SPUTNIK cross-check:** last visible scheduled tracker run `41287080980` at 09:01:18Z succeeded but confirmed only message IDs 623/624/625 and logged four unconfirmed sends; source OSError/SEC 403 issues remain. Its PR #82 is still open.
- **Open:** configure/verify the free Narwhal key; obtain a third comparable futures source; observe post-merge Gagarin monitor output and Telegram API acknowledgements; investigate monitor schedule gaps; integrate SPUTNIK PR #82; complete the real 100-setup out-of-sample journal and metrics. PAPER ONLY.



## 2026-11-01 — Cross-bot handoff verification after SPUTNIK PR #82 merge

- **GAGARIN main inspected:** latest functional change remains `b7e570abbaec7519497d1273b9e6897d6431f40f`; no GAGARIN functional file was changed in this execution.
- **Runtime state audit:** `main.py`, `telegram/render_runner.py`, `convergence_engine.py`, and `telegram/signals.py` contain no user-facing WAIT fallback. `engine/cloud_api_status.py` still recognizes legacy WAIT only as an input to normalize it into a blocked/non-executed state; it is not a default market direction. `cloud_api.py` retains a CSS class named `.wait` for neutral card styling, while its displayed default alert is `NONE`, not WAIT.
- **SPUTNIK handoff:** PR #82 is now merged in SPUTNIK as `cfb0cea6180b1cf90b8fd974aa68908b7c2fee19`. The handoff preserves LONG/SHORT BIAS and explicit D-L-A setup provenance; a legacy `PAPER_SIGNAL` alone no longer implies CONFIRMED.
- **GAGARIN tests/CI this execution:** no GAGARIN code change and no new GAGARIN test run were made. Last verified GAGARIN CI remains the prior PR #116 evidence: full suite 473; PAPER safety/smoke 26; trade-plan 34; Public Event Brain 82; Execution Layer 3; NEWS alert 68 — all SUCCESS (runs recorded above). Current commit status query returned no individual status records.
- **Open:** Narwhal is still not a verified runtime reference while the free API key is empty/unverified; no third independent same-contract futures source; complete Telegram API acknowledgement and monitor continuity; real 100-setup out-of-sample journal and metrics. No live quote, deployment or order is claimed. PAPER ONLY.


## 2026-11-01 — Exclude non-redistributable public futures quote pages from multi-source intake

- **CME delayed quotes:** the public page confirms a minimum 10-minute delay and exposes contract month/venue, but CME Data Terms permit access only in the presented form for personal non-commercial use, prohibit automated extraction/scraping/systematic retrieval and prohibit use in software/AI development without prior written consent. The separate delayed-snapshot REST API requires OAuth, API entitlement and an active Public Website (Delayed) Redistribution license. It is therefore **not eligible** as a free automated provider for GAGARIN/SPUTNIK.
- **CBOE delayed quotes:** the public CME quote dashboard explicitly prohibits downloading delayed quote table data through auto-extraction programs/queries/software. Excluded from automated ingestion.
- **Decision:** no code/provider was added. Do not scrape either website or treat a public browser table as an API. Continue searching for a provider whose free endpoint, redistribution/use terms, exact contract mapping and timestamp semantics are all verifiable.
- **Sources:** CME delayed quote page and delay explanation; CME Data Terms of Use (updated 2023); CME delayed-snapshot API onboarding; CBOE delayed quote page. Reviewed 2026-11-01.
- **Tests:** no code changed; no provider tests run. This is a terms/eligibility audit only.
- **Open:** Narwhal free-key authentication and source independence remain unverified; no third independent same-contract futures source is established. PAPER ONLY.


## 2026-11-01 — Audit residual PAPER-state presentation and quote provenance

- **Finding 1 — Aggressive dashboard:** `static/aggressive.html` treats both `PAPER_ENTRY` and `PAPER_SIGNAL` as `ok`, then labels either as `PAPER AUTORIZZATO`. GAGARIN's canonical API contract distinguishes `ENTRY_AUTHORIZED_PAPER_ONLY` from `SIGNAL_ONLY_NOT_EXECUTED`; the dashboard currently collapses these states. It also falls back from missing `entry` to `price` in a field labelled “Prezzo / Entry indicativa”, without rendering the quote's original timestamp/age. This is a user-facing presentation defect; no change made in this execution because the single functional change was the SPUTNIK handoff fix.
- **Finding 2 — API quote provenance:** `cloud_api.py:_state_json()` returns `price`, `data_source`, `data_status` and `live`, but does not expose a complete per-price record with original provider timestamp, currency, unit, bid/ask and computed age. The multi-source metadata may exist upstream, but the public JSON projection does not yet meet the requested provenance contract.
- **Finding 3 — legacy reasoning default:** `engine/analyst_reasoning.py` still uses `meta.get("gagarin_action", "WAIT")` as an internal fallback. The current verdict branch can still produce WATCH_LONG/WATCH_SHORT/NO_DIRECTION, so this is not the same as a user-facing WAIT board, but the default should eventually become `NO_DECISION` for consistency.
- **No GAGARIN code/test change in this execution:** the current main runtime paths `main.py`, `telegram/render_runner.py`, `convergence_engine.py` and `telegram/signals.py` have no user-facing WAIT fallback. Legacy WAIT is still recognized only by canonical safety/status normalizers.
- **Next functional priority:** correct the aggressive dashboard so `PAPER_SIGNAL` is never presented as an authorized entry, show BIAS / SETUP / TRADE PAPER explicitly, and never use `price` as an entry fallback. In parallel, expose full timestamped quote provenance in the API.
- **Open:** third independent same-contract futures source; free Narwhal key and actual endpoint response; per-price provenance projection; monitor/Telegram acknowledgement; real 100-setup out-of-sample journal. PAPER ONLY.

## 2026-11-01 — Separate aggressive-dashboard PAPER authorization from candidate signals

- **Finding:** `static/aggressive.html` treated both `PAPER_ENTRY` and `PAPER_SIGNAL` as authorized and displayed the generic `price` field as an entry when `entry` was absent. It also displayed SL/TP when the canonical setup state was only `EARLY_BIAS`.
- **Implemented:** the dashboard now labels an entry as PAPER-authorized only when all three canonical fields agree: `action=PAPER_ENTRY`, `trade_paper=ENTRY_AUTHORIZED_PAPER_ONLY`, and `setup=CONFIRMED`. `PAPER_SIGNAL` is rendered as `SIGNAL ONLY · NON ESEGUITO`; blocked/watch states remain visibly non-executed. Market price and entry are separate fields; market price is never used as an entry fallback.
- **Freshness presentation:** price, entry, SL and TP are hidden unless the API setup is `EARLY_SETUP` or `CONFIRMED`, states produced by the canonical adapter only when live/data_ok/fresh_live, finite positive price/ATR, and a fresh analysis timestamp pass. Otherwise the dashboard keeps BIAS/SETUP visible and explicitly says entry/SL/TP are omitted because fresh inputs are unavailable or the setup is neutral.
- **Files:** `static/aggressive.html`; new `tests/test_aggressive_dashboard_contract.py`.
- **Commits:** dashboard state fix `5ac615a36601fa36bb3aca7da5c56f67d3cab5b3`; freshness gating `baa8b29b51102e5bb27eb3aef073d25a30268a02`; runtime note rendering `bfdb9eeb152d1297cca902d7a702d5ca2db2e3a2`; script syntax correction `9e4fd6b4bb0ff5c31678e0705ab043dab7cd9856`; final test cleanup `da8f4e656485dcd02eda2df89ec0ff78c1d89757`; initial tests `652637a0fdcfe20ad269da894decd116806d1b31`; freshness assertions `eefbd3989cad7610a29eeee09de7350c747929c0`.
- **Tests:** three source-contract regressions cover explicit authorization, PAPER_SIGNAL separation, no price-to-entry fallback, fresh-setup gating, and separate BIAS/SETUP/TRADE PAPER display. The extracted dashboard JavaScript passed a syntax compile and five behavioral checks against the fetched PR-head file (PAPER_SIGNAL, fully authorized PAPER_ENTRY, missing authorization metadata, EARLY_SETUP without authorization, and blocked/watch). GitHub Actions on this code/test head completed successfully: GAGARIN integration run `41328117219` — **476 passed in 1.71s**; PAPER run `41328117238`, NEWS Alert run `41328117225`, Public Event Brain run `41328117268`, and Execution Layer run `41328117234` all SUCCESS. The three Python source-contract regressions were included in the integration suite. The subsequent research-log update is documentation-only; no Render deploy, live quote, Telegram delivery or broker order was performed. The first assertion revision was corrected before CI after the implementation changed to gate both market price and levels on fresh setup status. No live quote, Telegram delivery, Render deploy, or broker order was used.
- **Open:** Cloud API still lacks the complete per-price provenance projection (original timestamp, currency, unit, bid/ask and age); Narwhal free credential/contract comparability and a third independent same-contract futures source remain unverified. PAPER ONLY.


## 2026-11-01 — Expose per-price quote provenance in the Gagarin Cloud API

- **Finding:** the data engine already records the execution quote's provider, resolved symbol, source candle timestamp, currency, unit, market type, bid/ask availability, age, freshness status and price. It also stores isolated Narwhal/SILV reference records. However, `cloud_api.py:_state_json()` returned only `price`, `data_source`, `data_status` and `live`, so API consumers could not audit the actual quote basis or reference-source status.
- **Implemented:** added a `quote_provenance` projection with separate `execution_quote`, `execution_basis` and `reference_quotes`. It preserves source timestamps and age from metadata, keeps spot references separate from futures execution, and exposes comparison/basis fields only when the data engine supplied them. Reference records use an explicit allowlist; credentials or arbitrary metadata are not serialized.
- **Data integrity:** missing provenance remains null/UNKNOWN; analysis timestamps are never substituted for source timestamps; NaN, Infinity, booleans and invalid non-positive prices/bid/ask are not serialized as numeric quote values. Bid/ask availability is true only when both finite positive values exist and the source metadata does not explicitly disable it. No quote is fabricated and no price basis is changed.
- **Files:** `cloud_api.py`; `tests/test_cloud_api_quote_provenance.py`; this log.
- **Regression coverage:** complete Yahoo execution provenance with separate Narwhal delayed-futures and SILV spot references; missing metadata stays null rather than borrowing the analysis timestamp; non-finite values are nulled and cannot falsely enable bid/ask.
- **Verification:** PR CI pending at time of log update. No live quote, authenticated Narwhal response, Telegram delivery, Render deployment, broker connection or order is claimed. PAPER ONLY.
- **Open:** verify the new API contract against a live but read-only runtime response when available; configure and verify the free Narwhal key; find a third independently sourced same-contract futures feed; complete the real 100-setup out-of-sample journal and monitor/Telegram delivery audit.


### Verification — Cloud API quote provenance projection

- **PR:** #118 merged into `main`; merge commit `9ca873e3c639dab656ed2280964a6e78de1c3d8c`.
- **Main readback:** `cloud_api.py` contains `_quote_provenance_json()` and `_state_json()` exposes `quote_provenance`; `tests/test_cloud_api_quote_provenance.py` is present with three regression tests.
- **GitHub Actions on PR head `07b3b255895e3aba02cf76ce1de2f8e7f60d3169`:** Integration run `41330903449` — **479 passed in 2.14s**; Execution Layer `41330903430`, NEWS Alert `41330903433`, Public Event Brain `41330903525`, and PAPER `41330903542` all SUCCESS.
- **Coverage:** execution quote provenance is serialized independently from reference quotes; Narwhal's delayed continuous futures record remains reference-only and incomparable without a contract month; SILV spot basis remains separate; missing timestamps are not reconstructed from analysis time; non-finite values and incomplete bid/ask are not treated as valid.
- **Post-merge:** code, tests and log entry were read back from `main`. The recorded CI runs are PR-head checks before merge; no separate post-merge CI status was returned by the connector.
- **Limits:** no live API request, authenticated Narwhal key, Telegram send, Render deployment or broker order was performed. PAPER ONLY.
- **Open:** confirm the serialized response on a read-only live runtime when available; verify the free Narwhal credential and actual endpoint response; locate a third independent same-contract futures source; continue monitor/Telegram acknowledgement audit and build the real 100-setup out-of-sample journal.



## 2026-11-01 — Hide unvalidated risk levels in the Gagarin Cloud API

- **Public-system study:** reviewed QuantConnect LEAN's Apache-2.0 risk-management interface, where a risk model evaluates portfolio targets at each time step, and Freqtrade's documented protections (including StoplossGuard and MaxDrawdown, with protections explicitly enabled in backtests). Applicable lesson: risk state and authorization should be explicit, independently testable outputs. No external code or dependency was imported; LEAN's license is permissive, while Freqtrade's code was not copied.
- **Finding:** `cloud_api.py:_state_json()` serialized `entry`, `stop`, `tp1`, `tp2`, `tp3` and `rr3` unconditionally. This could expose stale/unvalidated risk levels in the JSON API even when the canonical status was `EARLY_BIAS` or `NEUTRAL`.
- **Implemented:** keep BIAS/SETUP/TRADE PAPER visible, but serialize risk levels only when the shared Cloud status adapter reports `EARLY_SETUP` or `CONFIRMED`. That adapter requires fresh-live metadata, live/data-ok state, finite positive price and ATR, and a valid non-stale analysis timestamp; stale PAPER_ENTRY is downgraded before this projection. No price or risk level is calculated or fabricated.
- **Files:** `cloud_api.py`; `tests/test_cloud_api_quote_provenance.py`; this log.
- **Commits:** implementation `451d4ebe5429489b2ca6195682fd5d6498cc5ec3`; regression tests `1ca95766c74cd5f50d3c4c95f663837435c16f0d` and stale-entry regression `5ccd5272e77c92ed7e2ef9989ba22761129f3504`; final PR documentation commit `e52308b65f3efcda7ef2ab5152c7128229f53a72`; squash merge `e5d07c4e0822eabd759226a6b151c764b1dad06f`.
- **Regression coverage added:** EARLY_BIAS and NEUTRAL hide all six risk fields; a stale PAPER_ENTRY is downgraded to PAPER_WATCH and hides all levels; fresh EARLY_SETUP and CONFIRMED preserve already-calculated levels. Existing quote-provenance serialization tests remain in the same module.
- **Validation:** PR #120 was tested on head `e52308b65f3efcda7ef2ab5152c7128229f53a72`. GAGARIN integration run `41334522626` — **482 passed in 2.41s**; Execution Layer `41334522583` — **3 passed**; Public Event Brain `41334522499` — **82 passed**; NEWS alert `41334522509` — **68 passed**; PAPER `41334522648` — **26 passed**. All five workflows SUCCESS. PR #120 was squash-merged to main as `e5d07c4e0822eabd759226a6b151c764b1dad06f`; main readback confirms the serializer gate and stale-level regressions. The connector returned no PR-triggered workflow runs for the merge commit, so no separate post-merge push run is claimed. No production API response, live quote, Telegram delivery, Render deploy, broker connection or order is claimed.
- **SPUTNIK audit:** main contains the merged handoff state-contract fix from `cfb0cea6180b1cf90b8fd974aa68908b7c2fee19`; no duplicate SPUTNIK change was made in this execution.
- **Open:** verify the serialized output on a read-only production runtime; audit actual monitor/Telegram runtime; configure and verify the free Narwhal credential and source independence; obtain a third independent same-contract futures source; complete the real 100-setup out-of-sample journal. PAPER ONLY.

## 2026-11-01 — Cross-bot audit after SPUTNIK source-time correction

- **Repository state:** audited GAGARIN main after PR #120 merge (`e5d07c4e0822eabd759226a6b151c764b1dad06f`). `engine/cloud_api_status.py` still requires fresh-live metadata, finite positive price/ATR and a non-stale analysis timestamp before CONFIRMED/PAPER authorization; `main.py` and `telegram/render_runner.py` remain wired to the shared runtime adapter. No duplicate GAGARIN code change was made in this execution.
- **Residual user-visible WAIT fallback:** GAGARIN's `trump_tracker.py` handoff formatter still uses `row.get('action', 'WAIT')` when the action field is absent. This can print WAIT instead of the explicit NO_DECISION/PAPER_WATCH state even though the shared adapter preserves BIAS. This is the next focused correction; do not remove internal trigger/selector states blindly because some represent technical trigger maturity rather than a user-facing direction.
- **Related reasoning path:** `engine/analyst_reasoning.py` has a legacy WAIT default for missing action metadata, but its directional branch still emits WATCH_LONG/WATCH_SHORT when a supported bias exists. Audit its display contract together with the handoff fix before changing it.
- **Tests/results:** no GAGARIN tests were run in this execution because no GAGARIN code changed. Latest recorded PR #120 CI remains Integration 482 passed, Execution Layer 3 passed, Public Event Brain 82 passed, NEWS Alert 68 passed, PAPER 26 passed; all SUCCESS on PR head before merge. No separate post-merge CI run, live runtime response, Render deploy, quote, Telegram delivery or broker order is claimed.
- **Open:** read-only runtime verification of Cloud API risk-level hiding; third independent same-contract futures source; free Narwhal endpoint/credential verification; real 100-setup out-of-sample journal; monitor and Telegram runtime health. PAPER ONLY.

## 2026-11-01 — Remove the missing-action WAIT fallback from the SPUTNIK → GAGARIN handoff

- **Finding:** the GAGARIN copy of `trump_tracker.py:gagarin_confirmation_message()` still rendered `row.get("action", "WAIT")` when the Cloud API row omitted its action. This obscured an available LONG/SHORT bias and contradicted the canonical API fields `bias`, `setup` and `trade_paper` already emitted by `cloud_api.py:_state_json()`.
- **Public-system study — Freqtrade protections:** the official documentation describes StoplossGuard and MaxDrawdown as separate, explicitly enabled protections; they are backtestable but require deliberate activation and strategy-specific calibration. This supports keeping risk controls observable and separately testable rather than silently turning a missing market decision into a directional veto. No Freqtrade code or dependency was copied.
- **Public-system study — Backtrader:** its official broker documentation exposes configurable commission schemes, futures multipliers/margin and slippage assumptions, while explicitly warning that simulation cannot guarantee real fills. Applicable to the future GAGARIN journal/backtest: record contract-specific costs and slippage rather than interpreting gross simulated results as executable edge. Backtrader was not added as a dependency.
- **Implemented:** each matched instrument now displays BIAS, SETUP and TRADE PAPER separately. Missing direction becomes `NEUTRAL / NO_DIRECTION`; missing setup becomes `EARLY_BIAS` only when LONG/SHORT is present, otherwise `NEUTRAL`; missing trade status becomes `NOT_EXECUTED`. Missing action becomes `NO_DECISION`. A legacy `WAIT` with directional bias is rendered as `PAPER_WATCH`, preserving the bias without implying a trade. No entry/SL/TP is created.
- **Files:** `trump_tracker.py`; `tests/test_news_monitor.py`; this research log.
- **Commits on branch `fix/gagarin-no-wait-sputnik-handoff-20261101`:** implementation `4d4d8ac865f79c09b656d8b522a4bf7ad95ad75a`; three regression tests `0c79d8a5d197aadaaab4feaec6fde27aea8bbf9c`; initial documentation commit `dcac143326cde2085b79dbd5e2d26eee84d68c05`. PR #121 was squash-merged as `58f723f4ff8f38e0e8f6d7b6964d2ed945542851`.
- **Regression coverage added:** missing action preserves LONG and emits NO_DECISION; legacy WAIT with SHORT is normalized to PAPER_WATCH while preserving EARLY_SETUP and blocked PAPER status; missing direction is explicitly NEUTRAL/NO_DIRECTION. All assert that user-facing text contains no WAIT.
- **Safety:** formatting-only change. No price, entry, stop, target, sizing or order is generated; PAPER ONLY. No live API call or Telegram message was sent.
- **Validation:** GitHub Actions on PR head `dcac143326cde2085b79dbd5e2d26eee84d68c05`: GAGARIN Integration run `41340458870` — **485 passed in 2.21s**; Execution Layer run `41340458939` — **3 passed**; PAPER run `41340458826` — **26 passed**; Public Event Brain run `41340458849` — **85 passed**; NEWS alert run `41340458851` — **71 passed**. All five workflows SUCCESS. These are PR-head checks before merge; the connector returned no separate PR-triggered workflow runs for merge commit `58f723f4ff8f38e0e8f6d7b6964d2ed945542851`.
- **Open:** same-contract third independent futures source; Narwhal free-key and upstream independence verification; real 100-setup out-of-sample journal with commission/spread/slippage; post-merge Cloud API runtime verification; source health and full Telegram acknowledgement checks. Backtrader's simulated fills are not a substitute for market microstructure data.
- **References:** Freqtrade protections documentation (https://docs.freqtrade.io/en/2025.9.1/plugins/); Backtrader commission schemes (https://www.backtrader.com/docu/commission-schemes/commission-schemes/); Backtrader slippage model (https://backtrader.com/docu/slippage/slippage/).


## 2026-11-01 — Normalize the analyst-layer missing-action fallback

- **Repository audit:** GAGARIN main was at `6c54ef05b950f604fb00a05c14ab31aae9c870f6`. The prior handoff formatter fix in PR #121 is already merged. A separate residual remained in `engine/analyst_reasoning.py`: absent action metadata defaulted to `WAIT`, and legacy `WAIT` was copied into the returned `governor_action` even though the directional verdict correctly remained `WATCH_LONG`/`WATCH_SHORT`.
- **Public-system study — NautilusTrader:** the official documentation describes a deterministic event-driven engine sharing core execution semantics between historical simulation and live operation, with modular adapters. Its current 2.0.0 release candidate and Rust/Python architecture are much larger than GAGARIN's current pipeline; the source is LGPL-3.0. We did not add the framework or its dependencies. Applicable lesson: preserve explicit lifecycle states and keep the same state contract observable across pipeline surfaces; do not treat framework maturity or backtest parity as proof of trading edge.
- **Implemented on branch `fix/gagarin-analyst-no-wait-default-20261101`:** missing action metadata now yields `NO_DECISION`; legacy `WAIT` is normalized to `PAPER_WATCH` only when LONG/SHORT bias exists, otherwise `NO_DECISION`. The analyst's directional verdict remains unchanged. Explicit `PAPER_ENTRY`/other actions are preserved. No setup, score, Governor threshold, risk parameter, price level or order authorization was changed.
- **Files:** `engine/analyst_reasoning.py`; `tests/test_convergence_engine.py`; this log.
- **Code commit:** `a8bab3e7f6cfa3f183715c7442a493cd4dfae091`.
- **Regression-test commit:** `b565f4fb8e4be2e3d431ef3fe20f549195a8672f`.
- **Coverage added:** missing action with LONG; legacy WAIT with SHORT; missing direction; preservation of explicit PAPER_ENTRY.
- **Validation:** source and tests are committed on the feature branch. GitHub Actions/PR checks are not yet available at the time of this log entry; do not count these tests as passed until CI completes.
- **Limits/open:** this removes the legacy WAIT value from the analyst result, not every internal trigger-maturity state. Runtime/Render behavior, live source health, Telegram delivery acknowledgement, independent same-contract futures references and the real 100-setup out-of-sample journal remain unverified/open. PAPER ONLY; no live order or Telegram send.
- **References:** NautilusTrader official architecture documentation (https://nautilustrader.io/docs/); official open-source and release information (https://nautilustrader.io/open-source/); repository/license (https://github.com/nautechsystems/nautilus_trader).


### CI and merge follow-up — analyst action-state correction

- **PR #122:** merged successfully with squash commit `b08798e36b65de71badc33ffd9060ffc40b00dbf`.
- **Main readback:** `engine/analyst_reasoning.py` contains the `NO_DECISION` default and legacy `WAIT` → `PAPER_WATCH` normalization for directional bias; all four regression tests are present in `tests/test_convergence_engine.py`.
- **GitHub Actions on final PR head `51e5c86c817a1f443ff99eecee314656d27063fb`:**
  - GAGARIN Integration run `41346755165`: **489 passed in 2.22s** (includes four new analyst regressions).
  - GAGARIN PAPER pipeline run `41346755113`: **26 passed in 0.46s**, paper-only smoke test SUCCESS.
  - Execution Layer run `41346755104`: **3 passed in 0.02s**.
  - Public Event Brain run `41346755149`: **85 passed in 0.62s**.
  - NEWS Alert run `41346755125`: **71 passed in 0.43s**.
  - All five workflows completed with SUCCESS. These are final PR-head checks before merge.
- **Post-merge caveat:** no separate PR-triggered workflow runs were returned for squash merge commit `b08798e36b65de71badc33ffd9060ffc40b00dbf`. Main code/test readback succeeded; production runtime/deploy remains unverified.
- **Safety:** no live order, price request or Telegram message; PAPER ONLY.


## 2026-11-01 — Public backtesting framework review: vectorbt

- **Project reviewed:** polakowo/vectorbt public repository and official documentation. The current repository README describes the community edition as fair-code under Apache 2.0 with Commons Clause; VectorBT PRO is a separate expanded product. The public API exposes fee and slippage assumptions in portfolio simulations, including per-order costs and time-varying parameter arrays.
- **Applicable lesson:** GAGARIN's historical trade journal should report gross and net outcomes separately and stress-test spread, commission and adverse slippage by instrument/session/regime. A single zero-cost backtest is not sufficient evidence of edge.
- **Not imported:** no code or dependency was added. The Commons Clause is not treated as plain Apache-2.0 permissive licensing, and PRO-only features/services are excluded. Vectorized OHLCV simulation also does not recreate real DOM/footprint or queue-position fills; these remain explicit limitations.
- **Repository audit:** PR #122's analyst-state correction remains in main. engine/analyst_reasoning.py retains WAIT only as a legacy input-normalization case; missing action metadata defaults to NO_DECISION and directional legacy WAIT maps to PAPER_WATCH. Current main.py and telegram/render_runner.py reads contained no WAIT literal in the inspected versions.
- **Code change this run:** none in GAGARIN; the single functional improvement for this execution is the SPUTNIK persistence privacy fix. No GAGARIN tests were run in this documentation-only review.
- **Next quantitative priority:** inspect GAGARIN's existing backtest cost model before adding any cost-stress module, avoiding duplicate fee/slippage logic. Require real historical fills/quotes, point-in-time splits and out-of-sample reporting; do not infer edge from VectorBT examples or published headline returns.
- **Reference:** https://github.com/polakowo/vectorbt and https://vectorbt.dev/getting-started/features/ . PAPER ONLY.


## 2026-11-01 — Public framework review: TradingAgents and Freqtrade

- **TradingAgents (TauricResearch):** current public README identifies Apache-2.0, a LangGraph multi-agent architecture (fundamental/sentiment/news/technical analysts, bull/bear researchers, trader, risk and portfolio manager), and labels the framework research-oriented. Its supported hosted model providers require provider credentials; Ollama is an optional local route. The repo is active, but model/provider/data non-determinism and API/model costs make it unsuitable as a direct no-paid-service dependency. Its useful lesson is role separation and point-in-time safeguards, not an assumed trading edge.
- **Freqtrade:** current official backtesting documentation includes fees, supports a configurable fee override, detailed timeframe evaluation, exported trade results, and warns that dynamic pairlists can impair historical reproducibility. Its core exchange/pair model is crypto-oriented, so its implementation is not directly reusable for our exchange-traded commodity futures. The portable lesson is to archive the exact data/config/strategy and report net results with explicit fees and execution assumptions.
- **Current GAGARIN audit:** `engine/data.py` still routes Yahoo continuous futures as the only active commodity execution feed; Narwhal remains delayed reference-only and SILV/ BiQuote remain different-basis references. `docs/gagarin-100-point-implementation-plan.md` still marks item 71 (spread, commission, slippage and gaps) as DA IMPLEMENTARE. `engine/paper_orb_cost_note.py` is a research note for an unrelated equity sample, not a general commodity execution-cost model.
- **Decision:** no TradingAgents/Freqtrade code or dependency imported. No strategy or threshold promoted. A cost model must be instrument-specific and use verified tick size/value, fees, bid/ask or documented spread, and observed slippage; otherwise costs remain unknown rather than fabricated.
- **Validation:** documentation-only entry; no GAGARIN code changed and no tests run in this entry. Latest existing GAGARIN CI evidence remains the five successful PR #122 workflows recorded above; production runtime and a new post-merge CI run remain unverified.
- **Next priority:** build a diagnostic-only commodity cost schema from verified contract specifications and actual quote provenance, then validate against real historical paper fills before it affects any signal or Governor. PAPER ONLY.
- **References:** https://github.com/TauricResearch/TradingAgents ; https://www.freqtrade.io/en/latest/backtesting/ .


## 2026-11-02 — Reject ambiguous provider timestamps in GAGARIN market-data ingestion

- **Audit finding:** `engine/data.py::_parse_time()` silently assigned UTC to every ISO timestamp without an offset. That creates an unverified absolute time and can misstate candle ordering/freshness. The shared normalizer is used by the Twelve Data legacy parser, BiQuote, and Yahoo; Yahoo supplies numeric epoch timestamps, while SILV/Narwhal reference timestamps are expected to carry explicit UTC/offset metadata.
- **Implemented:** ISO timestamps without an explicit timezone are now rejected by default. Numeric epoch timestamps and ISO strings with `Z` or a numeric offset remain accepted and normalized to UTC. A caller may supply an explicit timezone only when guaranteed by that provider request contract; the Twelve Data request explicitly sets `timezone=UTC`, so that legacy parser passes `timezone.utc`. No implicit timezone is applied to BiQuote, SILV DATA, or Narwhal.
- **Regression coverage:** added tests for naive datetime/date rejection, UTC and +02:00 normalization, numeric epoch preservation, default candle rejection, and the explicit Twelve Data UTC exception.
- **Public project studied:** Microsoft Qlib. Its point-in-time data design preserves the version of information available at a historical decision time to avoid look-ahead/data leakage. That principle reinforces keeping source timestamps explicit in GAGARIN. Qlib is MIT-licensed and broad/ML-oriented; no dependency or code was imported because this targeted ingestion guard fits the existing engine.
- **Files:** `engine/data.py`; `tests/test_data_finite_values.py`; this log.
- **Code commit:** `ef9e013e380d8a46ae9100cda1c432e9402167a2`.
- **Regression-test commit:** `a92481230b033cbae4845093f025fdb6eb5dcd42`.
- **Initial validation status:** pending when this entry was first written; superseded by the CI and merge follow-up below. PR #123 is now merged and the changed files were read back from `main`.
- **Safety:** no provider, symbol mapping, price, ATR, entry/SL/TP, risk threshold, Governor, or PAPER authorization changed. No network quote, Telegram send, deployment, or order was performed.
- **Open:** inspect the actual BiQuote timestamp shape in a controlled read-only provider response before considering any explicit timezone exception; verify free/independent same-contract futures sources; build the 100+ real-setup out-of-sample journal with spread/fees/slippage.
- **References:** Qlib repository and data-handler architecture: https://github.com/microsoft/qlib and https://github.com/microsoft/qlib/blob/main/qlib/data/dataset/handler.py; Qlib point-in-time database documentation: https://qlib.readthedocs.io/en/latest/advanced/PIT.html.


### CI and merge follow-up — strict provider timestamp provenance (2026-11-02)

- **PR:** #123 merged into `main` as squash commit `5b83b2842ed8804f2a0c7393b54c99d8005e52ac`.
- **Final PR head:** `82076cc17b14d42c265d000f0873b1a2b5c3d49d`.
- **GitHub Actions:** all five workflows completed SUCCESS on the final PR head:
  - Gagarin NEWS alert run `41376208332`: 71 passed.
  - Execution Layer run `41376208540`: 3 passed.
  - PAPER run `41376208452`: 26 passed.
  - GAGARIN integration run `41376208663`: 492 passed.
  - Public Event Brain run `41376208416`: 85 passed.
  - Total reported across workflows: 677 passing test executions (suites may overlap; not a count of unique tests).
- **Main readback:** verified `engine/data.py` rejects timezone-naive ISO timestamps by default, keeps numeric epochs and explicit offsets, and passes `timezone.utc` only in the Twelve Data parser whose request explicitly sets `timezone=UTC`. Verified all three regression tests and this research entry are present on `main`.
- **Post-merge status:** the connector returned no separate status contexts for merge commit `5b83b2842ed8804f2a0c7393b54c99d8005e52ac`; the five successful runs above are PR-head validation, not a post-merge runtime/deploy test.
- **Safety:** no live provider polling, Telegram message, Render deployment, broker action or order was performed. PAPER ONLY.


## 2026-11-02 — Throttle repeated failures on the personal GAGARIN dashboard login

- **Finding:** the new private dashboard login uses PBKDF2 password verification and a signed HttpOnly, Secure, SameSite=Strict session cookie, but the login endpoint had no application-level failed-attempt throttle.
- **Public security research:** OWASP Authentication Cheat Sheet recommends login throttling and warns that account-wide lockout can itself be abused for denial of service. The public fastapi-login-shield package (MIT, PyPI 0.1.9) demonstrates per-client attempt tracking and expiry, but is marked Alpha, has a single maintainer and no PyPI build provenance. No package or new dependency was adopted; the targeted implementation uses Python's standard library only.
- **Implemented on branch security/gagarin-login-throttle-20261102:** atomically reserve login attempts by the ASGI request client's host before the expensive PBKDF2 check; allow five attempts in a rolling 15-minute window, then reject further attempts with HTTP 429 and a Retry-After header. Failed attempts remain counted; a successful login clears that client's history. Reserving before password verification prevents concurrent requests from all passing the same pre-check. The in-process map is bounded to 1,024 clients and uses monotonic time. The code does not trust a caller-supplied X-Forwarded-For header.
- **Files:** cloud_api.py; tests/test_gagarin_private_dashboard_auth.py; this log.
- **Code commit:** 403b6f37b80b90f7409270a85fa8bdb283744bc5.
- **Regression-test commit:** d11f035d1aea009e6409e796d2274567f2a0b906.
- **Tests added:** five attempts are atomically reserved; the sixth is rejected with a bounded retry interval; the rolling window expires as expected; client keys are isolated; clearing after successful authentication restores access. GitHub Actions follow-up: NEWS alert run 41398949580, Public Event Brain run 41398949561, Execution Layer run 41398949660, and PAPER run 41398949559 completed SUCCESS. Integration run 41398949566 completed with 505 passed and one failure in the pre-existing PWA assertion tests/test_personal_app_pwa.py::test_service_worker_never_caches_private_api_responses, which still expects the old exact comment text. The open PR #128 proposes replacing that brittle assertion with a structural check. The auth tests were part of the integration suite; the quiet runner did not emit per-test names, so no separate per-test pass claim is made. Do not merge PR #129 until the unrelated PWA test is reconciled and the full CI is green.
- **Limits:** this is a best-effort per-process throttle, not a distributed rate limiter. Counters reset on process restart, are not shared across multiple workers/instances, and an IP/NAT may represent several users. It is a first defensive layer, not a substitute for edge/WAF limits or a shared store. The login password remains a single shared account credential; no global account lockout was added because it could lock out the owner. No secrets were read or changed.
- **Safety:** no trading signals, prices, provider routing, risk, Governor, PAPER authorization, portfolio, Telegram delivery, deployment or broker behavior changed. PAPER ONLY.
- **References:** OWASP Authentication Cheat Sheet (login throttling and lockout trade-offs): https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html ; fastapi-login-shield 0.1.9 (MIT, Alpha; evaluated but not installed): https://pypi.org/project/fastapi-login-shield/ .

## 2026-11-02 — Keep the personal dashboard API key out of persistent browser storage

- Finding: `static/intelligence.html` stored `CLOUD_API_KEY` in `localStorage`, so the key survived browser restarts and remained available to same-origin JavaScript. This was unnecessary for a manually entered personal dashboard key.
- Implemented on branch `security/gagarin-no-persistent-browser-api-key-20261102`: removed all localStorage persistence/restoration of the API key, disabled browser autocomplete on the password input, and clear the field on logout. The key remains in the password input only while the current page is open and is sent in the existing `X-API-Key` header.
- Regression coverage: assert the dashboard has a password input with autocomplete disabled, contains no localStorage/sessionStorage references, and clears the field during logout. Existing inline JavaScript syntax test remains in place.
- Limits: this reduces persistence at rest in the browser; it does not protect the key from same-origin script execution while the page is open. No API key value was read, logged, or committed. No production deployment or live API call was performed.
- Verification: all 7 GitHub Actions checks passed on PR #134 before merge. PR merged at 2026-11-02T09:54:39Z as `476553c11ae0d67546195dd879266d52fd8b46a8`; all 4 post-merge checks on `main` also completed with SUCCESS. No production deployment or live API request was performed.
- Next: document the server-side `APP_PASSWORD_HASH`, `APP_SESSION_SECRET`, and `CLOUD_API_KEY` setup without example secrets; verify the authenticated production flow after the owner configures the variables.

## 2026-11-02 — Document private dashboard environment setup without secrets

- Finding: .env.example documented execution and demo-provider settings but omitted the three variables required by the private dashboard: APP_PASSWORD_HASH, APP_SESSION_SECRET, and CLOUD_API_KEY. The login route returns HTTP 503 when either authentication variable is absent. No secret values were inspected.
- Implemented on branch docs/gagarin-private-dashboard-env-20261102: documented local generation of the PBKDF2-SHA256 password hash (600,000 rounds, within the verifier's 200,000–2,000,000 accepted range), a separate random session-signing secret, and a distinct API key. All three assignments remain empty in .env.example; generated values must be configured directly in the hosting Environment UI and never committed or sent in chat.
- Files: .env.example (commit 503e2c8d784b4b46c24cb459b8279b4b977490d9); tests/test_personal_app_pwa.py (final test/code commit de873eafcd060e2e9cf56bf050ef32076b02846c); this research log.
- Regression: require each variable to appear exactly once with an empty assignment, and require the documented generator, accepted PBKDF2 range, and hosting-UI instruction.
- Verification: five PR workflow runs on final branch head ee9282e3e1404aa798f5ce161ebfd117190aec57 completed SUCCESS: SOYUZ GAGARIN Tests 41431548348, Public Event Brain 41431548451, PAPER 41431548450, Execution Layer 41431548604, and NEWS Alert 41431548484. PR #135 merged on 2026-11-02 at 10:47:38Z as 719d0366ba1708f14cd9c5c2a9ba233fc81a3cf7. The GitHub connector's commit-run lookup returns PR-triggered runs only, so no post-merge main CI status is claimed.
- Limits/open: Render environment values were not read or changed; deployment, login/logout, API-key authentication, Sputnik handoff and Telegram delivery are not verified live. The Render workspace has not been explicitly confirmed for connector operations. The PWA still lacks a dedicated iOS PNG icon. No paid service, public private-data hosting, or live trading was enabled.
- Safety: no credentials were generated, read, logged or committed; no trading strategy, score, Governor, entry/SL/TP or PAPER authorization changed.
- Research note: Freqtrade's current Lookahead Analysis compares a full backtest against isolated signal backtests to detect indicator/entry/exit changes, but can only validate signals that actually trigger; this caveat must be preserved when adapting it to GAGARIN. Reference: https://www.freqtrade.io/en/stable/lookahead-analysis/


## 2026-11-02 — Dedicated iOS home-screen PNG icon

- **Finding:** the private PWA linked `apple-touch-icon` to an SVG only. iOS home-screen installation needs a dedicated raster touch icon for reliable presentation.
- **Implemented:** add `static/apple-touch-icon.png` at 180×180, update the HTML touch-icon link and web manifest, add the PNG to the service-worker App Shell, and bump the cache version to v2 so installed clients fetch the new asset.
- **Files:** `static/apple-touch-icon.png`, `static/intelligence.html`, `static/manifest.webmanifest`, `static/sw.js`, `tests/test_personal_app_pwa.py`.
- **Commits:** initial asset `ec0620412a24d4bf77bfcaa6faa7d9f08bf61871`; manifest `363ecb199b816483e675be823a8c6f60e61bd0a3`; HTML `3cab3e75bb50f938439b144d8193a5fee123a3c5`; service worker `61efe419c2f5513ebfea954b5f08a9fc669715a2`; test `14cf031297c718eab05233a39e1ac8311396ac3e`; antialias asset refinement `b4e5bc4b66e5f4d91407774566292e15738703b0`.
- **Validation:** local PNG inspection confirmed signature and 180×180 dimensions. GitHub Actions on final code/test commit `b4e5bc4b66e5f4d91407774566292e15738703b0`: SOYUZ GAGARIN Tests run `41438331105` SUCCESS; Public Event Brain `41438330919` SUCCESS; PAPER `41438330941` SUCCESS; NEWS Alert `41438330945` SUCCESS; Execution Layer `41438330949` SUCCESS. Regression checks the PNG signature/dimensions, manifest entry, iOS link and App Shell cache entry.
- **Safety:** the service worker still bypasses `/api/` and authenticated dashboard HTML. No credentials, private API responses, trading logic, Governor, PAPER authorization, or orders changed.
- **Limitations:** no physical iPhone installation test yet. The Render dashboard login remains HTTP 503 because at least one of `APP_PASSWORD_HASH` or `APP_SESSION_SECRET` is not configured; database persistence is disabled because `DATABASE_URL` is absent. The PR is not deployed until merged and deployed separately.
- **Mode:** PAPER ONLY.


## 2026-11-02 — Timestamp- and contract-aligned 15m/5m pullback diagnostic

- Implemented an independent, dependency-free MTF overlay on branch `research/gagarin-mtf-timestamp-contract-20261102`.
- Both 15m and 5m inputs now require completed OHLC bars with UTC close timestamps, the same provider, symbol, explicit futures contract, expiry, currency and unit.
- Rejects spot/CFD basis, missing or naive timestamps, non-monotonic/misaligned timestamps, stale/future bars, incomplete candles, malformed OHLC, insufficient history and mismatched latest 15m/5m endpoints.
- Allows finite negative historical futures prices (including historical WTI settlements); ATR must remain positive.
- Adapter records the result in `metadata.multi_timeframe_pullback`; Telegram shows its diagnostic state. Missing provider data is explicitly `NOT_PROVIDED`.
- Safety: diagnostic only; does not change scores, BIAS, Governor, gates, trigger, entry, SL, TP, sizing or PAPER authorization. No orders.
- Limitation: no production provider has yet been verified to supply the required timestamped exact-contract 15m/5m payload. This is not a live-data or performance claim.


## 2026-11-02 — Reject fractional ISO timestamps in MTF diagnostic

- **Finding:** numeric fractional epochs were rejected, but ISO-8601 timestamps with fractional seconds were passed through `datetime.fromisoformat` and truncated by `int(parsed.timestamp())`. This could silently turn a sub-second timestamp into a whole-second candle close.
- **Change:** reject fractional-second notation (dot or comma) in ISO timestamp strings; retain timezone-aware whole-second timestamps.
- **Regression:** add an ISO fractional timestamp case to `tests/test_multi_timeframe_pullback.py`.
- **Scope:** diagnostic validation only. No scoring, BIAS, Governor, entry, SL/TP, sizing, Telegram authorization or order behavior changed.
- **Validation:** GitHub Actions is required on the updated PR head; no passing result is claimed until the run completes.
- **Mode:** PAPER ONLY.


## 2026-11-02 — Safe diagnostics for malformed GDELT JSON

- **Finding:** the deployed NEWS monitor logged a generic `JSONDecodeError` when GDELT returned a non-JSON response. This did not stop the wider poll because the source-specific failure/backoff path already catches provider errors, but it did not identify whether the upstream response was HTML, another content type, or an unexpectedly empty payload.
- **Implemented:** normalize JSON decoding failures into `GDELTInvalidJSONError` with only bounded metadata: sanitized content type, HTTP status (when valid), and response byte count. The source failure log includes this curated metadata.
- **Privacy/safety:** the response body is never included in the exception message or log. Existing per-source cooldown and RSS fallback behavior is unchanged; no retry is added and no request frequency is increased.
- **Files:** `telegram/news_monitor.py`; `tests/test_public_feed_reliability.py`.
- **Commits:** implementation `0b62edbb58d18bc52b4a3330792b41be48144a94`; regression test `0d9448d664085cd912b3ddb2abf01456c38733ea`.
- **Test:** new mocked regression asserts content-type/status/byte-count diagnostics and proves a body marker is not exposed. CI is pending; no test pass is claimed before Actions completes.
- **Limits:** this improves diagnosis, not GDELT availability. HTTP 429, upstream invalid JSON, and source outages remain possible. No live feed quote, Telegram send, deployment or order is claimed.
- **Mode:** PAPER/DEMO only.


### CI follow-up — GDELT safe diagnostic test expectation

- Initial PR run `41472174720`: integration suite reported **525 passed, 1 failed**. The failure was only the test's expected sanitized Content-Type string: the sanitizer correctly retained the MIME slash while removing the semicolon/space separator. Production implementation behaved as intended.
- Corrected the expected value in test-only commit `853ec7bfb0c12002ce3b932b820b62ff15363150`.
- The PR head now requires a fresh complete CI run. The initial run remains recorded as failed; it is not being represented as green.


## 2026-11-02 — Add LUBJANKA M5 signal interceptors

- **Finding:** the existing Gagarin scan surfaces broad 4h/24h opportunity context and directional observations, but it does not independently label the first short-horizon move, momentum expansion and close beyond a recent range.
- **Implemented:** new pure diagnostic module `engine/lubjanka.py` with three independent interceptors: `EARLY_MOVE`, `MOMENTUM` and `BREAKOUT`. It uses the existing 5-minute OHLCV candles, computes a local true-range reference, ignores the still-forming bar, and records source, last completed bar timestamp/age, last close, ATR, range-expansion and volume proxies.
- **Integration:** `engine/gagarin.py` stores the result in `state.metadata["lubjanka"]`. `telegram/aggressive_alert.py` displays intercepted events, uses LUBJANKA direction as an alert-only fallback when all other bias fields are absent, and includes interceptor identity in alert deduplication, so a newly detected interceptor can trigger a changed alert even when the broader directional stage is unchanged.
- **Tests added:** `tests/test_lubjanka.py` covers LONG/SHORT interception, EARLY_MOVE/MOMENTUM/BREAKOUT, flat-market no-signal, incomplete-bar exclusion, stale data, non-monotonic timestamps, malformed OHLC and finite negative historical futures prices. `tests/test_lubjanka_telegram.py` covers Telegram display and alert-signature changes.
- **Safety:** diagnostic only; no change to setup direction, scores, Governor, risk, entry/SL/TP, PAPER authorization or order execution. LUBJANKA does not generate execution levels. Volume is an OHLCV proxy, not DOM/footprint.
- **Branch:** `feat/gagarin-lubjanka-interceptors-20261102`.
- **Commits:** module `8a2d0d0dcb37f8d2aeaa42accd1642c52eb457fd`; detector tests `f27f3fc046d6ec065ece927f7f80f3dc8d2d68cd`; Telegram tests `a88d75201b23456646df9fca9d2ec5d3210a6f8b`; engine integration `9ab6aa576ec6c271dd5bd2d88ba386096798a71c`; Telegram integration `c0a7822d4a541b6675860072e1567470becc13e3`; alert-only LUBJANKA direction fallback `33bff9b67a8729342bf9fbbde389a662bd859d3d`; fallback regression `b866062b5cfe671b1f2b6203c666d7227f414ab6`; JSON-stable alert signature fix `c2114dcb44ece5c81ddf52753386ffadf085a1a8`.
- **Verification:** initial run `41485037141` reported **537 passed, 2 failed** because a nested tuple in the alert signature changed to a list after JSON persistence. Fixed in `c2114dcb44ece5c81ddf52753386ffadf085a1a8`. Final-head CI: Gagarin integration **540 passed** (`41485236016`); Public Event Brain **86 passed** (`41485236052`); NEWS Alert **72 passed** (`41485236129`); Execution Layer **3 passed** (`41485236061`). PR #142 merged as `4b6ee92df705fdad0691395e1be7091057f7876c`. Render cloud and Telegram v2 deployments on that commit reached LIVE; Telegram webhook verified and monitor startup logged. First post-deploy LUBJANKA signal output and live-data performance remain unverified. No order execution.
- **Next:** run focused and full CI, inspect signal output on real fresh M5 data, then add the separate SPUTNIK event-impact interceptor only after this module is validated.

## 2026-11-02 — Add LUBJANKA false-breakout interceptor

- **Finding:** the first LUBJANKA release detected early directional movement, momentum expansion and closes beyond the previous six-bar range, but did not label a failed range sweep where a completed M5 candle trades beyond a boundary and closes back inside it.
- **Implemented:** engine/lubjanka.py now emits FALSE_BREAKOUT as EARLY_SETUP: an upside rejection is a SHORT hypothesis; a downside rejection is a LONG hypothesis. A two-sided sweep retains both observations and is marked as a directional conflict by the existing event aggregator. The existing Telegram formatter and alert deduplication already consume the generic event list, so no second alert pipeline was added.
- **Files:** engine/lubjanka.py; tests/test_lubjanka.py; tests/test_lubjanka_telegram.py.
- **Branch:** feat/gagarin-lubjanka-false-breakout-20261102.
- **Commits:** detector 8a7db8c3f27a845dfd88700aa21f1ceed063dd39; unit tests 6641bc0379a2d187c12297c671896934b4ac0be0; Telegram test 1f841cdf573324b8ce8f72d455959d4d0f633e2e; PR #143 squash merge 722f807300e6641dfe4b809deadb03a2862e8792.
- **CI on final PR head:** GAGARIN integration 41489166016 — 544 passed in 3.35s; Public Event Brain 41489165408 — 86 passed in 0.59s; NEWS alert 41489165744 — 72 passed in 0.39s; Execution Layer 41489165725 — 3 passed in 0.03s; PAPER workflow 41489165375 — 26 passed in 0.15s, with its separate smoke command returning the expected PAPER_WATCH / ASSET_NOT_IN_UNIVERSE for the workflow's unconfigured sample asset. All five workflows completed SUCCESS.
- **Safety:** completed M5 OHLCV only; no forming bar; observation-only. No score, Governor, risk, entry/SL/TP, PAPER authorization or order execution changed. The pattern is an OHLCV rejection proxy, not proof of DOM/footprint liquidity or a calibrated reversal.
- **Limits/open:** no live-data performance, real signal, Telegram message or post-merge Render deployment is claimed. The market monitor remains on a 15-minute cycle, so M5 candles are sampled every 15 minutes; do not shorten it until free-provider rate limits and request load are verified. Render account inspection is blocked until the owner confirms the workspace selection. The PWA/login and DATABASE_URL status therefore remain unverified in this run; the free database's previously reported expiry is 2026-11-06 10:44:06 UTC.
- **Next:** verify actual LUBJANKA output on fresh provider M5 bars and measure free-source request capacity before considering a 5-minute monitor; keep SPUTNIK PR #91 unmerged until its base is refreshed and CI rerun, and PR #92 unmerged while ranking CI is red. PAPER ONLY.


## 2026-11-02 — Protect every static HTML app and remove legacy browser API-key persistence

- **Finding:** the authentication middleware protected only `/static/intelligence.html`, while `/static/aggressive.html` was served by the public StaticFiles mount without the private session check. The aggressive page and an unused legacy dashboard script also read/write `gagarin_key` in browser `localStorage`, contrary to the private-app credential boundary.
- **Implemented:** require the signed, HttpOnly application session for every `/static/*.html` path; leave non-HTML app-shell assets public for PWA installation. Removed all API-key `localStorage` reads/writes from the aggressive page and legacy inline dashboard. Added password-input autocomplete controls and clear the aggressive page's in-memory key field on pagehide.
- **Files:** `cloud_api.py`, `static/aggressive.html`, `tests/test_personal_app_pwa.py`, this research log.
- **Regression coverage:** all static HTML paths must be covered by the private-session middleware; both current dashboard pages and the legacy inline dashboard must contain no localStorage/sessionStorage API-key persistence.
- **Validation:** implementation is on a fresh branch from main. GitHub Actions CI is required before merge; no test result or production deployment is claimed in this entry.
- **Security boundary:** manifest, icons and service worker remain publicly fetchable as PWA shell assets; private HTML requires the signed HttpOnly cookie; API routes continue to require `CLOUD_API_KEY`. No secrets were read, changed, or committed. PAPER ONLY; no broker or order action.


### Final CI and merge verification — private HTML/API-key hardening (2026-11-02)

- **PR:** #144 merged into `main` as squash commit `8829d4b26dadc18c185a468deb0c53e7072df5c6`.
- **Final PR head:** `e93354cb02d4d9778acc0d236f18208505c1576e`; base was current `main` `79c2ba9957303bd330b3cd5b6191d20aec564bbc`, with zero commits behind.
- **GitHub Actions:** all five required workflows succeeded: Gagarin Integration **545 passed**, Public Event Brain **86 passed**, NEWS Alert **72 passed**, PAPER **26 passed**, Execution Layer **3 passed**. Total **732 tests passed**. PAPER smoke test returned the expected `PAPER_WATCH / ASSET_NOT_IN_UNIVERSE` for its deliberately unconfigured sample asset.
- **Main readback:** middleware now checks every `/static/*.html` path; `static/aggressive.html` and the legacy inline dashboard contain no `localStorage` or `sessionStorage` API-key persistence; the regression tests are present on main.
- **Production limit:** no Render workspace was selected for this run, so no post-merge deployment, live /login, logout, protected-route HTTP, or PWA-install verification is claimed. This is a repository/CI security fix, not proof that the running service has received it.
- **Safety:** no secret values were read or changed; manifest, icons and service worker remain public app-shell assets; API routes still require `CLOUD_API_KEY`. PAPER ONLY; no broker/order action.


## 2026-11-02 — Increase Gagarin scheduled market scan cadence to five minutes

- Finding: LUBJANKA evaluates completed M5 candles, but the scheduled GitHub Actions monitor was triggered every 15 minutes. A short-lived M5 move could form and fade between scans.
- Implemented on branch `feat/gagarin-five-minute-interception-scan-20261102`: changed the scheduled monitor cron from every 15 minutes to every 5 minutes and aligned `MONITOR_INTERVAL_MINUTES` to `5`.
- Scope: only the scheduled Gagarin monitor workflow; no strategy thresholds, data-provider settings, Governor, PAPER authorization, or order behavior changed.
- Limits: this increases scheduled run frequency threefold and therefore increases provider request volume. It does not guarantee a scan exactly on each five-minute boundary because GitHub Actions scheduling can be delayed. Provider rate limits and actual workflow duration must be observed before claiming uninterrupted five-minute coverage. Public repository hosted-runner usage is not a guarantee of provider capacity.
- Validation: workflow diff checked for both cadence values; CI pending on PR. No production Render setting changed and no live trade signal or Telegram delivery is claimed.
- SPUTNIK comparison: `.github/workflows/trump_tracker.yml` already schedules the main public-event monitor every five minutes (`2-59/5`); no redundant schedule change was made there.
- Safety: PAPER ONLY; no orders sent.


## 2026-11-02 — Keep early LUBJANKA interceptions visible in Telegram shortlist

- **Finding:** the aggressive Telegram alert builder returns at most ten directional candidates. Sorting mainly by probability and quality could push a valid LUBJANKA interception with incomplete scores out of the message when ten higher-scoring ordinary candidates were present.
- **Implemented:** risk warnings remain first, confirmed entries second, then detected LUBJANKA interceptions ahead of ordinary possible/observation candidates. Probability and quality remain tie-breakers within each priority.
- **Regression:** a test creates ten high-scoring ordinary candidates plus one low-scoring LUBJANKA false-breakout interception and verifies the early interception remains visible in the ten-item shortlist.
- **Safety:** display ordering only. No detector thresholds, scores, direction, Governor, risk, entry/SL/TP, PAPER authorization, provider calls, Telegram transport or order execution changed.
- **Mode:** PAPER ONLY. CI required before merge; no live Telegram delivery or production deployment claimed.


## 2026-11-02 — Stop publishing PAPER journal CSVs from public GitHub workflows

- **Finding:** both `.github/workflows/soyuz.yml` and `.github/workflows/gagarin-monitor.yml` granted `contents: write` and committed `paper_trade_log.csv` / `gagarin_feedback.csv` to the public repository after each run. The current `paper_trade_log.csv` is tracked on the public default branch; its contents were not opened or copied during this change.
- **Implemented:** remove the CSV commit/push step from both workflows and reduce workflow repository permissions to `contents: read`. This prevents future scheduled/manual runs from publishing new journal rows to the public Git history.
- **Regression:** replace the old persistence-step assertion with checks that both workflows use read-only repository permissions and contain no journal git-add/push step.
- **Trade-off:** until private D1 persistence is deployed and verified, journal/feedback files produced on ephemeral GitHub runners will not survive between runs. This is an intentional privacy-first stopgap, not a claim that persistence is solved.
- **Open risk:** the existing tracked `paper_trade_log.csv` and its historical Git versions remain accessible in the public repository/history. They must be backed up securely and then removed/purged in a separately planned, verified action; do not rewrite public Git history blindly.
- **Safety:** no secret access, no database changes, no deployment, no paid service, no real orders.

## 2026-11-03 — Remove implicit Render endpoint defaults

- Finding: the legacy `cloud_monitor.py` silently defaulted `GAGARIN_CLOUD_URL` to a Render hostname. The MT5 bridge also contained a Render URL as its default, and the private API/.env guidance still told the owner to configure secrets on Render. These paths contradicted the no-Render architecture and could direct credentials or requests to an unwanted legacy service.
- Implemented on branch `no-render/require-explicit-cloud-url-20261103`: `cloud_monitor.py` now requires an explicit HTTPS base URL, rejects URL credentials/query/fragment and non-HTTPS schemes, sends no request when configuration is missing/invalid, and does not follow redirects with the API-key header. The MT5 bridge now has an empty URL default and refuses to start until an explicit HTTPS URL and bridge key are configured. Private API and .env setup copy is provider-neutral; `.env.example` documents the optional explicit `GAGARIN_CLOUD_URL`.
- Files: `cloud_monitor.py`, `cloud_api.py`, `mt5/SoyuzGagarinBridge.mq5`, `.env.example`, `tests/test_no_render_endpoint_defaults.py`.
- Commits: `872c156ab0560bf2340abe9a894e96c5dcb3b0b7` (monitor fail-closed); `b9a8ff501e4d710cbc2159a449f09ef2c03b8d14` (provider-neutral API copy); `be0879b4a4c573d3dbb046352c1fb777907d3199` (MT5 bridge disabled until explicit endpoint); `d43cd67b96a36bad0327db1e5326936548b6144f` (.env example); `e4420342fe0ec6a8c40dec0af26d0bfe94f0c07f` and `ac915bafb900f37866a92b9ae6998b1ccb9796b9` (regression tests).
- Tests: new offline tests cover missing URL, insecure/credentialed/query/fragment URLs, explicit HTTPS request construction, redirect refusal, absence of the legacy host in active config, and the MT5 empty-default guard. CI must run on the PR before merge. MQL compilation was not available in this execution; the MT5 check is source-level only.
- Limits: no endpoint was contacted, no API key was read, no deployment was performed, and no MT5 EA was run. This removes implicit Render fallbacks; it does not implement the Cloudflare Worker or activate the bridge.
- Next: verify PR CI; then implement the Worker API contract and private D1 binding without migrating live data until a backup/export and restore path are tested. PAPER ONLY.


### CI follow-up — provider-neutral setup copy

- First PR integration run `41551882806` reported **559 passed, 1 failed**. The failure was an existing assertion in `tests/test_personal_app_pwa.py` that still required the literal phrase `hosting Environment UI`, while the provider-neutral .env copy correctly changed this to `backend Environment UI`.
- Updated that assertion only in commit `bad113a29bd3faf14d5b9dabc4413e20c08b2712`. No runtime code change was needed.
- Other observed PR workflows on the original head: PAPER SUCCESS, NEWS Alert SUCCESS, Public Event Brain SUCCESS; Execution Layer was still in progress at the time of inspection.
- A new full integration run is required on the corrected head before merge. The MQL bridge is source-checked only; no MetaEditor compiler is available.


### Post-merge verification — 2026-11-03

- PR #153 was merged by squash into `main` as `ab548c8da53a3ea3dc33c5891dc61e483bb4137b`.
- Corrected-head integration run `41551959993`: **560 passed in 2.16s**.
- Additional workflows on the corrected head all completed SUCCESS: PAPER `41551959887`, NEWS Alert `41551959985`, Public Event Brain `41551959934`, Execution Layer `41551959845`.
- The first integration attempt's single stale documentation assertion was corrected before the successful final run.
- Read-back/deployment distinction: source changes are merged on GitHub; no backend deployment, external endpoint request, Telegram send, MT5 execution, or Cloudflare setup was performed. MetaEditor compilation remains unverified.


## 2026-11-03 — Restore Gagarin provider-heavy monitor to 15-minute cadence

- Finding: the default-branch .github/workflows/gagarin-monitor.yml had been changed to run every five minutes. Render logs for soyuz-gagarin-telegram-v2 recorded four GDELT HTTP 429 failures between 00:21:06Z and 00:22:09Z on 2026-11-03, with cooldowns of 900s and 1800s. The paired errors came from two Render instance IDs; current NEWS code polls RSS every 60s and enforces a per-process GDELT minimum interval of 900s. This proves source throttling and overlapping process-local cooldowns, not that the GitHub Actions cron caused the 429s. A separate 10:34Z–11:34Z query returned no application logs, so uninterrupted monitor activity was not established.
- Decision: restore the full provider-heavy scheduled monitor to every 15 minutes and set MONITOR_INTERVAL_MINUTES=15. The M5 LUBJANKA detector and its completed-candle semantics are unchanged; this changes only how often the full provider-heavy workflow is launched.
- Safety: existing thresholds, provider configuration, Governor, PAPER authorization, entry/SL/TP logic and order behavior are unchanged. PAPER_TRADING_ONLY=1 remains enforced. No Render setting, service plan, database allowlist or secret was changed.
- Regression: add tests/test_gagarin_monitor_cadence.py to assert the sole cron is */15 * * * *, the runtime interval is 15 minutes, and PAPER-only mode remains enabled.
- Validation: branch-only change; GitHub Actions CI is required. No scheduled run, live quote, Telegram delivery or deployment is claimed.
- Research comparison: Freqtrade's official exchange implementation tracks per-pair OHLCV refresh/poll timestamps and configurable candle-lag grace; its docs warn that exchange request limits constrain history fetches. This supports treating freshness and rate capacity as measured constraints, not assuming a five-minute schedule is sustainable.
- Open items: GDELT 429 source cooldowns need review; the Render NEWS listener's last successful polling heartbeat is not proven by the empty recent-log window. Reconsider a five-minute lightweight LUBJANKA-only scan only after provider request budgets, freshness and successful heartbeat are measured independently of the full NEWS monitor.
- Mode: PAPER ONLY. No broker orders.


## 2026-11-03 — Remove unused credentials from the Gagarin scheduled runner

- The scheduled `main.py` monitor does not call the Sifting integration or the separate Trading 212 Invest command flow. Removed their secret-to-environment mappings from this workflow only; Trading 212 Invest code and other workflows are untouched.
- Kept the optional Narwhal reference mapping because it is part of the market-data adapter and may be configured independently.
- Added a regression assertion that the scheduled runner does not receive Sifting or Trading 212 Invest credentials.
- This complements the 15-minute cadence correction. No analysis modules, directional logic, entry thresholds, risk controls, Telegram configuration, or PAPER-only authorization were removed.
- PAPER ONLY; no deployment, broker connection, or real orders.


## 2026-11-03 — Remove duplicate scheduled aggressive full-universe scan

- Audit: `.github/workflows/aggressive-alert.yml` independently ran `engine.gagarin.analyze_universe(operational_commodities())` every hour and sent entry/reversal Telegram alerts. The main Gagarin monitor already runs the same core engine across the operational universe and sends operational Telegram alerts on its own schedule.
- Cleanup: removed only the aggressive workflow's hourly cron. Kept `workflow_dispatch`, the aggressive formatter, tests, and manual run path available for intentional diagnostics.
- Rationale: avoid a second overlapping provider-heavy full-universe analysis and potential duplicate alerts. This is a schedule-level cleanup; it does not remove the aggressive strategy code or alter its scoring/risk logic.
- Regression: added a test that the aggressive workflow remains manually triggerable and has no scheduled trigger.
- Expected savings: one complete aggressive full-universe scan per hour and its associated provider requests, plus reduced duplicate alert risk. Exact request count and runtime savings are not measured yet.
- PAPER ONLY; no live orders, secret changes, deployment or Render changes.


## 2026-11-03 — Post-merge verification: duplicate scan cleanup

- PR #157 merged to main as `6038ad1f2f16689067a4c54e5c59492f276f6ac8`.
- All five PR-head GitHub Actions workflows completed SUCCESS on the exact final PR head `d0ab950275cb366ee91c2d75bcc7de9393785d63`.
- Verified on main: the full monitor cron is `*/15 * * * *` and `MONITOR_INTERVAL_MINUTES=15`.
- Verified on main: `aggressive-alert.yml` retains `workflow_dispatch` and has no schedule trigger.
- This is a GitHub source merge, not proof of Render deployment, a live quote, Telegram signal delivery, or trading performance.


## 2026-11-03 — Stop hourly runs of static day-research notes

- Audit of `engine/day_research.py`: the job serializes the in-repository `NOTES` dictionary into `data/day_research.json`. It performs no external data fetch, no new market observation, no backtest, and does not feed `final_decision`.
- The existing snapshot's notes match the script's fixed dictionary and its timestamp is preserved when content is unchanged. Re-running it hourly therefore does not create new research evidence.
- Removed only the hourly schedule from `.github/workflows/day-research.yml`; retained `workflow_dispatch` so the snapshot can still be regenerated deliberately. No research content, signal logic, scoring, thresholds, or risk settings changed.
- Expected effect: stop up to 14 redundant scheduled GitHub Actions runs per day for this static snapshot job. This is a workflow-run reduction, not a claimed trading or market-data improvement.
- PAPER ONLY; no deployment, live data request, Telegram message, or order.


## 2026-11-03 — Remove pip self-upgrade from daily driver fetch

- The daily `fetch-drivers.yml` job already uses `setup-python` with pip caching and installs its sole runtime dependency, `requests`.
- Removed the unconditional pip self-upgrade; kept the daily schedule, manual trigger, EIA/FRED configuration, dependency installation, and driver collection unchanged.
- This removes one unnecessary package-index operation from the daily job. No data-source calls, market logic, or driver mapping changed.
- PAPER ONLY; no deployment or orders.


## 2026-11-03 — Remove disabled Twelve Data legacy implementation

- The active execution route has explicitly excluded Twelve Data for the full active universe; `_try_provider()` returns a hard-disabled result before any network call.
- Repository-wide reference search found the old Twelve Data catalog, symbol resolver, candle fetch helpers, API-key config value and their associated test hooks only in `engine/data.py`, `config.py`, and one routing test. No active workflow or other module calls them.
- Removed those unreachable legacy fetch/catalog helpers and the unused API-key configuration. Kept the explicit hard-disable branch and strengthened its test to fail if any HTTP request is attempted.
- Kept `AGRI_SYMBOLS`, explicit Yahoo futures mappings, active Yahoo/FX routing, and all market-basis checks.
- This reduces dead code and removes an unused paid-provider credential surface; it does not reduce current quote latency or change the active data route.
- PAPER ONLY; no provider substitution, strategy change, deployment, or orders.


## 2026-11-03 — Remove pip self-upgrade from Public Event Brain test workflow

- Audit: `.github/workflows/public-event-brain-tests.yml` configures Python 3.12 with `actions/setup-python@v5`, then ran `python -m pip install --upgrade pip pytest requests`. The test job needs only the two test/runtime packages; the explicit pip self-upgrade is not an application dependency or a test requirement.
- Implemented on branch `cleanup/remove-pip-self-upgrade-public-event-tests-20261103`: changed the install command to `python -m pip install pytest requests`. Preserved Python version, triggers, permissions, timeout, test selection and test execution.
- Regression: added `tests/test_public_event_workflow_install.py` to assert that Python setup and both packages remain, the self-upgrade is absent, and the event-brain test command remains configured.
- Cost/benefit: removes one explicit pip upgrade/version-resolution operation per Public Event Brain workflow run. This workflow has push and pull-request triggers, not a time-based schedule; actual run count, package-index request count and wall-clock savings are not measured.
- Safety: no runtime provider, data source, polling cadence, event collection, catalyst, market signal, direction, score, Governor, risk, journal, Telegram runtime, PAPER authorization or order path changed. PAPER ONLY; no secrets, Render settings, live APIs, deployment, Telegram send, broker action or order.
- Validation: PR CI must execute on the exact final head before any merge consideration.
