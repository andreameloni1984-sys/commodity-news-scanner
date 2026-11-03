from pathlib import Path


def test_private_paper_journals_and_atomic_temps_are_gitignored():
    root = Path(__file__).resolve().parents[1]
    rules = (root / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/paper_trade_log.csv" in rules
    assert "/gagarin_feedback.csv" in rules
    assert "/.paper_trade_log.csv.*.tmp" in rules
