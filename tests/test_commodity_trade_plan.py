from engine.commodity_trade_plan import build_commodity_trade_plan


def test_long_structural_stop_and_targets_have_correct_geometry():
    plan = build_commodity_trade_plan(
        direction="LONG", reference_price=100, atr=2,
        lows=[98.5, 99, 98.8], highs=[101, 102, 101.5],
    )
    assert plan["status"] == "REFERENCE_ONLY"
    assert plan["stop_loss"] < plan["entry_reference"]
    assert plan["entry_reference"] < plan["take_profit_1"] < plan["take_profit_2"] < plan["take_profit_3"]
    assert plan["stop_basis"] == "RECENT_SWING_PLUS_ATR_BUFFER"
    assert plan["execution_authorized"] is False


def test_short_structural_stop_and_targets_have_correct_geometry():
    plan = build_commodity_trade_plan(
        direction="SHORT", reference_price=100, atr=2,
        highs=[101, 101.5, 102], lows=[98, 99, 98.5],
    )
    assert plan["status"] == "REFERENCE_ONLY"
    assert plan["take_profit_3"] < plan["take_profit_2"] < plan["take_profit_1"] < plan["entry_reference"] < plan["stop_loss"]


def test_rejects_structural_stop_wider_than_atr_cap():
    plan = build_commodity_trade_plan(
        direction="LONG", reference_price=100, atr=1,
        lows=[95], highs=[101],
    )
    assert plan["status"] == "STRUCTURE_TOO_WIDE"
    assert "stop_loss" not in plan


def test_missing_atr_or_bad_direction_fails_closed():
    assert build_commodity_trade_plan(direction="WAIT", reference_price=100, atr=1)["status"] == "INSUFFICIENT_DATA"
    assert build_commodity_trade_plan(direction="LONG", reference_price=100, atr=0)["status"] == "INSUFFICIENT_DATA"


def test_fallback_stop_uses_atr_and_targets_use_r_multiples():
    plan = build_commodity_trade_plan(direction="SHORT", reference_price=100, atr=2)
    assert plan["status"] == "REFERENCE_ONLY"
    assert plan["stop_basis"] == "ATR_FALLBACK"
    assert plan["stop_atr"] == 1.2
    assert plan["rr3"] == 2.5
