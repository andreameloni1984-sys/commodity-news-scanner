from types import SimpleNamespace
from engine.selector import select_anticipation


def test_selector_prefers_coherent_direction():
    state = SimpleNamespace(
        commodity="Oro", symbol="XAU/USD",
        regime="TREND_UP", structure="BULLISH",
        structure_direction="LONG", mtf_direction="LONG",
        mtf_alignment=80, setup_direction="LONG",
        breakout=True, breakout_direction="LONG",
        retest=False, retest_direction="NONE",
        trigger_confirmed=False, final_decision="WAIT",
        live=True, closes=[100 + i for i in range(60)],
        blockers=[], metadata={}
    )
    result = select_anticipation([state])
    assert result[0]["commodity"] == "Oro"
    assert result[0]["stage"] == "EARLY WARNING"
    assert result[0]["direction"] == "LONG"
    assert result[0]["score"] > 40


def test_selector_does_not_invent_direction_without_evidence():
    state = SimpleNamespace(
        commodity="Petrolio WTI", symbol="WTI/USD",
        regime="UNKNOWN", structure="RANGE",
        structure_direction="NONE", mtf_direction="NONE",
        mtf_alignment=0, setup_direction="NONE",
        breakout=False, breakout_direction="NONE",
        retest=False, retest_direction="NONE",
        trigger_confirmed=False, final_decision="WAIT",
        live=True, closes=[100 + ((-1) ** i) for i in range(60)],
        blockers=[], metadata={}
    )
    import engine.selector as module
    module._forecast_map = lambda: {}
    module._weather_map = lambda: {}

    result = select_anticipation([state])
    # Price history alone must not force a default LONG on an empty forecast.
    assert result == []


def test_selector_marks_short_as_late_when_recent_move_is_extended():
    state = SimpleNamespace(
        commodity="Argento", symbol="XAGUSD",
        regime="TREND_DOWN", structure="BEARISH",
        structure_direction="SHORT", mtf_direction="SHORT",
        mtf_alignment=80, setup_direction="SHORT",
        breakout=False, breakout_direction="NONE",
        retest=False, retest_direction="NONE",
        trigger_confirmed=False, final_decision="WAIT",
        live=True, closes=[100 - i * 0.1 for i in range(60)],
        move_4h_pct=-3.2,
        blockers=[], metadata={"late_move_threshold_pct": 2.5},
    )
    import engine.selector as module
    module._forecast_map = lambda: {}
    module._weather_map = lambda: {}

    result = select_anticipation([state])
    assert result
    assert result[0]["direction"] == "SHORT"
    assert result[0]["stage"] == "LATE SHORT"
    assert any("ingresso tardivo" in item for item in result[0]["blockers"])
