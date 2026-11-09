from engine.lubjanka_playbook import build_conditional_playbook

def bars(direction="down", count=20):
    closes = [100.0] * count
    if direction == "down":
        closes[-4:] = [99.9, 99.7, 99.4, 99.0]
    else:
        closes[-4:] = [100.1, 100.3, 100.6, 101.0]
    result = []
    for i, close in enumerate(closes):
        opening = closes[i - 1] if i else close
        result.append({"timestamp": 1800000000 + i * 300, "open": opening,
                       "high": max(opening, close) + .1, "low": min(opening, close) - .1,
                       "close": close, "volume": 100})
    return result

def test_short_playbook_has_ordered_levels_and_activation():
    candles = bars("down")
    plan = build_conditional_playbook(candles, {"status": "INTERCEPTED", "direction": "SHORT",
        "primary_interceptor": "EARLY_MOVE", "directional_conflict": False},
        now_epoch=candles[-1]["timestamp"] + 301)
    assert plan["status"] == "CONDITIONAL_PLAN"
    assert plan["stop_loss"] > plan["entry_trigger"] > plan["take_profit_1"] > plan["take_profit_2"]
    assert plan["rr_tp1"] == 1.5 and plan["rr_tp2"] == 2.5
    assert plan["execution_status"] == "NOT_EXECUTED"

def test_long_playbook_has_ordered_levels():
    candles = bars("up")
    plan = build_conditional_playbook(candles, {"status": "INTERCEPTED", "direction": "LONG",
        "primary_interceptor": "BREAKOUT", "directional_conflict": False},
        now_epoch=candles[-1]["timestamp"] + 301)
    assert plan["status"] == "CONDITIONAL_PLAN"
    assert plan["stop_loss"] < plan["entry_trigger"] < plan["take_profit_1"] < plan["take_profit_2"]

def test_conflicting_interceptors_keep_primary_direction_visible():
    candles = bars("down")
    plan = build_conditional_playbook(candles, {"status": "INTERCEPTED", "direction": "SHORT",
        "directional_conflict": True}, now_epoch=candles[-1]["timestamp"] + 301)
    assert plan["status"] == "CONDITIONAL_PLAN"
    assert plan["direction"] == "SHORT"
    assert plan["directional_conflict"] is True
    assert "CONFLITTO" in plan["note"]

def test_stale_bars_never_create_a_plan():
    candles = bars("down")
    plan = build_conditional_playbook(candles, {"status": "INTERCEPTED", "direction": "SHORT",
        "directional_conflict": False}, now_epoch=candles[-1]["timestamp"] + 3600)
    assert plan["status"] == "UNAVAILABLE"

def test_playbook_rejects_bar_older_than_ten_minutes():
    candles = bars("down")
    plan = build_conditional_playbook(
        candles,
        {"status": "INTERCEPTED", "direction": "SHORT", "directional_conflict": False},
        now_epoch=candles[-1]["timestamp"] + 603,
    )
    assert plan["status"] == "UNAVAILABLE"
    assert "non fresca" in plan["reason"]
