from datetime import datetime, timedelta, timezone

from telegram.news_monitor import build_alert_scorecard


def test_scorecard_uses_first_chronological_barrier_hit_not_storage_order():
    sent = datetime(2026, 10, 28, 14, 0, tzinfo=timezone.utc)
    rows = [
        {
            "kind": "NEWS_ALERT_SENT",
            "event_id": "out-of-order",
            "asset": "WTI",
            "direction": "LONG",
            "price": 80.0,
            "stop": 79.0,
            "tp1": 81.0,
            "sent_at": sent.isoformat(),
        },
        # Deliberately return the later TP observation before the earlier SL.
        {
            "kind": "NEWS_REACTION",
            "event_id": "out-of-order",
            "asset": "WTI",
            "current_price": 81.2,
            "observed_at": (sent + timedelta(minutes=40)).isoformat(),
        },
        {
            "kind": "NEWS_REACTION",
            "event_id": "out-of-order",
            "asset": "WTI",
            "current_price": 78.8,
            "observed_at": (sent + timedelta(minutes=20)).isoformat(),
        },
    ]

    report = build_alert_scorecard(rows, now=sent + timedelta(hours=1))

    assert report["scored"] == 1
    assert report["sl_observed"] == 1
    assert report["tp1_observed"] == 0
