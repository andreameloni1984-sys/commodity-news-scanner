"""Forex universe for explicit, on-demand Gagarin analysis.

Forex is intentionally kept separate from the commodity universe.
"""
from commodities.universe import Commodity

FOREX_PAIRS = [
    Commodity(name="Forex EUR/USD", symbol="EUR/USD", category="Forex", priority=1),
    Commodity(name="Forex GBP/USD", symbol="GBP/USD", category="Forex", priority=2),
    Commodity(name="Forex USD/JPY", symbol="USD/JPY", category="Forex", priority=3),
    Commodity(name="Forex AUD/USD", symbol="AUD/USD", category="Forex", priority=4),
    Commodity(name="Forex NZD/USD", symbol="NZD/USD", category="Forex", priority=5),
    Commodity(name="Forex USD/CAD", symbol="USD/CAD", category="Forex", priority=6),
    Commodity(name="Forex USD/CHF", symbol="USD/CHF", category="Forex", priority=7),
    Commodity(name="Forex EUR/JPY", symbol="EUR/JPY", category="Forex", priority=8),
    Commodity(name="Forex GBP/JPY", symbol="GBP/JPY", category="Forex", priority=9),
    Commodity(name="Forex EUR/GBP", symbol="EUR/GBP", category="Forex", priority=10),
    Commodity(name="Forex AUD/JPY", symbol="AUD/JPY", category="Forex", priority=11),
    Commodity(name="Forex EUR/CHF", symbol="EUR/CHF", category="Forex", priority=12),
]


def enabled_forex_pairs():
    """Return the configured Forex pairs without changing the commodity universe."""
    return [pair for pair in FOREX_PAIRS if pair.enabled]
