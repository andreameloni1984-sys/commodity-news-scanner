from engine.safety import apply_safety
from engine.state import SoyuzState


def make_state(direction):
    state = SoyuzState(commodity="Gold", symbol="XAU/USD")
    state.metadata["market_structure_check"] = {"direction": direction}
    state.setup_direction = "LONG"
    state.setup = "LONG_PULLBACK"
    return state


def test_opposite_bearish_crosscheck_blocks_long():
    state = apply_safety(make_state("BEARISH"))
    assert state.final_decision == "WAIT"
    assert "STRUCTURE_CROSSCHECK_OPPOSITE" in state.blockers


def test_opposite_bullish_crosscheck_blocks_short():
    state = make_state("BULLISH")
    state.setup_direction = "SHORT"
    state = apply_safety(state)
    assert state.final_decision == "WAIT"
    assert "STRUCTURE_CROSSCHECK_OPPOSITE" in state.blockers


def test_missing_crosscheck_does_not_create_opposite_direction_blocker():
    state = make_state("INSUFFICIENT")
    state = apply_safety(state)
    assert "STRUCTURE_CROSSCHECK_OPPOSITE" not in state.blockers
