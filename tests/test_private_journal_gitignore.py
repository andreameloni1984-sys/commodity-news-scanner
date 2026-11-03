from pathlib import Path


def test_private_paper_journals_and_atomic_temps_are_gitignored():
    root = Path(__file__).resolve().parents[1]
    rules = (root / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/paper_trade_log.csv" in rules
    assert "/gagarin_feedback.csv" in rules
    assert "/.paper_trade_log.csv.*.tmp" in rules


def test_scheduled_paper_monitor_cannot_publish_private_journals():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "gagarin-monitor.yml").read_text(
        encoding="utf-8"
    )

    assert "permissions:\n  contents: read" in workflow
    assert 'PAPER_TRADING_ONLY: "1"' in workflow
    assert "git add" not in workflow
    assert "git commit" not in workflow
    assert "git push" not in workflow
