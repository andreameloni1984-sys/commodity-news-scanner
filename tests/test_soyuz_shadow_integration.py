from soyuz_shadow_integration import (
    build_gagarin_data,
    build_intelligence_data,
    build_macro_data,
    compact_shadow_line,
    evaluate_shadow,
    run_shadow_safe,
)


def realistic_analysis():
    return {
        "final_direction": "LONG",
        "setup_direction": "LONG",
        "model_signal": "LONG",
        "signal": "LONG",

        "market_regime": "TREND",

        "macro_confidence": 85,

        "inflation_bias": 20,
        "rates_bias": 30,
        "dollar_bias": 15,
        "energy_bias": 10,
        "geopolitical_bias": 25,
        "fundamentals_bias": 35,

        "mtf_score": 92,
        "correlation_score": 85,
        "news_score": 80,
        "futures_score": 88,
        "anomaly_score": 70,

        "operational_entry_allowed": True,

        "gagarin_state": "READY_LONG",
        "gagarin_blockers": [],

        "gagarin": {
            "regime": {
                "state": "TREND",
                "ok": True,
            },
            "structure": {
                "state": "VALID",
                "ok": True,
            },
            "setup": {
                "state": "CONFIRMED",
                "ok": True,
            },
            "trigger": {
                "state": "CONFIRMED",
                "confirmed": True,
                "ok": True,
            },
            "risk": {
                "state": "VALID",
                "ok": True,
                "rr_tp1": 2.0,
            },
            "safety": {
                "state": "SAFE",
                "ok": True,
            },
            "entry_policy": {
                "state": "READY_LONG",
                "blockers": [],
            },
        },
    }


def blocked_analysis():
    return {
        "final_direction": "LONG",
        "setup_direction": "LONG",
        "signal": "WAIT",

        "market_regime": "TREND",

        "mtf_score": 90,

        "operational_entry_allowed": False,

        "gagarin_state": "WAIT",
        "gagarin_blockers": [
            "RR_TP1_FAIL",
            "TRIGGER_NOT_CONFIRMED",
        ],

        "gagarin": {
            "regime": {
                "state": "TREND",
                "ok": True,
            },
            "structure": {
                "state": "VALID",
                "ok": True,
            },
            "setup": {
                "state": "CONFIRMED",
                "ok": True,
            },
            "trigger": {
                "state": "WAIT",
                "confirmed": False,
                "ok": False,
            },
            "risk": {
                "state": "INVALID",
                "ok": False,
                "rr_tp1": 1.1,
            },
            "safety": {
                "state": "SAFE",
                "ok": True,
            },
            "entry_policy": {
                "state": "WAIT",
                "blockers": [
                    "RR_TP1_FAIL",
                    "TRIGGER_NOT_CONFIRMED",
                ],
            },
        },
    }


def test_shadow_authorizes_realistic_setup():
    analysis = realistic_analysis()

    result = evaluate_shadow(
        "Gold",
        analysis,
    )

    assert result["mode"] == "SHADOW"

    assert result["soyuz"]["direction"] == "LONG"

    assert result["soyuz"]["gagarin_authorized"] is True

    assert result["soyuz"]["state"] == "ENTRY_AUTHORIZED"

    assert result["comparison"]["status"] == "ALIGNED"


def test_shadow_blocks_incomplete_setup():
    analysis = blocked_analysis()

    result = evaluate_shadow(
        "Brent",
        analysis,
    )

    assert result["soyuz"]["direction"] == "LONG"

    assert result["soyuz"]["gagarin_authorized"] is False

    assert result["soyuz"]["state"] == "WAIT_GAGARIN"

    assert result["soyuz"]["gates"]["trigger_ok"] is False

    assert result["soyuz"]["gates"]["risk_ok"] is False


def test_shadow_does_not_modify_analysis():
    analysis = realistic_analysis()

    original = dict(analysis)

    evaluate_shadow(
        "Gold",
        analysis,
    )

    assert analysis == original


def test_shadow_safe_never_raises():
    result = run_shadow_safe(
        "Gold",
        None,
    )

    assert result["error"] is not None

    assert result["comparison"]["status"] == "ERROR"


def test_macro_builder_does_not_invent_missing_values():
    data = build_macro_data(
        {
            "market_regime": "TREND",
        }
    )

    assert data["regime"] == "TREND"

    assert data["inflation_bias"] == 0

    assert data["rates_bias"] == 0

    assert data["dollar_bias"] == 0


def test_intelligence_builder_uses_existing_scores():
    data = build_intelligence_data(
        {
            "final_direction": "LONG",
            "mtf_score": 90,
            "correlation_score": 80,
            "news_score": 70,
            "futures_score": 85,
            "anomaly_score": 60,
        }
    )

    assert data["direction"] == "LONG"

    assert data["mtf_score"] == 90

    assert data["correlation_score"] == 80

    assert data["news_score"] == 70

    assert data["futures_score"] == 85

    assert data["anomaly_score"] == 60


def test_gagarin_gate_requires_explicit_safety():
    data = build_gagarin_data(
        {
            "final_direction": "LONG",
            "market_regime": "TREND",
            "mtf_score": 95,

            "gagarin": {
                "regime": {
                    "state": "TREND",
                    "ok": True,
                },
                "structure": {
                    "state": "VALID",
                    "ok": True,
                },
                "setup": {
                    "state": "CONFIRMED",
                    "ok": True,
                },
                "trigger": {
                    "state": "CONFIRMED",
                    "ok": True,
                },
                "risk": {
                    "state": "VALID",
                    "ok": True,
                },
            },
        }
    )

    assert data["regime_ok"] is True

    assert data["structure_ok"] is True

    assert data["setup_ok"] is True

    assert data["trigger_ok"] is True

    assert data["risk_ok"] is True

    # Safety non dichiarata:
    # SOYUZ NON autorizza.
    assert data["safety_ok"] is False


def test_compact_shadow_line_is_diagnostic_only():
    result = evaluate_shadow(
        "Gold",
        realistic_analysis(),
    )

    line = compact_shadow_line(
        result
    )

    assert "SOYUZ SHADOW" in line

    assert "Gold" in line

    assert "LONG" in line

    assert "ENTRY_AUTHORIZED" in line