from commodities.universe import enabled_commodities, get_symbols, universe_size


def test_active_commodity_universe_keeps_only_selected_core_commodities():
    rows = enabled_commodities()
    commodity_rows = [row for row in rows if row.category != "Forex"]
    assert {row.symbol for row in commodity_rows} == {
        "XAU/USD",
        "XAG/USD",
        "COPPER/USD",
        "WTI/USD",
        "BRENT/USD",
        "WHEAT/USD",
        "CORN/USD",
        "SOYBEAN/USD",
    }
    assert len(commodity_rows) == 8


def test_unneeded_commodity_symbols_are_not_active():
    active = set(get_symbols())
    removed = {
        "XPT/USD",
        "XPD/USD",
        "RICE/USD",
        "SUGAR/USD",
        "COCOA/USD",
        "COFFEE/USD",
        "GASOLINE/USD",
        "NATGAS/USD",
    }
    assert active.isdisjoint(removed)


def test_forex_universe_is_preserved_separately():
    rows = enabled_commodities()
    forex = {row.symbol for row in rows if row.category == "Forex"}
    assert forex == {
        "EUR/USD",
        "GBP/USD",
        "USD/JPY",
        "USD/CHF",
        "AUD/USD",
        "USD/CAD",
        "NZD/USD",
        "EUR/JPY",
    }
    assert universe_size() == 16



def test_core_metals_and_cereals_have_explicit_data_routes():
    from engine.data import AGRI_SYMBOLS, PROVIDER_ORDER, YAHOO_SYMBOLS

    assert YAHOO_SYMBOLS["COPPER/USD"] == "HG=F"
    assert YAHOO_SYMBOLS["WHEAT/USD"] == "ZW=F"
    assert YAHOO_SYMBOLS["CORN/USD"] == "ZC=F"
    assert YAHOO_SYMBOLS["SOYBEAN/USD"] == "ZS=F"
    assert {"WHEAT/USD", "CORN/USD", "SOYBEAN/USD"} <= AGRI_SYMBOLS
    for symbol in ("COPPER/USD", "WHEAT/USD", "CORN/USD", "SOYBEAN/USD"):
        assert "YAHOO" in PROVIDER_ORDER[symbol]
