from commodities.universe import enabled_commodities, validate_universe
from engine.data import AGRI_SYMBOLS, AGRI_TERMS, PROVIDER_ORDER, YAHOO_SYMBOLS
from soyuz_gagarin.config import GagarinConfig
from engine.market_status import AGRICULTURE, METALS


EXPECTED = [
    ("Oro", "XAU/USD", "Metal"),
    ("Argento", "XAG/USD", "Metal"),
    ("Rame", "COPPER/USD", "Metal"),
    ("Petrolio WTI", "WTI/USD", "Energy"),
    ("Petrolio Brent", "BRENT/USD", "Energy"),
    ("Grano", "WHEAT/USD", "Agriculture"),
    ("Mais", "CORN/USD", "Agriculture"),
    ("Soia", "SOYBEAN/USD", "Agriculture"),
]


def test_enabled_universe_is_exactly_the_selected_eight():
    actual = [(item.name, item.symbol, item.category) for item in enabled_commodities()]
    assert actual == EXPECTED
    assert validate_universe() == []


def test_governor_allowlist_matches_selected_universe():
    assert set(GagarinConfig().allowed_assets) == {symbol for _, symbol, _ in EXPECTED}


def test_selected_assets_have_explicit_provider_routing():
    for symbol in ("XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD", "BRENT/USD",
                   "WHEAT/USD", "CORN/USD", "SOYBEAN/USD"):
        assert symbol in YAHOO_SYMBOLS
        assert symbol in PROVIDER_ORDER
    for symbol in ("WHEAT/USD", "CORN/USD", "SOYBEAN/USD"):
        assert symbol in AGRI_SYMBOLS
        assert symbol in AGRI_TERMS
        assert PROVIDER_ORDER[symbol][0] == "YAHOO"


def test_copper_and_grain_fallback_symbols_are_explicit():
    assert YAHOO_SYMBOLS["COPPER/USD"] == "HG=F"
    assert YAHOO_SYMBOLS["WHEAT/USD"] == "ZW=F"
    assert YAHOO_SYMBOLS["CORN/USD"] == "ZC=F"
    assert YAHOO_SYMBOLS["SOYBEAN/USD"] == "ZS=F"


def test_market_status_groups_match_selected_metals_and_agriculture():
    assert METALS == {"Oro", "Argento", "Rame"}
    assert AGRICULTURE == {"Grano", "Mais", "Soia"}
