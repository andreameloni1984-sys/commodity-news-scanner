import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_script(relative_path):
    return subprocess.run(
        [sys.executable, str(ROOT / relative_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_legacy_restore_script_is_inert_and_cannot_write_to_main():
    assert not (ROOT / "engine" / "trading212.py").exists()
    source = (ROOT / "scripts" / "restore_and_patch_bot.py").read_text(encoding="utf-8")

    for forbidden in (
        "api.github.com/repos",
        "GH_TOKEN",
        "TOKEN",
        "FOREX_AGGRESSIVE_PORTFOLIO",
        "engine.trading212",
        "compare_price",
        "parse_bid_ask",
        'BRANCH = "main"',
    ):
        assert forbidden not in source

    result = _run_script("scripts/restore_and_patch_bot.py")
    assert result.returncode == 2
    assert "DISABLED" in result.stdout
    assert "main" in result.stdout


def test_legacy_forex_patch_script_is_inert():
    source = (ROOT / "scripts" / "patch_forex_aggressive.py").read_text(encoding="utf-8")
    assert "_format_forex_aggressive" not in source
    assert "telegram/bot.py" not in source
    result = _run_script("scripts/patch_forex_aggressive.py")
    assert result.returncode == 2
    assert "DISABLED" in result.stdout


def test_legacy_direct_push_workflows_are_read_only_and_retired():
    workflow_dir = ROOT / ".github" / "workflows"
    for filename in ("restore-bot.yml", "restore-bot-py.yml", "patch-forex.yml"):
        source = (workflow_dir / filename).read_text(encoding="utf-8")
        assert "contents: read" in source
        assert "contents: write" not in source
        assert "git push" not in source
        assert "secrets.GH_TOKEN" not in source
        assert "DISABLED:" in source
