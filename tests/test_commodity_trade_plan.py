from soyuz_gagarin.commodity_trade_plan import build_commodity_bracket


def test_long_uses_recent_swing_and_valid_rr_ladder():
    plan = build_commodity_bracket(side="LONG", entry=100, atr=2, lows=[98.5, 99, 98.8])
    assert plan["ok"] is True
    assert plan["basis"] == "RECENT_SWING_PLUS_ATR_BUFFER"
    assert plan["stop"] < plan["entry"] < plan["tp1"] < plan["tp2"] < plan["tp3"]
    assert (plan["rr1"], plan["rr2"], plan["rr3"]) == (1.5, 2.0, 2.5)


def test_short_uses_recent_swing_and_valid_rr_ladder():
    plan = build_commodity_bracket(side="SHORT", entry=100, atr=2, highs=[101, 101.5, 102])
    assert plan["ok"] is True
    assert plan["stop"] > plan["entry"] > plan["tp1"] > plan["tp2"] > plan["tp3"] > 0


def test_rejects_swing_outside_maximum_atr_distance():
    plan = build_commodity_bracket(side="LONG", entry=100, atr=1, lows=[95])
    assert plan["ok"] is False
    assert plan["reason"] == "STRUCTURAL_STOP_OUTSIDE_ATR_LIMIT"


def test_fallback_uses_atr_when_swing_is_missing():
    plan = build_commodity_bracket(side="SHORT", entry=100, atr=2)
    assert plan["ok"] is True
    assert plan["basis"] == "ATR_FALLBACK"
    assert round(plan["stop_distance_atr"], 2) == 1.2


def test_invalid_input_fails_closed():
    assert not build_commodity_bracket(side="WAIT", entry=100, atr=1)["ok"]
    assert not build_commodity_bracket(side="LONG", entry=100, atr=0)["ok"]
