from forex.universe import enabled_forex_pairs
from market_universe import enabled_market_instruments
from engine.data import PROVIDER_ORDER, YAHOO_SYMBOLS


def test_forex_universe_contains_major_pairs_and_crosses():
    pairs = enabled_forex_pairs()
    symbols = {pair.symbol for pair in pairs}
    assert len(pairs) == 12
    assert {"EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "NZD/USD", "USD/CAD", "USD/CHF"} <= symbols
    assert {"EUR/JPY", "GBP/JPY", "EUR/GBP", "AUD/JPY", "EUR/CHF"} <= symbols
    assert all(symbol in YAHOO_SYMBOLS for symbol in symbols)
    assert all(symbol in PROVIDER_ORDER for symbol in symbols)


def test_market_universe_is_separate_and_fully_mapped():
    instruments = enabled_market_instruments()
    symbols = {item.symbol for item in instruments}
    assert len(instruments) == 15
    assert {"INDEX:NASDAQ100", "INDEX:SP500", "INDEX:DAX40", "INDEX:EUROSTOXX50", "INDEX:FTSEMIB"} <= symbols
    assert {"COPPER/USD", "NATGAS/USD", "RBOB/USD", "HEATINGOIL/USD"} <= symbols
    assert {"ETF:SPY", "ETF:QQQ", "ETF:IWM", "ETF:GLD", "ETF:SLV", "ETF:USO"} <= symbols
    assert all(symbol in YAHOO_SYMBOLS for symbol in symbols)
    assert all(PROVIDER_ORDER[symbol] == ("YAHOO",) for symbol in symbols)


def test_new_forex_and_market_symbols_are_explicitly_mapped():
    expected = {
        "EUR/JPY": "EURJPY=X",
        "GBP/JPY": "GBPJPY=X",
        "EUR/GBP": "EURGBP=X",
        "AUD/JPY": "AUDJPY=X",
        "EUR/CHF": "EURCHF=X",
        "INDEX:NASDAQ100": "^NDX",
        "INDEX:SP500": "^GSPC",
        "INDEX:DAX40": "^GDAXI",
        "INDEX:EUROSTOXX50": "^STOXX50E",
        "INDEX:FTSEMIB": "FTSEMIB.MI",
        "COPPER/USD": "HG=F",
        "NATGAS/USD": "NG=F",
        "RBOB/USD": "RB=F",
        "HEATINGOIL/USD": "HO=F",
        "ETF:SPY": "SPY",
        "ETF:QQQ": "QQQ",
        "ETF:IWM": "IWM",
        "ETF:GLD": "GLD",
        "ETF:SLV": "SLV",
        "ETF:USO": "USO",
    }
    for symbol, yahoo_symbol in expected.items():
        assert YAHOO_SYMBOLS[symbol] == yahoo_symbol
