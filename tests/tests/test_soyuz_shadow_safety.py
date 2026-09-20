from soyuz_shadow import SoyuzShadow


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


def test_shadow_does_not_modify_original_analysis():

    analysis = base_analysis()

    original_allowed = analysis[
        "operational_entry_allowed"
    ]

    original_direction = analysis[
        "setup_direction"
    ]

    engine = SoyuzShadow()

    engine.evaluate(
        "Gold",
        analysis,
    )

    assert analysis[
        "operational_entry_allowed"
    ] == original_allowed

    assert analysis[
        "setup_direction"
    ] == original_direction


def test_shadow_is_read_only_when_bot_blocks():

    analysis = base_analysis()

    analysis[
        "operational_entry_allowed"
    ] = False

    original = dict(analysis)

    engine = SoyuzShadow()

    result = engine.evaluate(
        "Gold",
        analysis,
    )

    assert result.bot_authorized is False

    assert analysis[
        "operational_entry_allowed"
    ] is False

    assert analysis[
        "setup_direction"
    ] == original[
        "setup_direction"
    ]


def test_shadow_never_creates_order_command():

    analysis = base_analysis()

    engine = SoyuzShadow()

    result = engine.evaluate(
        "Gold",
        analysis,
    )

    # Lo Shadow Mode può soltanto restituire
    # una valutazione diagnostica.
    assert not hasattr(
        result,
        "order",
    )

    assert not hasattr(
        result,
        "execute",
    )

    assert not hasattr(
        result,
        "send_order",
    )


def test_shadow_result_contains_only_diagnostic_authorization():

    analysis = base_analysis()

    engine = SoyuzShadow()

    result = engine.evaluate(
        "Gold",
        analysis,
    )

    assert hasattr(
        result,
        "soyuz_authorized",
    )

    assert hasattr(
        result,
        "bot_authorized",
    )

    assert hasattr(
        result,
        "divergence",
    )

    # Nessun prezzo operativo viene creato
    # dal motore Shadow.
    assert not hasattr(
        result,
        "entry",
    )

    assert not hasattr(
        result,
        "stop_loss",
    )

    assert not hasattr(
        result,
        "take_profit",
    )