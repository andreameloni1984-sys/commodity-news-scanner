from types import SimpleNamespace

from engine.decision_status import market_decision_status
from engine.safety import apply_safety
from engine.state import SoyuzState


def test_missing_quote_keeps_direction_as_early_bias_and_blocks_paper():
    state = SimpleNamespace(
        setup_direction="LONG",
        pre_move_direction="NONE",
        opportunity_direction="NONE",
        final_decision="BLOCKED",
        safety="BLOCKED",
        blockers=["DATA_NOT_OK", "LIVE_DATA_NOT_FRESH"],
        live=False,
        data_ok=False,
        price=None,
        atr=None,
    )
    result = market_decision_status(state)
    assert result["bias"] == "LONG"
    assert result["bias_source"] == "SETUP"
    assert result["setup"] == "EARLY_BIAS"
    assert result["trade_paper"] == "BLOCKED_NOT_EXECUTED"
    assert "DATA_NOT_OK" in result["blockers"]


def test_fresh_quote_and_atr_without_safety_approval_is_early_setup():
    state = SimpleNamespace(
        setup_direction="SHORT",
        pre_move_direction="NONE",
        opportunity_direction="NONE",
        final_decision="BLOCKED",
        safety="BLOCKED",
        blockers=["TRIGGER_NOT_CONFIRMED"],
        live=True,
        data_ok=True,
        price=80.0,
        atr=1.5,
    )
    result = market_decision_status(state)
    assert result["bias"] == "SHORT"
    assert result["setup"] == "EARLY_SETUP"
    assert result["trade_paper"] == "BLOCKED_NOT_EXECUTED"


def test_safe_entry_is_confirmed_but_explicitly_paper_only():
    state = SimpleNamespace(
        setup_direction="LONG",
        pre_move_direction="NONE",
        opportunity_direction="NONE",
        final_decision="ENTRY",
        safety="SAFE",
        blockers=[],
        live=True,
        data_ok=True,
        price=80.0,
        atr=1.5,
    )
    result = market_decision_status(state)
    assert result["bias"] == "LONG"
    assert result["setup"] == "CONFIRMED"
    assert result["trade_paper"] == "ENTRY_AUTHORIZED_PAPER_ONLY"


def test_no_supported_direction_is_neutral_not_wait():
    state = SimpleNamespace(
        setup_direction="NONE",
        pre_move_direction="NONE",
        opportunity_direction="NONE",
        final_decision="BLOCKED",
        safety="BLOCKED",
        blockers=["NO_VALID_SETUP"],
        live=False,
        data_ok=False,
        price=None,
        atr=None,
    )
    result = market_decision_status(state)
    assert result["bias"] == "NEUTRAL / NO_DIRECTION"
    assert result["setup"] == "NEUTRAL"
    assert result["trade_paper"] == "BLOCKED_NOT_EXECUTED"


def test_legacy_wait_value_is_never_exposed_as_trade_status():
    state = SimpleNamespace(
        setup_direction="LONG",
        pre_move_direction="NONE",
        opportunity_direction="NONE",
        final_decision="WAIT",
        safety="BLOCKED",
        blockers=["DATA_NOT_OK"],
        live=False,
        data_ok=False,
        price=None,
        atr=None,
    )
    result = market_decision_status(state)
    assert result["trade_paper"] == "BLOCKED_NOT_EXECUTED"
    assert "WAIT" not in result.values()


def test_safety_blocker_preserves_direction_but_sets_blocked_not_wait():
    state = SoyuzState(commodity="Petrolio WTI", symbol="CL=F", setup_direction="LONG")
    result = apply_safety(state)
    assert result.setup_direction == "LONG"
    assert result.safety == "BLOCKED"
    assert result.final_decision == "BLOCKED"
    assert result.entry is None
    assert result.stop is None
    assert result.tp1 is None
