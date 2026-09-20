from soyuz_shadow_integration import (
    run_shadow_safe,
    shadow_enabled,
)


def make_analysis():

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


def test_shadow_safe_returns_diagnostic():

    result = run_shadow_safe(
        "Gold",
        make_analysis(),
    )

    assert result is not None

    assert result[
        "commodity"
    ] == "Gold"

    assert "soyuz" in result

    assert "bot" in result

    assert "comparison" in result


def test_shadow_safe_does_not_modify_analysis():

    analysis = make_analysis()

    original = dict(
        analysis
    )

    run_shadow_safe(
        "Gold",
        analysis,
    )

    assert analysis == original


def test_shadow_is_available():

    assert shadow_enabled() is True


def test_shadow_failure_is_isolated():

    result = run_shadow_safe(
        "Gold",
        None,
    )

    assert result is not None

    assert result[
        "shadow_error"
    ] is True