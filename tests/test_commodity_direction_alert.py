from types import SimpleNamespace

from telegram.commodity_direction_alert import (
    find_directional_commodity_alerts,
    format_directional_commodity_alert,
)


def _state(name="Oro", direction="LONG", age=5, live=True, price=2700.0,
           probability=68, quality=60, confidence=65):
    return SimpleNamespace(
        commodity=name,
        symbol="XAU/USD",
        setup_direction=direction,
        opportunity_direction=None,
        live=live,
        price=price,
        data_age_seconds=age,
        data_source="TEST_PROVIDER",
        probability=probability,
        quality=quality,
        confidence=confidence,
        entry=2695.0,
        stop=2680.0,
        tp1=2730.0,
        metadata={"data_timestamp": "2026-10-20T08:00:00Z"},
    )


def test_directional_alert_formats_long_forecast_without_entry_gate():
    state = _state(direction="LONG")
    # Forecast alerts do not require trigger confirmation or ENTRY authorization.
    state.trigger_confirmed = False
    state.final_decision = "WAIT"

    message = format_directional_commodity_alert([state])

    assert "Oro potrebbe SALIRE" in message
    assert "Prezzo provider: 2700 USD" in message
    assert "PAPER ONLY" in message
    assert "non quotazione Trading 212" in message


def test_directional_alert_formats_short_forecast():
    message = format_directional_commodity_alert([_state("Palladio", "SHORT")])
    assert "Palladio potrebbe SCENDERE" in message


def test_directional_alert_fails_closed_for_stale_or_non_live_price():
    stale = _state(age=999)
    non_live = _state(live=False)
    no_price = _state(price=None)

    assert find_directional_commodity_alerts([stale, non_live, no_price]) == []
    assert format_directional_commodity_alert([stale, non_live, no_price]) == ""


def test_directional_alert_requires_minimum_scores_and_commodity():
    weak = _state(probability=40)
    forex = _state(name="EUR/USD")

    assert find_directional_commodity_alerts([weak, forex]) == []
