from datetime import datetime, timezone

from engine.contract_roll import apply_roll_block, roll_blocker
from engine.state import SoyuzState


def test_wti_mid_month_is_blocked():
    stamp = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
    assert roll_blocker("WTI/USD", stamp) == "CONTRACT_ROLL_WINDOW"


def test_wti_outside_window_is_clear():
    stamp = datetime(2026, 10, 8, 15, 0, tzinfo=timezone.utc)
    assert roll_blocker("WTI/USD", stamp) is None


def test_gold_only_in_quarterly_roll():
    inside = datetime(2026, 12, 10, 15, 0, tzinfo=timezone.utc)
    outside = datetime(2026, 10, 10, 15, 0, tzinfo=timezone.utc)
    assert roll_blocker("XAU/USD", inside) == "CONTRACT_ROLL_WINDOW"
    assert roll_blocker("XAU/USD", outside) is None


def test_forex_is_never_a_roll():
    stamp = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
    assert roll_blocker("EUR/USD", stamp) is None


def test_apply_roll_block_forces_wait():
    state = SoyuzState(commodity="Petrolio WTI", symbol="WTI/USD")
    state.final_decision = "ENTRY"
    state.safety = "SAFE"
    apply_roll_block(state, datetime(2026, 10, 19, tzinfo=timezone.utc))
    assert state.final_decision == "WAIT"
    assert "CONTRACT_ROLL_WINDOW" in state.blockers
