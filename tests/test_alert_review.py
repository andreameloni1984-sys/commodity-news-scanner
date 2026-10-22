import csv
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from engine.feedback import (
    assign_alert_ids,
    record_sent_alerts,
    pending_alert_reviews,
    review_alert,
    format_alert_review,
    FIELDS,
    update_open_outcomes,
)
from engine.alert_review_scheduler import daily_alert_review_tick


def test_sent_alerts_are_recorded_once_and_manual_verdict_is_persistent(tmp_path):
    path = tmp_path / "feedback.csv"
    alerts = [{
        "symbol": "XAUUSD",
        "commodity": "Oro",
        "direction": "LONG",
        "stage": "CONFERMATA",
        "price": 2700.5,
        "entry": 2701,
        "stop": 2690,
        "tp1": 2720,
        "probability": 80,
        "quality": 70,
        "confidence": 75,
    }]
    assign_alert_ids(alerts, now=datetime(2026, 10, 20, 19, 0, tzinfo=ZoneInfo("UTC")))
    alert_id = alerts[0]["alert_id"]

    assert record_sent_alerts(alerts, path=path) == 1
    assert record_sent_alerts(alerts, path=path) == 0
    assert len(pending_alert_reviews(path=path)) == 1

    ok, message = review_alert(alert_id[:6], "ESATTO", path=path)
    assert ok is True
    assert alert_id in message
    assert pending_alert_reviews(path=path) == []
    assert "valutati: 1" in format_alert_review(path=path, day="2026-10-20")


def test_review_rejects_invalid_or_ambiguous_verdict(tmp_path):
    path = tmp_path / "feedback.csv"
    alerts = [
        {"symbol": "XAUUSD", "direction": "LONG", "stage": "POSSIBILE", "price": 2700},
        {"symbol": "WTI", "direction": "SHORT", "stage": "POSSIBILE", "price": 75},
    ]
    assign_alert_ids(alerts, now=datetime(2026, 10, 20, 19, 0, tzinfo=ZoneInfo("UTC")))
    record_sent_alerts(alerts, path=path)

    ok, message = review_alert("BAD-ID", "ESATTO", path=path)
    assert ok is False
    assert "non trovato" in message.lower()

    ok, message = review_alert(alerts[0]["alert_id"], "MAYBE", path=path)
    assert ok is False
    assert "non valida" in message.lower()


def test_nightly_review_sends_once_at_21_italy_and_never_in_tests_by_itself(tmp_path):
    marker = tmp_path / "schedule.json"
    now = datetime(2026, 10, 20, 21, 5, tzinfo=ZoneInfo("Europe/Rome"))
    sent = []

    assert daily_alert_review_tick(sent.append and (lambda message: sent.append(message) or True),
                                   now=now, marker_path=marker) is True
    assert len(sent) == 1
    assert "SONDAGGIO ALERT" in sent[0]
    assert daily_alert_review_tick(lambda message: True, now=now, marker_path=marker) is False
    outside = datetime(2026, 10, 20, 20, 55, tzinfo=ZoneInfo("Europe/Rome"))
    assert daily_alert_review_tick(lambda message: True, now=outside,
                                   marker_path=tmp_path / "other.json") is False



def test_forward_outcome_resolves_with_only_tp1(tmp_path):
    path = tmp_path / "feedback.csv"
    row = {field: "" for field in FIELDS}
    row.update({
        "signal_id": "one-target",
        "symbol": "XAUUSD",
        "direction": "LONG",
        "entry": "100",
        "stop": "90",
        "tp1": "110",
        "tp2": "",
        "tp3": "",
        "entry_bar_timestamp": "100",
        "last_checked_timestamp": "100",
        "outcome": "OPEN",
        "r_multiple": "",
    })
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)

    state = SimpleNamespace(
        symbol="XAUUSD",
        candles=[
            {"timestamp": 100, "high": 101, "low": 99},
            {"timestamp": 200, "high": 112, "low": 105},
        ],
    )
    assert update_open_outcomes([state], path=path) == 1
    with path.open("r", newline="", encoding="utf-8") as handle:
        saved = next(csv.DictReader(handle))
    assert saved["outcome"] == "TP1"
    assert float(saved["r_multiple"]) == 1.0
    assert saved["last_checked_timestamp"] == "200"


def test_forward_outcome_rejects_malformed_supplied_optional_target(tmp_path):
    path = tmp_path / "feedback.csv"
    row = {field: "" for field in FIELDS}
    row.update({
        "signal_id": "bad-target",
        "symbol": "XAUUSD",
        "direction": "LONG",
        "entry": "100",
        "stop": "90",
        "tp1": "110",
        "tp2": "not-a-price",
        "tp3": "",
        "entry_bar_timestamp": "100",
        "outcome": "OPEN",
    })
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)
    state = SimpleNamespace(
        symbol="XAUUSD",
        candles=[
            {"timestamp": 100, "high": 101, "low": 99},
            {"timestamp": 200, "high": 112, "low": 105},
        ],
    )
    assert update_open_outcomes([state], path=path) == 0
