"""Tests for the weekly trend safety gate (gate 21)."""

from engine.safety import apply_safety
from engine.state import SoyuzState
from engine.weekly_trend import apply_weekly_trend


def _base_state(**overrides) -> SoyuzState:
    """Minimal state that passes all gates except the weekly one."""
    state = SoyuzState(
        data_ok=True,
        live=True,
        setup="BREAKOUT_LONG",
        setup_direction="LONG",
        trigger_confirmed=True,
        trigger_direction="LONG",
        structure_direction="LONG",
        mtf_direction="LONG",
        opportunity_type="RANGE_BREAKOUT",
        entry=100.0,
        stop=95.0,
        tp1=105.0,
        tp2=110.0,
        tp3=115.0,
        stop_atr=2.0,
        rr1=1.5,
        rr2=2.0,
        rr3=3.0,
        probability=0.6,
        quality=0.6,
        confidence=0.6,
    )
    for key, value in overrides.items():
        if hasattr(state, key):
            object.__dict__.update({key: value}) if False else None
            if key == "metadata":
                state.metadata.update(value)
            else:
                object.__dict__.update({key: value}) if False else None
                try:
                    object.__getattribute__(state, key)
                    object.__dict__.update({key: value}) if False else None
                except AttributeError:
                    pass
    # Apply overrides via direct attribute assignment where possible
    for key, value in overrides.items():
        if key == "metadata":
            state.metadata.update(value)
        elif hasattr(state, key):
            try:
                object.__dict__.update({key: value}) if False else None
            except Exception:
                pass
    return state


def _state_with(direction, strength="STRONG", bars=20):
    """Build a state whose weekly trend is already classified."""
    state = _base_state()
    state.metadata["weekly_trend"] = {
        "status": "CALCULATED",
        "direction": direction,
        "strength": strength,
        "slope_atr": 1.5 if direction == "LONG" else -1.5,
        "bars": bars,
        "lookback_days": 20,
        "slope_atr_min": 0.5,
        "slope_atr_strong": 1.0,
    }
    return state


def test_weekly_trend_blocks_opposing_long():
    """Weekly SHORT must block a LONG setup."""
    state = _state_with("SHORT")
    state = apply_safety(state)
    assert state.safety == "BLOCKED"
    assert state.final_decision == "WAIT"
    assert "WEEKLY_TREND_MISMATCH" in state.blockers


def test_weekly_trend_blocks_opposing_short():
    """Weekly LONG must block a SHORT setup."""
    state = _state_with("LONG")
    state = apply_safety(state)
    # flip setup to SHORT
    state.setup_direction = "SHORT"
    state.trigger_direction = "SHORT"
    state.structure_direction = "SHORT"
    state.mtf_direction = "SHORT"
    state.opportunity_type = "TREND_CONTINUATION"
    state.entry = 100.0
    state.stop = 105.0
    state.tp1 = 95.0
    state.tp2 = 90.0
    state.tp3 = 85.0
    state = apply_safety(state)
    assert state.safety == "BLOCKED"
    assert "WEEKLY_TREND_MISMATCH" in state.blockers


def test_weekly_trend_allows_aligned_long():
    """Weekly LONG must allow a LONG setup."""
    state = _state_with("LONG")
    state = apply_safety(state)
    assert "WEEKLY_TREND_MISMATCH" not in state.blockers
    assert state.safety == "SAFE"
    assert state.final_decision == "ENTRY"


def test_weekly_trend_fail_open_missing():
    """Missing weekly trend must not block (fail-open)."""
    state = _base_state()  # no weekly_trend in metadata
    state = apply_safety(state)
    assert "WEEKLY_TREND_MISMATCH" not in state.blockers
    assert state.safety == "SAFE"


def test_weekly_trend_fail_open_none_direction():
    """Weekly trend with direction NONE must not block."""
    state = _state_with("NONE", strength="NONE")
    state = apply_safety(state)
    assert "WEEKLY_TREND_MISMATCH" not in state.blockers
    assert state.safety == "SAFE"


def test_apply_weekly_trend_writes_metadata():
    """apply_weekly_trend must write the weekly_trend dict."""
    state = _base_state()
    state.metadata["daily_closes"] = [100 + i * 0.5 for i in range(20)]
    state = apply_weekly_trend(state)
    wt = state.metadata["weekly_trend"]
    assert wt["status"] == "CALCULATED"
    assert wt["direction"] == "LONG"
    assert wt["strength"] == "STRONG"
    assert wt["bars"] == 20
