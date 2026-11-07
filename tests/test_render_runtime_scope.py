from pathlib import Path


def test_render_runner_starts_only_the_news_monitor_background_worker():
    source = Path("telegram/render_runner.py").read_text(encoding="utf-8")
    assert "target=news_monitor_loop" in source
    assert "target=invest_auto_loop" not in source
    assert "target=position_monitor_loop" not in source


def test_render_runner_has_no_legacy_broker_or_position_routes():
    source = Path("telegram/render_runner.py").read_text(encoding="utf-8").lower()
    for obsolete in ("trading212", "invest_auto", "/mt5/paper", "position_monitor", "/monitora", "/posizioni"):
        assert obsolete not in source


def test_render_runner_registers_only_direction_and_calendar_commands():
    source = Path("telegram/render_runner.py").read_text(encoding="utf-8")
    for command in ('"command": "classifica"', '"command": "analisi"', '"command": "calendario"'):
        assert command in source
    assert '"command": "aggressivo212"' not in source
