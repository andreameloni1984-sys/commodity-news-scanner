import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

from economic_calendar import fetch_calendar, format_calendar, messages_due


def _response(rows):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(rows).encode("utf-8")
    return response


def test_fetch_calendar_filters_and_sorts_relevant_events():
    rows = [
        {"title": "CPI y/y", "country": "USD", "date": "2026-11-10T08:30:00-05:00", "impact": "High", "forecast": "3.8%", "previous": "3.7%"},
        {"title": "Low impact speech", "country": "USD", "date": "2026-11-10T09:00:00-05:00", "impact": "Low"},
        {"title": "CPI", "country": "JPY", "date": "2026-11-10T09:00:00-05:00", "impact": "High"},
        {"title": "Retail Sales", "country": "USD", "date": "2026-11-10T07:30:00-05:00", "impact": "Medium"},
    ]
    now = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
    events = fetch_calendar(now=now, opener=lambda *a, **k: _response(rows))
    assert [event["title"] for event in events] == ["Retail Sales", "CPI y/y"]
    assert events[-1]["when"] == datetime(2026, 11, 10, 13, 30, tzinfo=timezone.utc)


def test_calendar_message_uses_rome_timezone_and_marks_impact():
    event = {
        "title": "CPI y/y", "currency": "USD", "impact": "HIGH",
        "when": datetime(2026, 11, 10, 13, 30, tzinfo=timezone.utc),
        "forecast": "3.8%", "previous": "3.7%",
    }
    message = format_calendar([event], now=datetime(2026, 11, 9, 12, tzinfo=timezone.utc))
    assert "10/11 14:30" in message
    assert "CPI y/y" in message
    assert "PAPER" not in message


def test_messages_due_sends_pre_event_only_inside_single_15_minute_window():
    now = datetime(2026, 11, 10, 13, 20, tzinfo=timezone.utc)
    event = {
        "title": "CPI y/y", "currency": "USD", "impact": "HIGH",
        "when": datetime(2026, 11, 10, 13, 30, tzinfo=timezone.utc),
        "forecast": "", "previous": "",
    }
    due = messages_due([event], now=now)
    assert len(due) == 1
    assert due[0][0] == "pre_event"
    assert "EVENTO IN ARRIVO" in due[0][1]


def test_messages_due_daily_brief_at_0700_rome():
    now = datetime(2026, 11, 10, 6, 0, tzinfo=timezone.utc)
    event = {
        "title": "CPI y/y", "currency": "USD", "impact": "HIGH",
        "when": datetime(2026, 11, 10, 13, 30, tzinfo=timezone.utc),
        "forecast": "", "previous": "",
    }
    due = messages_due([event], now=now)
    assert len(due) == 1
    assert due[0][0] == "daily"
