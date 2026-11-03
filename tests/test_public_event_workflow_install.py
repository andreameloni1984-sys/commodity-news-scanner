from pathlib import Path


def test_public_event_brain_workflow_installs_test_dependencies_without_pip_upgrade():
    workflow = Path(".github/workflows/public-event-brain-tests.yml").read_text()

    assert "actions/setup-python@v5" in workflow
    assert 'python-version: "3.12"' in workflow
    assert "python -m pip install pytest requests" in workflow
    assert "python -m pip install --upgrade pip" not in workflow
    assert "python -m pytest -q tests/test_public_event_brain.py" in workflow
