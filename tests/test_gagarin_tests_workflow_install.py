from pathlib import Path


def test_gagarin_test_workflow_keeps_dependencies_and_tests_without_pip_self_upgrade():
    workflow = Path(".github/workflows/gagarin-tests.yml").read_text(encoding="utf-8")

    assert "python -m pip install -r requirements.txt" in workflow
    assert "python -m pytest -q" in workflow
    assert "python -m pip install --upgrade pip" not in workflow
    assert "pip install --upgrade pip" not in workflow
