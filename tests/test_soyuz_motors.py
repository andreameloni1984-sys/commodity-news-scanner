from soyuz_motors import SoyuzFusion


def test_authorized_only_when_all_gagarin_gates_are_true():
    fusion = SoyuzFusion()

    result = fusion.evaluate(
        "Gold",

        {
            "regime": "TREND",
            "confidence": 80,
        },

        {
            "direction": "LONG",
            "mtf_score": 90,
            "correlation_score": 80,
            "news_score": 70,
            "futures_score": 80,
            "anomaly_score": 60,
        },

        {
            "regime_ok": True,
            "structure_ok": True,
            "setup_ok": True,
            "trigger_ok": True,
            "risk_ok": True,
            "safety_ok": True,
        },
    )

    assert result.state == "ENTRY_AUTHORIZED"
    assert result.gagarin_authorized is True


def test_directional_setup_waits_when_gagarin_blocks():
    fusion = SoyuzFusion()

    result = fusion.evaluate(
        "Brent",

        {
            "regime": "TREND",
            "confidence": 75,
        },

        {
            "direction": "LONG",
            "mtf_score": 90,
        },

        {
            "regime_ok": True,
            "structure_ok": True,
            "setup_ok": True,
            "trigger_ok": False,
            "risk_ok": True,
            "safety_ok": True,
        },
    )

    assert result.state == "WAIT_GAGARIN"
    assert result.gagarin_authorized is False