from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from engine.cloud_api_status import attach_runtime_decision_metadata, cloud_api_decision_status


def make_state(
    direction="LONG",
    *,
    live=False,
    data_ok=False,
    price=None,
    atr=None,
    timestamp=None,
):
    return SimpleNamespace(
        setup_direction=direction,
        pre_move_direction="NONE",
        opportunity_direction="NONE",
        live=live,
        data_ok=data_ok,
        price=price,
        atr=atr,
        analysis_timestamp=timestamp or "",
        final_decision="BLOCKED",
        safety="BLOCKED",
        blockers=["TRIGGER_NOT_CONFIRMED"],
    )


def fresh_state(direction="LONG"):
    return make_state(
        direction,
        live=True,
        data_ok=True,
        price=75.0,
        atr=1.25,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def test_missing_cloud_decision_preserves_direction_as_early_bias():
    result = cloud_api_decision_status(make_state("LONG"), {})

    assert result["action"] == "NO_DECISION"
    assert result["bias"] == "LONG"
    assert result["setup"] == "EARLY_BIAS"
    assert result["trade_paper"] == "NOT_EXECUTED"
    assert result["reason"] == "DECISION_NOT_RETURNED"


def test_legacy_wait_is_normalized_without_erasing_short_bias():
    result = cloud_api_decision_status(
        fresh_state("SHORT"),
        {"gagarin_action": "WAIT", "gagarin_reason": "TRIGGER_NOT_CONFIRMED", "fresh_live": True},
    )

    assert result["action"] == "PAPER_WATCH"
    assert result["bias"] == "SHORT"
    assert result["setup"] == "EARLY_SETUP"
    assert result["trade_paper"] == "BLOCKED_NOT_EXECUTED"
    assert "WAIT" not in result.values()


def test_only_fresh_engine_paper_entry_can_be_confirmed():
    result = cloud_api_decision_status(
        fresh_state("LONG"),
        {"gagarin_action": "PAPER_ENTRY", "fresh_live": True},
    )

    assert result["action"] == "PAPER_ENTRY"
    assert result["bias"] == "LONG"
    assert result["setup"] == "CONFIRMED"
    assert result["trade_paper"] == "ENTRY_AUTHORIZED_PAPER_ONLY"


def test_stale_paper_entry_is_downgraded_and_not_authorized():
    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    state = make_state(
        "LONG",
        live=True,
        data_ok=True,
        price=75.0,
        atr=1.25,
        timestamp=stale.isoformat(),
    )
    result = cloud_api_decision_status(
        state,
        {"gagarin_action": "PAPER_ENTRY", "fresh_live": True},
    )

    assert result["action"] == "PAPER_WATCH"
    assert result["bias"] == "LONG"
    assert result["setup"] == "EARLY_BIAS"
    assert result["trade_paper"] == "BLOCKED_NOT_EXECUTED"
    assert result["reason"] == "PAPER_ENTRY_REJECTED_BY_STATUS_VALIDATION"


def test_no_direction_is_explicitly_neutral_not_wait():
    result = cloud_api_decision_status(make_state("NONE"), {})

    assert result["action"] == "NO_DECISION"
    assert result["bias"] == "NEUTRAL / NO_DIRECTION"
    assert result["setup"] == "NEUTRAL"
    assert result["trade_paper"] == "NOT_EXECUTED"
    assert "WAIT" not in result.values()



def test_runtime_missing_decision_preserves_bias_without_wait():
    state = make_state("SHORT")
    metadata = attach_runtime_decision_metadata(state, None)

    assert metadata["gagarin_action"] == "NO_DECISION"
    assert metadata["gagarin_bias"] == "SHORT"
    assert metadata["gagarin_setup"] == "EARLY_BIAS"
    assert metadata["gagarin_trade_paper"] == "NOT_EXECUTED"
    assert "WAIT" not in metadata.values()


def test_runtime_legacy_wait_becomes_safety_block_not_market_wait():
    state = make_state("LONG")
    decision = SimpleNamespace(action="WAIT", reason="TRIGGER_NOT_CONFIRMED")
    metadata = attach_runtime_decision_metadata(state, decision)

    assert metadata["gagarin_action"] == "BLOCKED"
    assert metadata["gagarin_bias"] == "LONG"
    assert metadata["gagarin_trade_paper"] == "BLOCKED_NOT_EXECUTED"
    assert "WAIT" not in metadata.values()


def test_cli_and_monitor_use_shared_runtime_status_adapter():
    for path in ("main.py", "telegram/render_runner.py"):
        source = Path(path).read_text(encoding="utf-8")
        assert "attach_runtime_decision_metadata" in source
        assert 'else "WAIT"' not in source
