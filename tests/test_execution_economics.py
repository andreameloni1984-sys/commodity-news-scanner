from soyuz_gagarin.execution_economics import (
    basis,
    basis_percent,
    breakeven_win_rate,
    cost_r,
    curve_state,
    executable_price,
    expectancy_net_r,
    position_size,
    rr_from_prices,
    spread,
    spread_bps,
)


def test_quote_formulas_use_real_bid_ask_inputs():
    assert spread(100, 101) == 1
    assert round(spread_bps(100, 101), 4) == 99.5025
    assert executable_price("LONG", 100, 101) == 101
    assert executable_price("SHORT", 100, 101) == 100


def test_quote_formulas_fail_closed():
    assert spread(None, 101) is None
    assert spread(101, 100) is None
    assert executable_price("LONG", 0, 101) is None


def test_rr_and_breakeven_are_price_based():
    assert rr_from_prices("LONG", 100, 98, 105) == 2.5
    assert rr_from_prices("SHORT", 100, 102, 95) == 2.5
    assert breakeven_win_rate(2, 1) == round(1 / 3, 6)


def test_expectancy_net_accounts_for_explicit_cost():
    assert expectancy_net_r(0.60, 2, 1, 0.0) == 0.8
    assert expectancy_net_r(0.60, 2, 1, 0.1) == 0.7


def test_expectancy_and_risk_fail_closed():
    assert expectancy_net_r(None, 2, 1) is None
    assert cost_r(None, 100, 98) is None
    assert position_size(10000, 0.01, 100, 98, 1) == 0.5


def test_basis_and_curve_are_explicit_data_only():
    assert basis(105, 100) == 5
    assert basis_percent(105, 100) == 5.0
    assert curve_state(100, 101) == "CONTANGO"
    assert curve_state(101, 100) == "BACKWARDATION"
    assert curve_state(100, 100) == "FLAT"
    assert basis(None, 100) is None
    assert curve_state(100, None) is None
