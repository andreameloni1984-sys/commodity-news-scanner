from types import SimpleNamespace

from engine.gagarin import build_lubjanka_handoff


def _state(events, *, atr=2.0):
    return SimpleNamespace(
        metadata={
            "lubjanka": {"status": "INTERCEPTED" if events else "NO_INTERCEPT", "events": events},
            "quote_market_type": "FUTURES_CONTINUOUS",
        },
        candles=[{"timestamp": 1_800_000_000, "open": 100.0, "high": 103.0, "low": 99.0, "close": 101.0}],
        atr=atr,
        data_source="YAHOO",
    )


def test_lubjanka_long_is_surfaced_with_reference_levels_without_authorizing_execution():
    result = build_lubjanka_handoff(_state([
        {"interceptor": "EARLY_MOVE", "direction": "LONG", "stage": "EARLY_BIAS"},
        {"interceptor": "MOMENTUM", "direction": "LONG", "stage": "EARLY_SETUP"},
    ]))

    assert result["status"] == "EARLY_WATCH"
    assert result["direction"] == "LONG"
    assert result["entry_reference"] == 101.0
    assert result["stop_loss_reference"] == 99.0
    assert result["take_profit_1_reference"] == 103.0
    assert result["take_profit_2_reference"] == 105.0
    assert result["risk_reward_tp2"] == 2.0
    assert result["market_type"] == "FUTURES_CONTINUOUS"
    assert result["execution_authorized"] is False
    assert result["paper_only"] is True


def test_lubjanka_short_is_surfaced():
    result = build_lubjanka_handoff(_state([
        {"interceptor": "EARLY_MOVE", "direction": "SHORT", "stage": "EARLY_BIAS"},
    ]))

    assert result["direction"] == "SHORT"
    assert result["stop_loss_reference"] == 103.0
    assert result["take_profit_1_reference"] == 99.0
    assert result["take_profit_2_reference"] == 97.0


def test_discordant_interceptors_are_visible_not_silently_discarded():
    result = build_lubjanka_handoff(_state([
        {"interceptor": "EARLY_MOVE", "direction": "LONG"},
        {"interceptor": "BREAKOUT", "direction": "SHORT"},
    ]))

    assert result["status"] == "DIRECTION_CONFLICT"
    assert result["directions"] == ["LONG", "SHORT"]
    assert result["execution_authorized"] is False


def test_missing_or_stale_lubjanka_data_is_reported():
    state = _state([])
    state.metadata["lubjanka"] = {"status": "STALE_DATA", "reason": "old candles"}
    result = build_lubjanka_handoff(state)

    assert result["status"] == "UNAVAILABLE"
    assert result["reason"] == "old candles"


def test_no_directional_events_do_not_create_a_candidate():
    result = build_lubjanka_handoff(_state([]))

    assert result["status"] == "NO_EARLY_MOVE"
    assert result["execution_authorized"] is False
