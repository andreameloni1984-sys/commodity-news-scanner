from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from soyuz_gagarin.adapter import evaluate_states
from soyuz_gagarin.engine import GagarinEngine
from soyuz_gagarin.models import Candidate, MarketSnapshot


def market(symbol="XAU/USD"):
    return MarketSnapshot(
        symbol=symbol,
        timestamp="2026-10-02T00:00:00Z",
        price=1.0,
    )


def candidate(**overrides):
    values = dict(
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
        tp1=1.1,
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
    values.update(overrides)
    return Candidate(**values)


def test_rejects_low_quality():
    d = GagarinEngine().evaluate(
        market(),
        candidate(quality=40),
    )
    assert d.action == "WAIT"
    assert d.reason == "QUALITY_BELOW_THRESHOLD"


def test_allows_paper_candidate():
    d = GagarinEngine().evaluate(
        market(),
        candidate(),
    )
    assert d.action == "PAPER_SIGNAL"
    assert d.reason == "APPROVED_FOR_PAPER"


def test_unknown_asset_is_blocked():
    d = GagarinEngine().evaluate(
        market("XYZ"),
        candidate(symbol="XYZ"),
    )
    assert d.action == "WAIT"
    assert d.reason == "ASSET_NOT_IN_UNIVERSE"


def test_legacy_wait_is_not_an_automatic_gagarin_veto():
    state = SimpleNamespace(
        symbol="XPT/USD",
        price=100.0,
        atr=2.0,
        setup_direction="LONG",
        probability=80.0,
        quality=70.0,
        confidence=70.0,
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
        stop_atr=1.0,
        rr1=2.0,
        rr2=3.0,
        rr3=5.0,
        regime="TREND_UP",
        final_decision="WAIT",
        blockers=["FINAL_CONFLUENCE_FAIL"],
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
        metadata={"operational_gates": {
            "paper_only": True, "data_quality_ok": True, "freshness_ok": True,
            "contract_ok": True, "liquidity_ok": True, "volatility_ok": True,
            "regime_ok": True, "session_ok": True, "curve_ok": True,
        }},
    )

    decisions = evaluate_states([state])

    assert len(decisions) == 1
    assert decisions[0].action == "PAPER_SIGNAL"
    assert decisions[0].reason == "APPROVED_FOR_PAPER"


def test_missing_trigger_stays_wait():
    state = SimpleNamespace(
        symbol="XAU/USD",
        price=100.0,
        atr=2.0,
        setup_direction="LONG",
        probability=80.0,
        quality=70.0,
        confidence=70.0,
        data_ok=True,
        live=True,
        trigger_confirmed=False,
        structure_direction="LONG",
        mtf_direction="LONG",
        entry=100.0,
        stop=98.0,
        tp1=104.0,
        tp2=106.0,
        tp3=110.0,
        stop_atr=1.0,
        rr1=2.0,
        rr2=3.0,
        rr3=5.0,
        regime="TREND_UP",
        final_decision="WAIT",
        blockers=["TRIGGER_NOT_CONFIRMED"],
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
        metadata={"operational_gates": {
            "paper_only": True, "data_quality_ok": True, "freshness_ok": True,
            "contract_ok": True, "liquidity_ok": True, "volatility_ok": True,
            "regime_ok": True, "session_ok": True, "curve_ok": True,
        }},
    )

    decisions = evaluate_states([state])

    assert decisions[0].action == "WAIT"
    assert decisions[0].reason == "TRIGGER_NOT_CONFIRMED"


def test_rejects_invalid_target_geometry():
    d = GagarinEngine().evaluate(
        market(),
        candidate(tp2=1.05),
    )
    assert d.action == "WAIT"
    assert d.reason == "TARGET_GEOMETRY_INVALID"


def test_rejects_weak_rr_tiers_even_when_tp3_is_strong():
    d = GagarinEngine().evaluate(
        market(),
        candidate(rr1=1.0, rr2=2.0, rr3=4.0),
    )
    assert d.action == "WAIT"
    assert d.reason == "RR_TIER_BELOW_THRESHOLD"


def test_operational_gate_is_hard_veto():
    d = GagarinEngine().evaluate(
        market(),
        candidate(liquidity_ok=False),
    )
    assert d.action == "WAIT"
    assert d.reason == "LIQUIDITY_FAIL"


def test_stale_timestamp_fails_closed_even_when_freshness_gate_is_true():
    state = SimpleNamespace(
        symbol="XAU/USD",
        price=100.0,
        atr=2.0,
        setup_direction="LONG",
        probability=80.0,
        quality=70.0,
        confidence=70.0,
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
        stop_atr=1.0,
        rr1=2.0,
        rr2=3.0,
        rr3=5.0,
        regime="TREND_UP",
        final_decision="WAIT",
        blockers=[],
        analysis_timestamp=(datetime.now(timezone.utc) - timedelta(seconds=901)).isoformat(),
        metadata={"operational_gates": {
            "paper_only": True, "data_quality_ok": True, "freshness_ok": True,
            "contract_ok": True, "liquidity_ok": True, "volatility_ok": True,
            "regime_ok": True, "session_ok": True, "curve_ok": True,
        }},
    )

    decisions = evaluate_states([state])

    assert decisions[0].action == "WAIT"
    assert decisions[0].reason == "FRESHNESS_FAIL"
