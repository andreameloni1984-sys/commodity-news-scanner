from soyuz_gagarin.engine import GagarinEngine
from soyuz_gagarin.models import Candidate, MarketSnapshot


def candidate():
    return Candidate(
        symbol="XAU/USD",
        side="LONG",
        probability=70,
        quality=70,
        confidence=70,
        rr=3.0,
        stop_distance_atr=1.0,
        data_ok=True,
        live=True,
        trigger_confirmed=True,
        structure_direction="LONG",
        mtf_direction="LONG",
        entry=1.0,
        stop=0.9,
        tp1=1.15,
        tp2=1.2,
        tp3=1.3,
        rr1=1.5,
        rr2=2.0,
        rr3=3.0,
        paper_only=True,
        data_quality_ok=True,
        freshness_ok=True,
        contract_ok=True,
        liquidity_ok=True,
        volatility_ok=True,
        regime_ok=True,
        session_ok=True,
        curve_ok=True,
    )


def test_missing_market_atr_fails_closed():
    decision = GagarinEngine().evaluate(
        MarketSnapshot(
            symbol="XAU/USD",
            timestamp="2026-10-02T00:00:00Z",
            price=1.0,
            atr=0.0,
        ),
        candidate(),
    )
    assert decision.action == "PAPER_WATCH"
    assert decision.reason == "MARKET_ATR_MISSING"


def test_market_atr_must_match_stop_geometry():
    decision = GagarinEngine().evaluate(
        MarketSnapshot(
            symbol="XAU/USD",
            timestamp="2026-10-02T00:00:00Z",
            price=1.0,
            atr=0.2,
        ),
        candidate(),
    )
    assert decision.action == "PAPER_WATCH"
    assert decision.reason == "STOP_ATR_GEOMETRY_MISMATCH"


def test_matching_market_atr_allows_paper_entry():
    decision = GagarinEngine().evaluate(
        MarketSnapshot(
            symbol="XAU/USD",
            timestamp="2026-10-02T00:00:00Z",
            price=1.0,
            atr=0.1,
        ),
        candidate(),
    )
    assert decision.action == "PAPER_ENTRY"
    assert decision.reason == "APPROVED_FOR_PAPER"
