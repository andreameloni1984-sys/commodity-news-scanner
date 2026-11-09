from pathlib import Path


def test_daily_summary_uses_same_durable_feedback_store_as_monitor():
    daily_summary = Path(".github/workflows/daily-summary.yml").read_text(encoding="utf-8")
    monitor = Path(".github/workflows/gagarin-monitor.yml").read_text(encoding="utf-8")

    database_secret = "DATABASE_URL: ${{ secrets.DATABASE_URL }}"
    assert database_secret in monitor
    assert database_secret in daily_summary
    assert 'python -m pip install "requests>=2.31,<3" "psycopg[binary]>=3.2,<4"' in daily_summary


def test_daily_summary_never_reports_runner_local_csv_as_verified_history():
    daily_summary = Path(".github/workflows/daily-summary.yml").read_text(encoding="utf-8")

    assert "backend = storage_backend()" in daily_summary
    assert 'if backend != "POSTGRES":' in daily_summary
    assert "Feedback non disponibile: archivio persistente" in daily_summary
    assert "fb = summarize()" in daily_summary
