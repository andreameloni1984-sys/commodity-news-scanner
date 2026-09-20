from soyuz_adapter import SoyuzAdapter


def test_adapter_blocks_when_gagarin_is_incomplete():
    adapter = SoyuzAdapter()

    analysis = {
        "regime": "TREND",
        "direction": "LONG",

        "macro_confidence": 80,

        "mtf_score": 90,
        "correlation_score": 80,
        "news_score": 80,
        "futures_score": 80,
        "anomaly_score": 70,

        "regime_ok": True,
        "structure_ok": True,
        "setup_ok": True,
        "trigger_ok": False,
        "risk_ok": True,
        "safety_ok": True,
    }

    decision = adapter.evaluate(
        "Gold",
        analysis,
    )

    assert decision.direction == "LONG"
    assert decision.gagarin_authorized is False
    assert decision.state == "WAIT_GAGARIN"


def test_adapter_authorizes_when_all_gagarin_gates_are_true():
    adapter = SoyuzAdapter()

    analysis = {
        "regime": "TREND",
        "direction": "LONG",

        "macro_confidence": 90,

        "inflation_bias": 20,
        "rates_bias": 30,
        "dollar_bias": 20,
        "energy_bias": 10,
        "geopolitical_bias": 40,
        "fundamentals_bias": 30,

        "mtf_score": 95,
        "correlation_score": 90,
        "news_score": 90,
        "futures_score": 90,
        "anomaly_score": 80,

        "regime_ok": True,
        "structure_ok": True,
        "setup_ok": True,
        "trigger_ok": True,
        "risk_ok": True,
        "safety_ok": True,
    }

    decision = adapter.evaluate(
        "Gold",
        analysis,
    )

    assert decision.direction == "LONG"
    assert decision.gagarin_authorized is True
    assert decision.state == "ENTRY_AUTHORIZED"