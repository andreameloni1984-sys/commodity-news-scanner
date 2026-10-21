import csv
from datetime import datetime, timezone

from engine.feedback import FIELDS, evaluate_open_signals, load_feedback


def write_signal(path, direction="LONG", entry=100, stop=98, tp1=103, tp2=104, tp3=105):
    row = {field: "" for field in FIELDS}
    row.update({
        "timestamp_utc": "2026-10-21T10:00:00+00:00",
        "symbol": "TEST",
        "direction": direction,
        "entry": entry,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "outcome": "OPEN",
        "r_multiple": "",
    })
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)


def test_tp3_closes_signal_and_calculates_r_multiple(tmp_path):
    path = tmp_path / "feedback.csv"
    write_signal(path)
    candles = {"TEST": [{
        "timestamp": "2026-10-21T10:05:00Z", "high": 106, "low": 99,
    }]}
    assert evaluate_open_signals(candles, path) == 1
    row = load_feedback(path)[0]
    assert row["outcome"] == "TP3"
    assert float(row["r_multiple"]) == 2.5
    assert row["closed_at_utc"].startswith("2026-10-21T10:05:00")
    assert evaluate_open_signals(candles, path) == 0


def test_stop_wins_if_stop_and_target_touched_in_same_candle(tmp_path):
    path = tmp_path / "feedback.csv"
    write_signal(path)
    candles = {"TEST": [{
        "timestamp": "2026-10-21T10:05:00Z", "high": 106, "low": 97,
    }]}
    assert evaluate_open_signals(candles, path) == 1
    row = load_feedback(path)[0]
    assert row["outcome"] == "STOP"
    assert float(row["r_multiple"]) == -1.0


def test_candles_before_or_at_signal_time_are_ignored(tmp_path):
    path = tmp_path / "feedback.csv"
    write_signal(path)
    candles = {"TEST": [{
        "timestamp": "2026-10-21T10:00:00Z", "high": 106, "low": 99,
    }]}
    assert evaluate_open_signals(candles, path) == 0
    assert load_feedback(path)[0]["outcome"] == "OPEN"


def test_short_stop_is_directionally_correct(tmp_path):
    path = tmp_path / "feedback.csv"
    write_signal(path, direction="SHORT", entry=100, stop=102, tp1=97, tp2=96, tp3=95)
    candles = {"TEST": [{
        "timestamp": "2026-10-21T10:05:00Z", "high": 103, "low": 94,
    }]}
    assert evaluate_open_signals(candles, path) == 1
    row = load_feedback(path)[0]
    assert row["outcome"] == "STOP"
    assert float(row["r_multiple"]) == -1.0
