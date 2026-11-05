from datetime import datetime
from zoneinfo import ZoneInfo

from engine.forex_session import (
    forex_window_open,
    forex_windows,
    filter_forex_for_session,
)

ROME = ZoneInfo("Europe/Rome")


def test_forex_is_scanned_at_any_intraday_hour_on_weekdays():
    for hour, minute in ((0, 5), (7, 59), (11, 0), (13, 15), (18, 0), (22, 45)):
        assert forex_window_open(datetime(2026, 10, 21, hour, minute, tzinfo=ROME))


def test_legacy_liquidity_windows_are_descriptive_only():
    assert forex_windows(datetime(2026, 10, 21, 12, 0, tzinfo=ROME)) == (
        (8 * 60, 11 * 60), (14 * 60, 18 * 60)
    )


def test_weekends_remain_closed_for_automatic_forex_scans():
    assert not forex_window_open(datetime(2026, 10, 24, 9, 0, tzinfo=ROME))


def test_filter_keeps_forex_outside_former_hours_on_weekdays(monkeypatch):
    monkeypatch.delenv("GAGARIN_FOREX_ON_DEMAND", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    items = [
        type("Instrument", (), {"category": "Forex", "name": "EUR/USD"})(),
        type("Instrument", (), {"category": "Metal", "name": "Oro"})(),
    ]
    result = filter_forex_for_session(items, datetime(2026, 10, 21, 12, 0, tzinfo=ROME))
    assert [x.name for x in result] == ["EUR/USD", "Oro"]


def test_automatic_filter_excludes_forex_only_on_weekends(monkeypatch):
    monkeypatch.delenv("GAGARIN_FOREX_ON_DEMAND", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    items = [
        type("Instrument", (), {"category": "Forex", "name": "EUR/USD"})(),
        type("Instrument", (), {"category": "Metal", "name": "Oro"})(),
    ]
    result = filter_forex_for_session(items, datetime(2026, 10, 24, 9, 0, tzinfo=ROME))
    assert [x.name for x in result] == ["Oro"]


def test_explicit_on_demand_bypasses_weekend_market_calendar(monkeypatch):
    monkeypatch.delenv("GAGARIN_FOREX_ON_DEMAND", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    items = [type("Instrument", (), {"category": "Forex", "name": "EUR/USD"})()]
    assert filter_forex_for_session(
        items, datetime(2026, 10, 24, 9, 0, tzinfo=ROME), on_demand=True
    ) == items
