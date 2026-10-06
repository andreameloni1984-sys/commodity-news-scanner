"""Tests for the non-probabilistic horizon scenario engine."""

from engine.horizons import build_horizon_scenarios


class State:
    def __init__(self, closes, mtf_data=None):
        self.closes = closes
        self.mtf_data = mtf_data or {}


def test_horizons_fail_closed_when_history_is_insufficient():
    state = State([100.0] * 120)

    result = build_horizon_scenarios(state)

    assert result["1D"]["status"] == "INSUFFICIENT_DATA"
    assert result["15D"]["status"] == "INSUFFICIENT_DATA"
    assert result["30D"]["status"] == "INSUFFICIENT_DATA"


def test_15d_uses_explicit_daily_series_when_available():
    daily = [{"close": 100.0 + i} for i in range(15)]
    state = State([100.0] * 120, {"1D": daily})

    result = build_horizon_scenarios(state, ("15D",))

    assert result["15D"]["status"] == "SCENARIO"
    assert result["15D"]["direction"] == "BULLISH"
    assert result["15D"]["probability"] is None
    assert result["15D"]["calibrated"] is False


def test_30d_does_not_invent_a_forecast():
    daily = [{"close": 100.0 + i} for i in range(20)]
    state = State([100.0] * 120, {"1D": daily})

    result = build_horizon_scenarios(state, ("30D",))

    assert result["30D"]["status"] == "INSUFFICIENT_DATA"


def test_neutral_move_is_not_forced_directional():
    daily = [{"close": 100.0}, {"close": 100.1}]
    state = State([100.0] * 300, {"1D": daily})

    result = build_horizon_scenarios(state, ("1D",))

    assert result["1D"]["status"] == "SCENARIO"
    assert result["1D"]["direction"] == "NEUTRAL"
