from datetime import datetime, timezone

from engine.state import SoyuzState
from engine.setup import apply_setup
from engine.trigger import apply_trigger
from soyuz_gagarin.config import GagarinConfig
from soyuz_gagarin.models import Candidate
from soyuz_gagarin.risk_governor import approve


def test_trend_setup_does_not_require_mtf_confirmation():
    state = SoyuzState(
        commodity="Oro",
        symbol="XAU/USD",
        data_ok=True,
        regime="TREND_UP",
        structure="BULLISH",
        structure_direction="LONG",
        structure_pattern="HH_HL",
        mtf_direction="NONE",
        mtf_alignment=0.0,
    )

    apply_setup(state)

    assert state.setup == "TREND_CONTINUATION"
    assert state.setup_direction == "LONG"


def test_explicit_opposite_mtf_still_blocks_trend_setup():
    state = SoyuzState(
        commodity="Oro",
        symbol="XAU/USD",
        data_ok=True,
        regime="TREND_UP",
        structure="BULLISH",
        structure_direction="LONG",
        structure_pattern="HH_HL",
        mtf_direction="SHORT",
        mtf_alignment=80.0,
    )

    apply_setup(state)

    assert state.setup == "NONE"


def test_closed_m5_momentum_can_confirm_without_mtf_alignment():
    candle_time = datetime(2026, 10, 7, 2, 0, tzinfo=timezone.utc)
    state = SoyuzState(
        commodity="Oro",
        symbol="XAU/USD",
        data_ok=True,
        live=True,
        analysis_timestamp=datetime(2026, 10, 7, 2, 5, tzinfo=timezone.utc).isoformat(),
        atr=2.0,
        price=101.5,
        setup="TREND_CONTINUATION",
        setup_direction="LONG",
        opportunity_type="TREND_CONTINUATION",
        structure="BULLISH",
        structure_direction="LONG",
        mtf_direction="NONE",
        mtf_alignment=0.0,
        mtf_data={
            "5min": [
                {
                    "timestamp": candle_time.timestamp() - 300,
                    "open": 99.8, "high": 100.2, "low": 99.5, "close": 100.0,
                },
                {
                    "timestamp": candle_time.timestamp(),
                    "open": 100.0, "high": 101.6, "low": 99.9, "close": 101.5,
                },
            ]
        },
    )

    apply_trigger(state)

    assert state.trigger_confirmed is True
    assert state.trigger_direction == "LONG"


def _candidate(mtf_direction="NONE"):
    return Candidate(
        symbol="XAU/USD",
        side="LONG",
        probability=95.0,
        quality=95.0,
        confidence=95.0,
        rr=2.5,
        stop_distance_atr=1.0,
        data_ok=True,
        live=True,
        trigger_confirmed=True,
        opportunity_type="TREND_CONTINUATION",
        structure_direction="LONG",
        mtf_direction=mtf_direction,
        entry=100.0,
        stop=99.0,
        tp1=101.5,
        tp2=102.0,
        tp3=102.5,
        rr1=1.5,
        rr2=2.0,
        rr3=2.5,
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


def test_paper_governor_allows_missing_mtf_when_local_evidence_is_valid():
    ok, reason = approve(
        _candidate(),
        GagarinConfig(profile_name="AGGRESSIVE"),
        market_atr=1.0,
    )

    assert ok is True
    assert reason == "APPROVED_FOR_PAPER"


def test_paper_governor_still_rejects_explicit_opposite_mtf():
    ok, reason = approve(
        _candidate(mtf_direction="SHORT"),
        GagarinConfig(profile_name="AGGRESSIVE"),
        market_atr=1.0,
    )

    assert ok is False
    assert reason == "MTF_DIRECTION_MISMATCH"
