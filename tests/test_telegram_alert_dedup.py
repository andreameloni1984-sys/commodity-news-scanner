from types import SimpleNamespace

from telegram.alert_dedup import (
    select_new_signals,
    mark_sent,
    signal_fingerprint,
)


def signal(**overrides):
    values = {
        "symbol": "XAU/USD",
        "setup_direction": "LONG",
        "setup": "BREAKOUT",
        "trigger": "CONFIRMED",
        "entry": 2650.0,
        "stop": 2635.0,
        "tp1": 2672.5,
        "tp2": 2680.0,
        "tp3": 2690.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_new_signal_is_selected(tmp_path, monkeypatch):
    monkeypatch.setenv("GAGARIN_ALERT_STATE_FILE", str(tmp_path / "state.json"))
    item = signal()
    assert select_new_signals([item], now=1000) == [item]


def test_same_signal_is_suppressed_after_successful_send(tmp_path, monkeypatch):
    monkeypatch.setenv("GAGARIN_ALERT_STATE_FILE", str(tmp_path / "state.json"))
    item = signal()

    mark_sent([item], now=1000)

    assert select_new_signals([item], now=1001) == []


def test_material_level_change_creates_new_fingerprint(tmp_path, monkeypatch):
    monkeypatch.setenv("GAGARIN_ALERT_STATE_FILE", str(tmp_path / "state.json"))
    first = signal()
    changed = signal(entry=2660.0)

    mark_sent([first], now=1000)

    assert signal_fingerprint(first) != signal_fingerprint(changed)
    assert select_new_signals([changed], now=1001) == [changed]


def test_same_signal_can_alert_again_after_cooldown(tmp_path, monkeypatch):
    monkeypatch.setenv("GAGARIN_ALERT_STATE_FILE", str(tmp_path / "state.json"))
    item = signal()

    mark_sent([item], now=1000)

    assert select_new_signals([item], now=1000 + 12 * 60 * 60) == [item]
