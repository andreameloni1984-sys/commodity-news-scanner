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
    assert result[0]["stage"] == "EARLY WATCH"
    assert result[0]["direction"] == "LONG"
    assert result[0]["score"] > 40

def test_selector_does_not_require_entry():
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
    result = select_anticipation([state])
    assert result
    assert result[0]["stage"] == "EARLY WATCH"
