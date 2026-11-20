from pathlib import Path


def test_render_keepalive_targets_health_and_uses_offset_ten_minute_schedule():
    workflow = Path(".github/workflows/gagarin-render-keepalive.yml").read_text(
        encoding="utf-8"
    )

    assert 'cron: "3,13,23,33,43,53 * * * *"' in workflow
    assert "https://soyuz-gagarin-telegram-v2.onrender.com/health" in workflow
    assert "--retry 8" in workflow
    assert "--retry-all-errors" in workflow
    assert 'test "$response" = "OK"' in workflow


def test_render_keepalive_is_read_only_and_does_not_use_secrets_or_mutating_routes():
    workflow = Path(".github/workflows/gagarin-render-keepalive.yml").read_text(
        encoding="utf-8"
    )

    assert "permissions:\n  contents: read" in workflow
    assert "secrets." not in workflow
    assert "/health" in workflow
    assert "/telegram/webhook" not in workflow
