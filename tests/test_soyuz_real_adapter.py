from soyuz_real_adapter import (
    SoyuzRealAdapter,
    build_real_macro_data,
    build_real_intelligence_data,
    build_real_gagarin_data,
)


def test_real_adapter_reads_real_direction_and_mtf():

    analysis = {
        "market_regime": "TREND_UP",
        "setup_direction": "LONG",

        "timeframes": {
            "4H": {
                "direction": "LONG",
                "score": 90,
            },
            "1H": {
                "direction": "LONG",
                "score": 85,
            },
            "15m": {
                "direction": "LONG",
                "score": 80,
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

    adapter = SoyuzRealAdapter()

    result = adapter.evaluate(
        "Gold",
        analysis,
    )

    assert result["soyuz"]["direction"] == "LONG"
    assert result["soyuz"]["metadata"]["mtf_score"] >= 80
    assert result["soyuz"]["gagarin_authorized"] is True


def test_real_adapter_blocks_shock_regime():

    analysis = {
        "market_regime": "SHOCK",
        "setup_direction": "LONG",

        "timeframes": {
            "4H": {"direction": "LONG"},
            "1H": {"direction": "LONG"},
            "15m": {"direction": "LONG"},
        },

        "entry_trigger": {
            "confirmed": True,
        },

        "risk": {
            "mode": "SHOCK",
        },

        "operational_entry_allowed": False,
    }

    adapter = SoyuzRealAdapter()

    result = adapter.evaluate(
        "Brent",
        analysis,
    )

    assert result["soyuz"]["direction"] == "LONG"
    assert result["soyuz"]["gagarin_authorized"] is False
    assert result["existing_bot"]["operational_entry_allowed"] is False


def test_real_adapter_never_authorizes_without_trigger():

    analysis = {
        "market_regime": "TREND_UP",
        "setup_direction": "LONG",

        "timeframes": {
            "4H": {"direction": "LONG"},
            "1H": {"direction": "LONG"},
            "15m": {"direction": "LONG"},
        },

        "entry_trigger": {
            "confirmed": False,
        },

        "risk": {
            "mode": "NORMAL",
        },

        "entry_policy": {
            "rr_tp1": 2.0,
            "rr_tp2": 2.5,
        },

        "operational_entry_allowed": False,
    }

    adapter = SoyuzRealAdapter()

    result = adapter.evaluate(
        "Gold",
        analysis,
    )

    assert result["soyuz"]["gagarin_authorized"] is False
    assert result["soyuz"]["state"] == "WAIT_GAGARIN"


def test_real_adapter_builders_do_not_invent_missing_macro_data():

    analysis = {
        "market_regime": "RANGE",
        "setup_direction": "SHORT",
    }

    macro = build_real_macro_data(
        analysis
    )

    intelligence = build_real_intelligence_data(
        analysis
    )

    gagarin = build_real_gagarin_data(
        analysis
    )

    assert macro["regime"] == "RANGE"

    assert macro["inflation_bias"] == 0
    assert macro["rates_bias"] == 0
    assert macro["dollar_bias"] == 0

    assert intelligence["direction"] == "SHORT"

    assert gagarin["regime_ok"] is True
    assert gagarin["structure_ok"] is False
    assert gagarin["trigger_ok"]  is False