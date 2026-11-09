from commodities.universe import (
    auxiliary_commodities,
    enabled_commodities,
    operational_commodities,
)


EXPECTED_COMMODITY_SYMBOLS = {
    "XAU/USD",
    "XAG/USD",
    "COPPER/USD",
    "WTI/USD",
    "BRENT/USD",
    "WHEAT/USD",
    "CORN/USD",
    "SOYBEAN/USD",
}


def test_enabled_universe_is_exactly_the_eight_commodity_basket():
    enabled_symbols = {
        commodity.symbol
        for commodity in enabled_commodities()
    }

    assert enabled_symbols == EXPECTED_COMMODITY_SYMBOLS
    assert {
        commodity.symbol
        for commodity in operational_commodities()
    } == EXPECTED_COMMODITY_SYMBOLS


def test_no_auxiliary_forex_instruments_are_enabled():
    assert auxiliary_commodities() == []
