from datetime import datetime, timezone

from engine.market_status import classify_data_status, get_market_status


def test_sunday_evening_chicago_is_open():
    # 2026-10-11 22:30 UTC = 17:30 CT, Globex already open.
    stamp = datetime(2026, 10, 11, 22, 30, tzinfo=timezone.utc)
    assert get_market_status("Oro", stamp) == "OPEN"


def test_saturday_is_closed():
    stamp = datetime(2026, 10, 10, 15, 0, tzinfo=timezone.utc)
    assert get_market_status("Petrolio WTI", stamp) == "CLOSED"
    assert classify_data_status("Petrolio WTI", True, True, stamp) == "MARKET_CLOSED"


def test_weekday_maintenance_is_closed():
    # 2026-10-07 21:30 UTC = 16:30 CT.
    stamp = datetime(2026, 10, 7, 21, 30, tzinfo=timezone.utc)
    assert get_market_status("Cacao", stamp) == "CLOSED"


def test_weekday_session_is_open():
    stamp = datetime(2026, 10, 7, 15, 0, tzinfo=timezone.utc)
    assert get_market_status("Caffè", stamp) == "OPEN"
