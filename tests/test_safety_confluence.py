from engine.safety import apply_safety
from engine.state import SoyuzState


def _ready(**overrides) -> SoyuzState:
    state = SoyuzState(commodity="Gold", symbol="XAU/USD")
    state.data_ok = True
    state.live = True
    state.setup = "RANGE_REVERSAL"
    state.setup_direction = "LONG"
    state.trigger_confirmed = True
    state.trigger_direction = "LONG"
    state.structure_direction = "SHORT"
    state.mtf_direction = "SHORT"
    state.opportunity_type = "RANGE_REVERSAL"
    state.entry = 100.0
    state.stop = 98.0
    state.tp1 = 103.0
    state.tp2 = 104.0
    state.tp3 = 105.0
    state.stop_atr = 1.2
    state.rr1 = 1.5
    state.rr2 = 2.0
    state.rr3 = 2.5
    state.probability = 70.0
    state.quality = 70.0
    state.confidence = 70.0
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def test_range_reversal_does_not_require_mtf_match():
    state = apply_safety(_ready())
    assert "MTF_DIRECTION_MISMATCH" not in state.blockers
    assert "FINAL_CONFLUENCE_FAIL" not in state.blockers
    assert state.final_decision == "ENTRY"
    assert state.safety == "SAFE"


def test_trend_continuation_still_requires_mtf_match():
    state = apply_safety(_ready(
        opportunity_type="TREND_CONTINUATION",
        structure_direction="LONG",
        mtf_direction="SHORT",
    ))
    assert "MTF_DIRECTION_MISMATCH" in state.blockers
    assert state.final_decision == "WAIT"


def test_inverted_target_ladder_is_blocked():
    state = apply_safety(_ready(tp1=106.0, tp2=104.0, tp3=105.0))
    assert "LONG_TARGET_LADDER_INVALID" in state.blockers
    assert state.final_decision == "WAIT"
