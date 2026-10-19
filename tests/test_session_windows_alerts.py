from datetime import datetime
from zoneinfo import ZoneInfo

from engine.session_windows import current_window, is_eia_window, is_overlap
from telegram.aggressive_alert import format_aggressive_alert

ROME = ZoneInfo("Europe/Rome")


def test_week_key_and_overlap_do_not_raise_name_error():
    now = datetime(2026, 10, 19, 16, 0, tzinfo=ROME)
    assert current_window(now)["overlap"] == (15, 0, 19, 0)
    assert is_overlap(now) is True


def test_eia_window_handles_minute_rollover():
    before = datetime(2026, 10, 21, 16, 20, tzinfo=ROME)
    inside = datetime(2026, 10, 21, 16, 45, tzinfo=ROME)
    after = datetime(2026, 10, 21, 17, 16, tzinfo=ROME)
    assert is_eia_window(before) is True
    assert is_eia_window(inside) is True
    assert is_eia_window(after) is False


def test_eia_window_uses_next_week_schedule_without_invalid_time():
    # From 2 November the configured EIA time is 15:30; boundaries cross no invalid minute.
    before = datetime(2026, 11, 4, 15, 15, tzinfo=ROME)
    after = datetime(2026, 11, 4, 16, 16, tzinfo=ROME)
    assert is_eia_window(before) is True
    assert is_eia_window(after) is False


def test_aggressive_alert_formatter_survives_session_annotation(monkeypatch):
    monkeypatch.setattr("telegram.aggressive_alert.is_overlap", lambda: True)
    monkeypatch.setattr("telegram.aggressive_alert.is_eia_window", lambda: False)
    state = type("State", (), {
        "commodity": "Gold", "symbol": "XAUUSD", "setup_direction": "LONG",
        "opportunity_direction": "LONG", "probability": 42, "quality": 32,
        "confidence": 30, "trigger_confirmed": False, "live": True,
        "final_decision": "WATCH", "entry": 2700, "stop": 2680, "tp1": 2740,
        "tp2": 2760, "tp3": None, "price": 2710, "atr": 10,
        "closes": [2680, 2690, 2695, 2702, 2710],
        "highs": [2685, 2695, 2700, 2705, 2712],
        "lows": [2670, 2680, 2688, 2695, 2701],
    })()
    message = format_aggressive_alert([state])
    assert "POSSIBILE OPPORTUNITÀ" in message
    assert "Pattern:" in message
    assert "Gestione/uscita:" in message
    assert "Sessione: overlap attivo" in message
    assert "PAPER ONLY" in message
