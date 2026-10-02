from soyuz_gagarin.engine import GagarinEngine
from soyuz_gagarin.models import Candidate, MarketSnapshot


def market(symbol="GOLD"):
    return MarketSnapshot(symbol=symbol, timestamp="2026-10-02T00:00:00Z", price=1.0)


def test_rejects_low_quality():
    c = Candidate("GOLD", "LONG", 70, 40, 70, 3.0, 1.0)
    d = GagarinEngine().evaluate(market(), c)
    assert d.action == "WAIT"


def test_allows_paper_candidate():
    c = Candidate("GOLD", "LONG", 70, 70, 70, 3.0, 1.0)
    d = GagarinEngine().evaluate(market(), c)
    assert d.action == "PAPER_SIGNAL"
    assert "PAPER" in d.reason


def test_unknown_asset_is_blocked():
    c = Candidate("XYZ", "LONG", 90, 90, 90, 4.0, 1.0)
    d = GagarinEngine().evaluate(market("XYZ"), c)
    assert d.action == "WAIT"
