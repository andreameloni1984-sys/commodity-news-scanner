def extract_technical_trigger_ok(analysis):
    """
    Trigger tecnico di basso livello.
    NON è l'autorità finale.
    """
    trigger_value = analysis.get(
        "entry_trigger"
    )

    if isinstance(trigger_value, dict):
        value = _first(
            trigger_value,
            "confirmed",
            "ok",
            "valid",
            "authorized",
            "trigger_confirmed",
            default=None,
        )

        if value is not None:
            return _bool(value)

        state = _upper(
            _first(
                trigger_value,
                "state",
                "status",
                "label",
                default="",
            )
        )

        return state in {
            "CONFIRMED",
            "READY",
            "VALID",
            "ACTIVE",
            "TRIGGERED",
        }

    if trigger_value is not None:
        return _bool(
            trigger_value
        )

    return False


def extract_prediction_trigger_ok(
    analysis
):
    """
    Prediction Authority v5.3.1.
    Questo ha priorità sul trigger tecnico.
    """

    prediction = analysis.get(
        "prediction_authority_v531"
    )

    if not isinstance(
        prediction,
        dict,
    ):
        return None

    value = _first(
        prediction,
        "trigger_confirmed",
        "confirmed",
        default=None,
    )

    if value is None:
        return None

    return _bool(value)