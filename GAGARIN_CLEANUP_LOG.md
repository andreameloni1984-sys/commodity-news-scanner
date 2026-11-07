# GAGARIN cleanup log

## 2026-11-03 — Remove redundant pip self-upgrade from manual aggressive workflow

- Repository baseline: `main` at `dea2eb8177fe2e3cabb3d91485c949c865804ec6`.
- Candidate: `.github/workflows/aggressive-alert.yml` ran `python -m pip install --upgrade pip` before installing the repository's pinned `requirements.txt`.
- Evidence: the same workflow uses `actions/setup-python@v5` with pip caching; the scheduled `gagarin-monitor.yml` already installs `requirements.txt` directly without self-upgrading pip. The aggressive workflow is manual-only after the duplicate hourly scan was removed, so the overhead occurs only on an intentional manual run.
- Change: remove only the pip self-upgrade command. Keep setup-python, pip cache, requirements installation (and its fallback), compile check, main import smoke test, news/Sputnik tests, aggressive alert path, and `PAPER_TRADING_ONLY=1`.
- Test: add `tests/test_aggressive_workflow_install.py` to assert no self-upgrade while dependency installation, compile/import/test checks and PAPER-only execution remain.
- Cost/benefit: removes one explicit package-manager self-upgrade operation and its associated package-index/version-resolution work per manual run. Exact HTTP request count and wall-clock savings are not measured; no fixed time saving is claimed.
- Scope: workflow setup only. No runtime package, provider, polling schedule, strategy, score, direction, Governor, entry/SL/TP, sizing, Telegram code or PAPER authorization changed.
- Research: Freqtrade's official DataProvider caches per-pair/timeframe candle data and tracks freshness; its pairlist docs warn that repeated exchange requests add latency and can hit API limits. Applied only the general principle of removing unnecessary setup work; no Freqtrade code copied. See https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/data/dataprovider.py and https://github.com/freqtrade/freqtrade/blob/develop/docs/includes/pairlists.md.
- Limits: CI must pass on the final PR head. This does not prove a live run, Telegram delivery, or measurable end-to-end speedup.
- Safety: draft PR only; no merge, deployment, secrets, Render settings, paid services, broker calls or real orders. PAPER ONLY.


## Final CI verification — code head c16ed2d3e5ab3479445b2f6e2b6944afc22fccb7

All five PR workflows completed SUCCESS:
- Integration: **566 passed in 1.71s** — run `41661857997`.
- PAPER: **26 passed in 0.13s** — run `41661857713`.
- NEWS Alert: **72 passed in 0.95s** — run `41661857745`.
- Public Event Brain: **86 passed in 0.62s** — run `41661857936`.
- Execution Layer: **3 passed in 0.02s** — run `41661858091`.
- Total: **753 tests passed**.

The tested code head is `c16ed2d3e5ab3479445b2f6e2b6944afc22fccb7`. The workflow/test change is the tested code; this log records those exact results.

Main advanced after branch creation with unrelated commit `e04b8997a9c8ae3a5eb7e34d7d99219caa32dbb0`, which makes the branch one commit behind. Its changes are limited to `.github/workflows/day-research.yml` and `GAGARIN_RESEARCH_LOG.md`; this PR changes `.github/workflows/aggressive-alert.yml`, `tests/test_aggressive_workflow_install.py`, and this separate cleanup log. GitHub currently reports the PR as not mergeable; update/rebase is required before any merge consideration. No merge was attempted.
