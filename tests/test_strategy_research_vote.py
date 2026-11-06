from engine.strategy_research_vote import compare_trend_strategies


def test_uptrend_votes_long_without_execution():
    prices = [100 + i for i in range(35)]
    result = compare_trend_strategies(prices)
    assert result["direction"] == "LONG"
    assert result["long_votes"] >= 2
    assert result["paper_only"] is True
    assert result["execution_allowed"] is False


def test_downtrend_votes_short():
    prices = [200 - i for i in range(35)]
    result = compare_trend_strategies(prices)
    assert result["direction"] == "SHORT"
    assert result["short_votes"] >= 2


def test_breakout_does_not_use_current_bar_in_reference_window():
    prices = [100.0] * 20 + [101.0]
    result = compare_trend_strategies(prices, breakout_period=20)
    assert result["votes"]["breakout"] == "LONG"


def test_insufficient_history_is_not_fabricated_signal():
    result = compare_trend_strategies([100.0])
    assert result["direction"] == "UNKNOWN"
    assert result["status"] == "INSUFFICIENT_HISTORY"


def test_invalid_prices_fail_closed():
    result = compare_trend_strategies([100.0, float("nan"), 102.0])
    assert result["status"] == "NO_DATA"
    assert result["execution_allowed"] is False
