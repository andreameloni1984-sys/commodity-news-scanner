from soyuz_shadow import (
    SoyuzShadow,
    shadow_summary,
)


def base_analysis():

    return {
        "market_regime": "TREND_UP",

        "setup_direction": "LONG",

        "timeframes": {
            "4H": {
                "direction": "LONG",
                "score": 90,
            },
            "1H": {
                "direction": "LONG",
                "score": 90,
            },
            "15m": {
                "direction": "LONG",
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


def test_shadow_detects_agreement():

    engine = SoyuzShadow()

    result = engine.evaluate(
        "Gold",
        base_analysis(),
    )

    assert result.direction_agreement is True

    assert result.bot_authorized is True

    assert result.soyuz_authorized is True

    assert result.authorization_agreement is True

    assert result.divergence is False


def test_shadow_detects_authorization_divergence():

    analysis = base_analysis()

    analysis[
        "operational_entry_allowed"
    ] = False

    engine = SoyuzShadow()

    result = engine.evaluate(
        "Gold",
        analysis,
    )

    assert result.bot_authorized is False

    assert result.soyuz_authorized is True

    assert result.authorization_agreement is False

    assert result.divergence is True


def test_shadow_detects_direction_divergence():

    analysis = base_analysis()

    analysis[
        "setup_direction"
    ] = "SHORT"

    engine = SoyuzShadow()

    result = engine.evaluate(
        "Gold",
        analysis,
    )

    assert result.bot_direction == "SHORT"

    assert result.soyuz_direction == "SHORT"

    assert result.direction_agreement is True


def test_shadow_summary_is_generated():

    engine = SoyuzShadow()

    result = engine.evaluate(
        "Brent",
        base_analysis(),
    )

    summary = shadow_summary(
        result
    )

    assert "SOYUZ SHADOW" in summary

    assert "Brent" in summary

    assert "BOT=LONG" in summary

    assert "SOYUZ=LONG" in summary