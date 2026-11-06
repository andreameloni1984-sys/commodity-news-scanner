import subprocess
import sys
from pathlib import Path


def test_legacy_restore_script_is_inert_and_cannot_write_to_main():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "restore_and_patch_bot.py"
    source = script.read_text(encoding="utf-8")

    for forbidden in (
        "api.github.com/repos",
        "GH_TOKEN",
        "TOKEN",
        "FOREX_AGGRESSIVE_PORTFOLIO",
        "engine.trading212",
        "compare_price",
        "parse_bid_ask",
        "BRANCH = \"main\"",
    ):
        assert forbidden not in source

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "DISABLED" in result.stdout
    assert "main" in result.stdout
