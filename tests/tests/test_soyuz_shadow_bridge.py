from soyuz_shadow_bridge import (
    SoyuzShadowBridge,
)


def make_analysis(direction="LONG"):

    return {
        "market_regime": "TREND_UP",
        "setup_direction": direction,

        "timeframes": {
            "4H": {
                "direction": direction,
                "score": 90,
            },
            "1H": {
                "direction": direction,
                "score": 90,
            },
            "15m": {
                "direction": direction,
                "score": 85,
            },
        },

        "entry_trigger": {
            "confirmed": True,
            "score": 90,
        },

        "risk": {
            "mode": "NORMAL",
        },

        "entry_policy": {
            "rr_tp1": 2.0,
            "rr_tp2": 2.5,
            "entry_status": "ENTRY_CONFIRMED",
        },

        "operational_entry_allowed": True,
    }


def test_bridge_does_not_modify_original():

    analysis = make_analysis()

    original = dict(
        analysis
    )

    bridge = SoyuzShadowBridge()

    result = bridge.analyze(
        "Gold",
        analysis,
    )

    assert result.commodity == "Gold"

    assert analysis == original


def test_bridge_returns_shadow_result():

    bridge = SoyuzShadowBridge()

    result = bridge.analyze(
        "Silver",
        make_analysis(),
    )

    assert result.bot_direction == "LONG"

    assert result.soyuz_direction == "LONG"

    assert result.bot_authorized is True

    assert result.soyuz_authorized is True


def test_bridge_can_process_multiple_commodities():

    bridge = SoyuzShadowBridge()

    analyses = {
        "Gold": make_analysis("LONG"),
        "Silver": make_analysis("LONG"),
        "Brent": make_analysis("SHORT"),
    }

    results = bridge.analyze_many(
        analyses
    )

    assert len(results) == 3

    commodities = {
        result.commodity
        for result in results
    }

    assert commodities == {
        "Gold",
        "Silver",
        "Brent",
    }


def test_bridge_diagnostic_is_read_only():

    bridge = SoyuzShadowBridge()

    result = bridge.analyze(
        "Gold",
        make_analysis(),
    )

    diagnostic = bridge.diagnostic(
        result
    )

    assert diagnostic[
        "commodity"
    ] == "Gold"

    assert "bot" in diagnostic

    assert "soyuz" in diagnostic

    assert "comparison" in diagnostic

    assert diagnostic[
        "comparison"
    ][
        "divergence"
    ] is False


def test_bridge_summary():

    bridge = SoyuzShadowBridge()

    result = bridge.analyze(
        "Gold",
        make_analysis(),
    )

    summary = bridge.summary(
        result
    )

    assert "SOYUZ SHADOW" in summary

    assert "Gold" in summary

    assert "BOT=LONG" in summary

    assert "SOYUZ=LONG" in summary