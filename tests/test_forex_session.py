from datetime import datetime
from zoneinfo import ZoneInfo
from engine.forex_session import forex_window_open, forex_windows, filter_forex_for_session

ROME = ZoneInfo("Europe/Rome")

def test_normal_forex_windows():
    assert forex_window_open(datetime(2026, 10, 21, 8, 0, tzinfo=ROME))
    assert forex_window_open(datetime(2026, 10, 21, 10, 59, tzinfo=ROME))
    assert not forex_window_open(datetime(2026, 10, 21, 11, 0, tzinfo=ROME))
    assert not forex_window_open(datetime(2026, 10, 21, 13, 59, tzinfo=ROME))
    assert forex_window_open(datetime(2026, 10, 21, 14, 0, tzinfo=ROME))
    assert forex_window_open(datetime(2026, 10, 21, 17, 59, tzinfo=ROME))
    assert not forex_window_open(datetime(2026, 10, 21, 18, 0, tzinfo=ROME))

def test_dst_mismatch_moves_afternoon_start_to_1300():
    dt = datetime(2026, 10, 26, 13, 15, tzinfo=ROME)
    assert forex_windows(dt)[1][0] == 13 * 60
    assert forex_window_open(dt)
    spring = datetime(2027, 3, 15, 13, 15, tzinfo=ROME)
    assert forex_windows(spring)[1][0] == 13 * 60
    assert forex_window_open(spring)

def test_weekends_are_closed():
    assert not forex_window_open(datetime(2026, 10, 24, 9, 0, tzinfo=ROME))

def test_filter_keeps_non_forex_outside_hours(monkeypatch):
    monkeypatch.delenv("GAGARIN_FOREX_ON_DEMAND", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    items = [
        type("Instrument", (), {"category": "Forex", "name": "EUR/USD"})(),
        type("Instrument", (), {"category": "Metal", "name": "Oro"})(),
    ]
    result = filter_forex_for_session(items, datetime(2026, 10, 21, 12, 0, tzinfo=ROME))
    assert [x.name for x in result] == ["Oro"]

def test_explicit_on_demand_bypasses_time_gate(monkeypatch):
    monkeypatch.delenv("GAGARIN_FOREX_ON_DEMAND", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    items = [type("Instrument", (), {"category": "Forex", "name": "EUR/USD"})()]
    assert filter_forex_for_session(items, datetime(2026, 10, 21, 12, 0, tzinfo=ROME), on_demand=True) == items
