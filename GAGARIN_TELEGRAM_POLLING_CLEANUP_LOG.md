# GAGARIN Telegram Polling Cleanup Log

## 2026-11-03 — Remove redundant pip self-upgrade from Telegram polling

- Base main at audit time: 842890b63fbbd2c4dddea2bf4e9fd5dc2cbb2df3.
- Audited .github/workflows/telegram-polling.yml: it uses actions/setup-python@v5 with cache: "pip", then installs the repository requirements.txt (or the existing requests fallback) before running python telegram/polling_runner.py.
- The workflow already has the same setup/install pattern as .github/workflows/gagarin-monitor.yml, which installs dependencies directly without upgrading pip first.
- Removed only python -m pip install --upgrade pip. Kept the five-minute weekday schedule, manual dispatch, concurrency group, token validation, dependency installation, Telegram polling entrypoint, and PAPER_TRADING_ONLY=1.
- Added tests/test_telegram_polling_workflow.py to assert that the schedule/manual entrypoints, pip cache, dependency install, token validation, PAPER-only environment and polling runner remain, while the self-upgrade command is absent.
- Cost/benefit: removes one pip self-upgrade/version-resolution operation from each scheduled/manual workflow invocation. The cron permits up to 180 scheduled invocations per weekday (900 across five weekdays), before missed/queued/cancelled runs; this is a schedule-derived upper bound, not an observed run count. Exact PyPI HTTP request count and wall-clock savings are not measured.
- No application dependency, provider, polling interval, Telegram handler, event source, signal logic, score, direction, Governor, entry, SL/TP, sizing, journal, LUBJANKA or PAPER authorization changed.
- No secrets or Render settings read/changed; no manual workflow dispatch, Telegram send, live provider request, broker connection, order or deployment performed. PAPER ONLY.
- Research basis: GitHub's Python Actions guide documents setup-python pip caching followed directly by pip install -r requirements.txt; Freqtrade's data guide illustrates incremental reuse rather than repeated full downloads. Only the applicable CI dependency-install principle was used; no third-party code copied.
- Pending: PR-head GitHub Actions validation. Do not merge or deploy automatically.
