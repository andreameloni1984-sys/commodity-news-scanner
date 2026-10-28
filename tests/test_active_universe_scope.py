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
        "RICE/USD",
    }
    assert len(commodity_rows) == 6


def test_unneeded_commodity_symbols_are_not_active():
    active = set(get_symbols())
    removed = {
        "XPT/USD",
        "XPD/USD",
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
    assert universe_size() == 14
