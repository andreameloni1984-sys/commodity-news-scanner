from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from engine.market_status import (
    classify_data_status,
    get_market_status,
    is_weekend,
)

UTC = timezone.utc
CHICAGO = ZoneInfo("America/Chicago")


def test_active_grain_symbols_are_closed_during_afternoon_break():
    # 2026-11-04 00:33 UTC == 2026-11-03 18:33 America/Chicago.
    timestamp = datetime(2026, 11, 4, 0, 33, tzinfo=UTC)
    for commodity in ("Grano", "Mais", "Soia"):
        assert get_market_status(commodity, timestamp) == "CLOSED"
        assert classify_data_status(
            commodity, live=False, data_ok=True, timestamp=timestamp
        ) == "MARKET_CLOSED"


def test_grains_reopen_at_1900_chicago():
    timestamp = datetime(2026, 11, 4, 1, 0, tzinfo=UTC)  # 19:00 CT
    for commodity in ("Grano", "Mais", "Soia"):
        assert get_market_status(commodity, timestamp) == "OPEN"


def test_grain_morning_break_is_closed():
    before_break = datetime(2026, 11, 4, 13, 44, tzinfo=UTC)  # 07:44 CT
    break_start = datetime(2026, 11, 4, 13, 45, tzinfo=UTC)  # 07:45 CT
    reopen = datetime(2026, 11, 4, 14, 30, tzinfo=UTC)       # 08:30 CT

    assert get_market_status("Grano", before_break) == "OPEN"
    assert get_market_status("Grano", break_start) == "CLOSED"
    assert get_market_status("Grano", reopen) == "OPEN"


def test_grain_day_session_closes_at_1320_chicago():
    before_close = datetime(2026, 11, 4, 19, 19, tzinfo=UTC)  # 13:19 CT
    at_close = datetime(2026, 11, 4, 19, 20, tzinfo=UTC)      # 13:20 CT

    assert get_market_status("Mais", before_close) == "OPEN"
    assert get_market_status("Mais", at_close) == "CLOSED"


def test_grains_do_not_reopen_friday_evening():
    friday_evening = datetime(2026, 11, 7, 1, 0, tzinfo=UTC)  # Friday 19:00 CT
    assert get_market_status("Soia", friday_evening) == "CLOSED"


def test_weekly_open_is_sunday_1900_chicago():
    before_open = datetime(2026, 11, 9, 0, 59, tzinfo=UTC)  # Sunday 18:59 CT
    at_open = datetime(2026, 11, 9, 1, 0, tzinfo=UTC)       # Sunday 19:00 CT

    assert get_market_status("Grano", before_open) == "CLOSED"
    assert get_market_status("Grano", at_open) == "OPEN"


def test_calendar_uses_chicago_dst_rules():
    # During US daylight time, Chicago is UTC-5.
    closed = datetime(2026, 7, 2, 23, 30, tzinfo=UTC)  # 18:30 CDT
    opened = datetime(2026, 7, 3, 0, 0, tzinfo=UTC)    # 19:00 CDT

    assert get_market_status("Grano", closed) == "CLOSED"
    assert get_market_status("Grano", opened) == "OPEN"


def test_non_grain_commodity_status_is_not_changed_by_grain_break():
    timestamp = datetime(2026, 11, 4, 0, 33, tzinfo=UTC)  # 18:33 CT
    assert get_market_status("Oro", timestamp) == "OPEN"
    assert classify_data_status(
        "Oro", live=False, data_ok=True, timestamp=timestamp
    ) == "STALE"


def test_market_closed_is_not_data_error_and_data_error_keeps_priority():
    timestamp = datetime(2026, 11, 4, 0, 33, tzinfo=UTC)

    assert classify_data_status(
        "Grano", live=True, data_ok=True, timestamp=timestamp
    ) == "MARKET_CLOSED"
    assert classify_data_status(
        "Grano", live=False, data_ok=False, timestamp=timestamp
    ) == "DATA_ERROR"


def test_weekend_check_is_timezone_independent():
    sunday_evening_chicago = datetime(2026, 11, 8, 19, 0, tzinfo=CHICAGO)
    assert not is_weekend(sunday_evening_chicago)
