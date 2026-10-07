from engine.opportunity import calculate_expectancy, expectancy_from_hit_rate


def test_expectancy_formula_positive():
    result = calculate_expectancy(0.40, 3.0, 1.0)
    assert result["expectancy_r"] == 0.6
    assert result["breakeven_win_rate"] == 0.25
    assert result["positive"] is True


def test_expectancy_formula_negative():
    result = calculate_expectancy(0.40, 1.0, 1.0)
    assert result["expectancy_r"] == -0.2
    assert result["positive"] is False


def test_hit_rate_expectancy_proxy_uses_standard_2r_target():
    result = expectancy_from_hit_rate(60.0)
    assert result["expectancy_r"] == 0.8
    assert result["breakeven_win_rate"] == 0.333333
    assert result["status"] == "POSITIVE_EXPECTANCY"


def test_invalid_expectancy_fails_closed():
    result = calculate_expectancy(None, 2.0, 1.0)
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["positive"] is False
