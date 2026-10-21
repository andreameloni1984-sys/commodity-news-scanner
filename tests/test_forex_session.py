from datetime import datetime
from zoneinfo import ZoneInfo
from engine.forex_session import forex_window_open, filter_forex_for_session

ROME = ZoneInfo("Europe/Rome")

def test_forex_windows_open():
    assert forex_window_open(datetime(2026, 10, 21, 8, 0, tzinfo=ROME))
    assert forex_window_open(datetime(2026, 10, 21, 10, 59, tzinfo=ROME))
    assert forex_window_open(datetime(2026, 10, 21, 14, 0, tzinfo=ROME))
    assert forex_window_open(datetime(2026, 10, 21, 17, 59, tzinfo=ROME))

def test_forex_windows_closed_at_boundaries():
    for hour, minute in ((7, 59), (11, 0), (13, 59), (18, 0), (22, 0)):
        assert not forex_window_open(datetime(2026, 10, 21, hour, minute, tzinfo=ROME))

def test_filter_keeps_non_forex_outside_hours(monkeypatch):
    monkeypatch.delenv("GAGARIN_FOREX_ON_DEMAND", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    items = [
        type("Instrument", (), {"category": "Forex", "name": "EUR/USD"})(),
        type("Instrument", (), {"category": "Metal", "name": "Oro"})(),
    ]
    result = filter_forex_for_session(items, datetime(2026, 10, 21, 12, 0, tzinfo=ROME))
    assert [x.name for x in result] == ["Oro"]

def test_manual_run_bypasses_time_gate(monkeypatch):
    monkeypatch.setenv("GAGARIN_FOREX_ON_DEMAND", "1")
    items = [type("Instrument", (), {"category": "Forex", "name": "EUR/USD"})()]
    assert filter_forex_for_session(items, datetime(2026, 10, 21, 12, 0, tzinfo=ROME)) == items
