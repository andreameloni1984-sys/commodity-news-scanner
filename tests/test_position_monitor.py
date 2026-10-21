from types import SimpleNamespace

from engine import position_monitor as monitor


def state(price=97, age=10):
    return SimpleNamespace(
        symbol="XAUUSD", commodity="Oro", live=True,
        price=price, data_age_seconds=age, atr=2,
        opens=[99.5, 100.5, 101.5, 102.5, 103.5],
        closes=[100, 101, 102, 103, 104],
        highs=[101, 102, 103, 104, 105],
        lows=[99, 100, 101, 102, 103],
    )


def register(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "_POSITION_FILE", tmp_path / "positions.json")
    ok, message = monitor.register_position(
        symbol="XAUUSD", commodity="Oro", direction="LONG",
        entry=100, stop=98, tp1=105,
    )
    assert ok, message


def test_position_levels_must_match_direction(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "_POSITION_FILE", tmp_path / "positions.json")
    ok, _ = monitor.register_position(
        symbol="XAUUSD", commodity="Oro", direction="LONG",
        entry=100, stop=102, tp1=105,
    )
    assert not ok
    assert monitor.list_positions() == []


def test_stop_crossing_emits_once_until_state_recovers(monkeypatch, tmp_path):
    register(monkeypatch, tmp_path)
    first = monitor.evaluate_positions([state(price=97)])
    assert len(first) == 1
    assert "RISCHIO" in first[0]
    assert monitor.evaluate_positions([state(price=97)]) == []

    # A recovery resets the transition state; a new stop breach may alert again.
    assert monitor.evaluate_positions([state(price=101)]) == []
    second = monitor.evaluate_positions([state(price=97)])
    assert len(second) == 1


def test_stale_quotes_do_not_trigger_position_alerts(monkeypatch, tmp_path):
    register(monkeypatch, tmp_path)
    assert monitor.evaluate_positions([state(price=97, age=999)]) == []

def test_hourly_status_update_is_sent_after_one_hour(monkeypatch, tmp_path):
    register(monkeypatch, tmp_path)
    positions = monitor._read()
    position = positions["XAUUSD"]
    from datetime import datetime, timedelta, timezone
    position["last_hourly_update_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    monitor._write(positions)
    monkeypatch.setattr(
        monitor, "analyze_pattern_and_exit",
        lambda **kwargs: {"exit_action": "HOLD", "candlestick_pattern": "NONE", "pattern": "RANGE",
                          "reversal_status": "NONE", "reason": "no invalidation"},
    )

    messages = monitor.evaluate_positions([state(price=101)])
    assert len(messages) == 1
    assert "AGGIORNAMENTO ORARIO" in messages[0]
    assert "Quotazione provider: 101 USD" in messages[0]
    assert "non Trading 212 Bid/Ask" in messages[0]
    assert monitor.evaluate_positions([state(price=101)]) == []


def test_hourly_status_waits_one_hour_after_registration(monkeypatch, tmp_path):
    register(monkeypatch, tmp_path)
    monkeypatch.setattr(
        monitor, "analyze_pattern_and_exit",
        lambda **kwargs: {"exit_action": "HOLD", "candlestick_pattern": "NONE", "pattern": "RANGE",
                          "reversal_status": "NONE", "reason": "no invalidation"},
    )
    assert monitor.evaluate_positions([state(price=101)]) == []


def test_remove_position_stops_monitoring(monkeypatch, tmp_path):
    register(monkeypatch, tmp_path)
    ok, _ = monitor.remove_position("XAUUSD")
    assert ok
    assert monitor.evaluate_positions([state(price=97)]) == []
