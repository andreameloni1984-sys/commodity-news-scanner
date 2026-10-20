from types import SimpleNamespace

import engine.pattern_exit as pattern_exit
import telegram.aggressive_alert as aggressive_alert


def test_long_stop_invalidated_with_insufficient_ohlc():
    result = pattern_exit.analyze_pattern_and_exit(
        direction="LONG", closes=[100, 99, 98, 97], stop=95, tp1=110,
        current_price=94,
    )
    assert result["stop_invalidated"] is True
    assert result["target_reached"] is False
    assert result["exit_action"] == "EXIT_WARNING"


def test_short_stop_invalidated_with_insufficient_ohlc():
    result = pattern_exit.analyze_pattern_and_exit(
        direction="SHORT", closes=[100, 101, 102, 103], stop=105, tp1=90,
        current_price=106,
    )
    assert result["stop_invalidated"] is True
    assert result["target_reached"] is False
    assert result["exit_action"] == "EXIT_WARNING"


def test_long_stop_invalidated_with_five_closes():
    result = pattern_exit.analyze_pattern_and_exit(
        direction="LONG", opens=[101, 100, 99, 98, 97],
        closes=[100, 99, 98, 97, 96], highs=[102, 101, 100, 99, 98],
        lows=[99, 98, 97, 96, 95], stop=95, tp1=110, atr=2,
        current_price=94.5,
    )
    assert result["stop_invalidated"] is True
    assert result["exit_action"] == "EXIT_WARNING"


def test_short_stop_invalidated_with_five_closes():
    result = pattern_exit.analyze_pattern_and_exit(
        direction="SHORT", opens=[99, 100, 101, 102, 103],
        closes=[100, 101, 102, 103, 104], highs=[101, 102, 103, 104, 105],
        lows=[98, 99, 100, 101, 102], stop=105, tp1=90, atr=2,
        current_price=105.5,
    )
    assert result["stop_invalidated"] is True
    assert result["exit_action"] == "EXIT_WARNING"


def test_long_tp1_reached_with_insufficient_ohlc():
    result = pattern_exit.analyze_pattern_and_exit(
        direction="LONG", closes=[100, 101, 102], stop=95, tp1=105,
        current_price=105,
    )
    assert result["target_reached"] is True
    assert result["stop_invalidated"] is False
    assert result["exit_action"] == "TAKE_PROFIT_WATCH"


def test_pattern_analysis_is_calculated_once_per_alert(monkeypatch):
    calls = []
    real_analyze = aggressive_alert.analyze_pattern_and_exit

    def counted(**kwargs):
        calls.append(kwargs)
        return real_analyze(**kwargs)

    monkeypatch.setattr(aggressive_alert, "analyze_pattern_and_exit", counted)
    state = SimpleNamespace(
        commodity="Test", symbol="TEST", setup_direction="LONG",
        opportunity_direction="LONG", probability=70, quality=60,
        confidence=60, trigger_confirmed=True, live=True,
        final_decision="PAPER_ENTRY", entry=100, stop=90, tp1=120,
        tp2=130, tp3=140, price=95, data_age_seconds=1,
        price_timestamp="2026-10-20T07:00:00Z", atr=2,
        opens=[101, 100, 99, 98, 97], closes=[100, 99, 98, 97, 96],
        highs=[102, 101, 100, 99, 98], lows=[99, 98, 97, 96, 95],
    )
    alerts = aggressive_alert.find_aggressive_alerts([state])
    assert len(calls) == 1
    assert len(alerts) == 1



def test_provider_price_beyond_long_stop_cannot_be_confirmed():
    state = SimpleNamespace(
        commodity="LONG stop", symbol="LONG_TEST", setup_direction="LONG",
        opportunity_direction="LONG", probability=80, quality=70,
        confidence=70, trigger_confirmed=True, live=True,
        final_decision="PAPER_ENTRY", entry=100, stop=95, tp1=110,
        tp2=115, tp3=120, price=94, data_age_seconds=1,
        price_timestamp="2026-10-20T07:00:00Z", atr=2,
        opens=[], closes=[100, 99, 98], highs=[], lows=[],
    )
    alerts = aggressive_alert.find_aggressive_alerts([state])
    assert len(alerts) == 1
    assert alerts[0]["stage"] == "RISCHIO"
    message = aggressive_alert.format_aggressive_alerts(alerts)
    assert "Stop superato sul prezzo provider: SÌ" in message
    assert "Prezzo broker non acquisito" in message


def test_provider_price_beyond_short_stop_cannot_be_confirmed():
    state = SimpleNamespace(
        commodity="SHORT stop", symbol="SHORT_TEST", setup_direction="SHORT",
        opportunity_direction="SHORT", probability=80, quality=70,
        confidence=70, trigger_confirmed=True, live=True,
        final_decision="PAPER_ENTRY", entry=100, stop=105, tp1=90,
        tp2=85, tp3=80, price=106, data_age_seconds=1,
        price_timestamp="2026-10-20T07:00:00Z", atr=2,
        opens=[], closes=[100, 101, 102], highs=[], lows=[],
    )
    alerts = aggressive_alert.find_aggressive_alerts([state])
    assert len(alerts) == 1
    assert alerts[0]["stage"] == "RISCHIO"
    message = aggressive_alert.format_aggressive_alerts(alerts)
    assert "Stop superato sul prezzo provider: SÌ" in message
    assert "Prezzo broker non acquisito" in message
