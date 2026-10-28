from datetime import datetime, timedelta, timezone

from telegram.news_monitor import build_alert_scorecard


def test_scorecard_marks_same_timestamp_stop_and_tp_as_ambiguous_independent_of_row_order():
    sent = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
    alert = {
        "kind": "NEWS_ALERT_SENT",
        "event_id": "same-time-barriers",
        "asset": "WTI",
        "direction": "LONG",
        "price": 80.0,
        "stop": 79.0,
        "tp1": 81.0,
        "sent_at": sent.isoformat(),
    }
    stop_row = {
        "kind": "NEWS_REACTION",
        "event_id": "same-time-barriers",
        "asset": "WTI",
        "current_price": 78.8,
        "observed_at": (sent + timedelta(minutes=20)).isoformat(),
    }
    target_row = {
        "kind": "NEWS_REACTION",
        "event_id": "same-time-barriers",
        "asset": "WTI",
        "current_price": 81.2,
        "observed_at": (sent + timedelta(minutes=20)).isoformat(),
    }
    later_row = {
        "kind": "NEWS_REACTION",
        "event_id": "same-time-barriers",
        "asset": "WTI",
        "current_price": 80.5,
        "observed_at": (sent + timedelta(minutes=30)).isoformat(),
    }

    reports = [
        build_alert_scorecard([alert, stop_row, target_row, later_row], now=sent + timedelta(hours=1)),
        build_alert_scorecard([alert, target_row, stop_row, later_row], now=sent + timedelta(hours=1)),
    ]

    for report in reports:
        assert report["alerts"] == 1
        assert report["scored"] == 1
        assert report["ambiguous_barrier_observations"] == 1
        assert report["sl_observed"] == 0
        assert report["tp1_observed"] == 0
        assert report["open_at_last_check"] == 0

    assert reports[0]["ambiguous_barrier_observations"] == reports[1]["ambiguous_barrier_observations"]
