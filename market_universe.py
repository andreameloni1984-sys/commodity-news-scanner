"""Additional index, ETF and energy instruments for on-demand Gagarin analysis.

These instruments stay separate from the core commodity universe. Symbols are
logical identifiers resolved only through explicit provider mappings.
"""
from commodities.universe import Commodity

MARKET_INSTRUMENTS = [
    # Equity indices
    Commodity(name="Nasdaq 100", symbol="INDEX:NASDAQ100", category="Index", priority=1),
    Commodity(name="S&P 500", symbol="INDEX:SP500", category="Index", priority=2),
    Commodity(name="DAX 40", symbol="INDEX:DAX40", category="Index", priority=3),
    Commodity(name="Euro Stoxx 50", symbol="INDEX:EUROSTOXX50", category="Index", priority=4),
    Commodity(name="FTSE MIB", symbol="INDEX:FTSEMIB", category="Index", priority=5),
    # Additional commodity futures
    Commodity(name="Rame", symbol="COPPER/USD", category="Metal", priority=6),
    Commodity(name="Gas naturale USA", symbol="NATGAS/USD", category="Energy", priority=7),
    Commodity(name="Benzina RBOB USA", symbol="RBOB/USD", category="Energy", priority=8),
    Commodity(name="Gasolio da riscaldamento USA", symbol="HEATINGOIL/USD", category="Energy", priority=9),
    # ETFs: analyzed as listed securities, not as their underlying index/commodity.
    Commodity(name="SPDR S&P 500 ETF", symbol="ETF:SPY", category="ETF", priority=10),
    Commodity(name="Invesco QQQ ETF", symbol="ETF:QQQ", category="ETF", priority=11),
    Commodity(name="iShares Russell 2000 ETF", symbol="ETF:IWM", category="ETF", priority=12),
    Commodity(name="SPDR Gold Shares", symbol="ETF:GLD", category="ETF", priority=13),
    Commodity(name="iShares Silver Trust", symbol="ETF:SLV", category="ETF", priority=14),
    Commodity(name="United States Oil Fund", symbol="ETF:USO", category="ETF", priority=15),
]


def enabled_market_instruments():
    """Return enabled indices, additional energy/metals and ETFs."""
    return [item for item in MARKET_INSTRUMENTS if item.enabled]
