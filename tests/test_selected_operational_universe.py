from commodities.universe import enabled_commodities, get_symbols, validate_universe
from engine.invest_universe import enabled_instruments


def test_gagarin_only_enables_selected_core_commodities():
    assert [item.name for item in enabled_commodities()] == [
        "Oro", "Argento", "Rame", "Petrolio WTI", "Petrolio Brent"
    ]
    assert get_symbols() == ["XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD", "BRENT/USD"]
    assert validate_universe() == []


def test_invest_only_enables_spy_and_qqq():
    assert [item.name for item in enabled_instruments()] == ["SPY", "QQQ"]
