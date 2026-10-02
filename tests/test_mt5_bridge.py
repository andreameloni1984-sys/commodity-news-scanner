import pytest

from soyuz_gagarin.engine import GagarinEngine
from soyuz_gagarin.models import Candidate, MarketSnapshot
from soyuz_gagarin.mt5_bridge import build_demo_payload


def approved_decision():
    candidate = Candidate(
        symbol="XPT/USD",
        side="LONG",
        probability=80,
        quality=70,
        confidence=70,
        rr=5,
        stop_distance_atr=1.0,
        data_ok=True,
        live=True,
        trigger_confirmed=True,
        structure_direction="LONG",
        mtf_direction="LONG",
        entry=100.0,
        stop=98.0,
        tp1=104.0,
        tp2=106.0,
        tp3=110.0,
        rr1=2.0,
        rr2=3.0,
        rr3=5.0,
    )
    return GagarinEngine().evaluate(
        MarketSnapshot("XPT/USD", "2026-10-02T00:00:00Z", 100.0),
        candidate,
    )


def test_builds_demo_payload_without_execution():
    decision = approved_decision()
    payload = build_demo_payload(decision)

    assert payload["transport"] == "MT5_DEMO"
    assert payload["paper_only"] is True
    assert payload["execution"] == "DISABLED"
    assert payload["symbol"] == "XPT/USD"
    assert payload["side"] == "LONG"
    assert payload["entry"] == 100.0
    assert payload["stop_loss"] == 98.0
    assert payload["take_profit_3"] == 110.0


def test_wait_cannot_become_mt5_payload():
    decision = approved_decision()
    decision.action = "WAIT"

    with pytest.raises(ValueError, match="DECISION_NOT_PAPER_SIGNAL"):
        build_demo_payload(decision)


def test_invalid_geometry_is_blocked():
    decision = approved_decision()
    decision.candidate.tp3 = 97.0

    with pytest.raises(ValueError, match="INVALID_LONG_GEOMETRY"):
        build_demo_payload(decision)
