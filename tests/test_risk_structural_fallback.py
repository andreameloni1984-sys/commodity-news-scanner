from engine.risk import apply_risk
from engine.state import SoyuzState


def make_state(direction, *, price=100.0, atr=1.0, swing=None):
    state = SoyuzState(commodity="TEST", symbol="TEST/USD")
    state.price = price
    state.atr = atr
    state.setup_direction = direction
    if direction == "LONG":
        state.last_swing_low = swing
    else:
        state.last_swing_high = swing
    return state


def assert_targets_and_rr(state):
    assert state.entry == 100.0
    assert state.stop is not None
    assert state.tp1 is not None
    assert state.tp2 is not None
    assert state.tp3 is not None
    assert state.rr1 == 1.5
    assert state.rr2 == 2.0
    assert state.rr3 == 2.5
    assert 0.8 <= state.stop_atr <= 2.5
    assert state.metadata["risk_diagnostics"]["status"] == "RISK_VALID"


def test_long_tight_structural_stop_uses_atr_fallback_and_builds_targets():
    # stop = 99.75, only 0.25 ATR from entry
    state = apply_risk(make_state("LONG", swing=99.90))
    assert_targets_and_rr(state)
    assert state.metadata["risk_diagnostics"]["stop_source"] == "ATR_FALLBACK_TIGHT_STRUCTURE"
    assert state.metadata["risk_diagnostics"]["structural_stop"] == 99.75
    assert state.stop == 98.8


def test_short_tight_structural_stop_uses_atr_fallback_and_builds_targets():
    # stop = 100.25, only 0.25 ATR from entry
    state = apply_risk(make_state("SHORT", swing=100.10))
    assert_targets_and_rr(state)
    assert state.metadata["risk_diagnostics"]["stop_source"] == "ATR_FALLBACK_TIGHT_STRUCTURE"
    assert state.metadata["risk_diagnostics"]["structural_stop"] == 100.25
    assert state.stop == 101.2


def test_long_wide_structural_stop_uses_atr_fallback_and_builds_targets():
    state = apply_risk(make_state("LONG", swing=96.0))
    assert_targets_and_rr(state)
    assert state.metadata["risk_diagnostics"]["stop_source"] == "ATR_FALLBACK_WIDE_STRUCTURE"
    assert state.metadata["risk_diagnostics"]["structural_stop"] == 95.85
    assert state.stop == 98.8


def test_short_wide_structural_stop_uses_atr_fallback_and_builds_targets():
    state = apply_risk(make_state("SHORT", swing=104.0))
    assert_targets_and_rr(state)
    assert state.metadata["risk_diagnostics"]["stop_source"] == "ATR_FALLBACK_WIDE_STRUCTURE"
    assert state.metadata["risk_diagnostics"]["structural_stop"] == 104.15
    assert state.stop == 101.2


def test_missing_structure_uses_atr_fallback_and_builds_targets():
    state = apply_risk(make_state("LONG"))
    assert_targets_and_rr(state)
    assert state.metadata["risk_diagnostics"]["stop_source"] == "ATR_FALLBACK"
