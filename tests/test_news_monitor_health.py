from datetime import datetime, timedelta, timezone

import telegram.news_monitor as monitor


def test_news_monitor_health_is_starting_before_first_success(monkeypatch):
    started = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(monitor, "POLL_SECONDS", 60)
    monkeypatch.setattr(monitor, "_MONITOR_STARTED_AT", started)
    monkeypatch.setattr(monitor, "_MONITOR_LAST_SUCCESS_AT", None)

    report = monitor.news_monitor_health(now=started + timedelta(seconds=30))

    assert report["status"] == "STARTING"
    assert report["last_success_at"] is None
    assert report["stale_after_seconds"] == 180


def test_news_monitor_health_turns_stale_after_missing_poll_heartbeats(monkeypatch):
    started = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)
    last_success = started + timedelta(seconds=60)
    monkeypatch.setattr(monitor, "POLL_SECONDS", 60)
    monkeypatch.setattr(monitor, "_MONITOR_STARTED_AT", started)
    monkeypatch.setattr(monitor, "_MONITOR_LAST_SUCCESS_AT", last_success)

    healthy = monitor.news_monitor_health(now=last_success + timedelta(seconds=179))
    stale = monitor.news_monitor_health(now=last_success + timedelta(seconds=181))

    assert healthy["status"] == "OK"
    assert stale["status"] == "STALE"
    assert stale["age_seconds"] == 181
