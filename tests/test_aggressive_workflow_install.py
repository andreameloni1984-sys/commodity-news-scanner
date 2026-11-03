from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "aggressive-alert.yml"


def test_aggressive_workflow_uses_setup_python_pip_without_self_upgrade():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "uses: actions/setup-python@v5" in text
    assert 'cache: "pip"' in text
    assert "pip install -r requirements.txt" in text
    assert "python -m pip install --upgrade pip" not in text


def test_aggressive_workflow_keeps_runtime_checks_and_paper_only_execution():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert 'PAPER_TRADING_ONLY: "1"' in text
    assert "python -m compileall -q engine telegram" in text
    assert "python -c \"import main;" in text
    assert "python -m pytest -q tests/test_news_monitor.py tests/test_sputnik_item_intelligence.py" in text
    assert "python - <<'PY'" in text
    assert "run_aggressive_alert(states)" in text
