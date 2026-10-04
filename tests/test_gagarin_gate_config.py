from gagarin_gate import evaluate
from soyuz_gagarin.config import GagarinConfig


def valid_candidate():
    return {
        "symbol": "TEST_CONFIG",
        "data_status": "LIVE",
        "paper_only": True,
        "data_quality_ok": True,
        "freshness_ok": True,
        "contract_ok": True,
        "liquidity_ok": True,
        "volatility_ok": True,
        "regime_ok": True,
        "session_ok": True,
        "curve_ok": True,
        "mtf_confirmed": True,
        "setup_valid": True,
        "direction": "LONG",
        "trigger_confirmed": True,
        "trigger_direction": "LONG",
        "entry": 100.0,
        "stop": 98.0,
        "tp1": 106.0,
        "tp2": 108.0,
        "tp3": 110.0,
        "atr": 1.0,
        "probability": 62.0,
        "quality": 55.0,
        "confidence": 60.0,
    }


def test_legacy_gate_uses_canonical_config_thresholds():
    cfg = GagarinConfig()
    c = valid_candidate()

    assert c["probability"] == cfg.min_probability
    assert c["quality"] == cfg.min_quality
    assert c["confidence"] == cfg.min_confidence

    result = evaluate(c)

    assert result.state == "ENTRY"
    assert result.final_confluence is True


def test_legacy_gate_blocks_just_below_canonical_probability():
    cfg = GagarinConfig()
    c = valid_candidate()
    c["probability"] = cfg.min_probability - 0.01

    result = evaluate(c)

    assert result.state == "WATCH"
    assert "PROBABILITY_FAIL" in result.blockers


def test_legacy_gate_blocks_just_below_canonical_rr():
    cfg = GagarinConfig()
    c = valid_candidate()
    # TP1 = 105 makes RR = 2.5 exactly; move it one cent below the threshold.
    c["tp1"] = 104.99

    result = evaluate(c)

    assert result.state == "WATCH"
    assert "RR_FAIL" in result.blockers
