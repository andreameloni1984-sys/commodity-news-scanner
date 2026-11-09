from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gagarin_runtime_does_not_poll_trading212():
    runner = (ROOT / "telegram" / "render_runner.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "soyuz.yml").read_text(encoding="utf-8")

    assert "invest_auto_loop" not in runner
    assert "Trading212" not in runner
    assert "T212_AUTO_BUY_ENABLED" not in runner
    assert "T212_API_KEY" not in workflow
    assert "T212_API_SECRET" not in workflow
