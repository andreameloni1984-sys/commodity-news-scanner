from pathlib import Path


def test_manual_soyuz_workflow_skips_full_pytest_suite():
    workflow = Path(".github/workflows/soyuz.yml").read_text(encoding="utf-8")

    # The full suite is already run by the push/PR CI workflow. The manual
    # market run should not wait for it before starting Gagarin.
    assert "python -m pytest" not in workflow
    assert "python -m compileall -q ." in workflow
    assert "python main.py" in workflow
    assert 'PAPER_TRADING_ONLY: "1"' in workflow
