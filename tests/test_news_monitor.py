from types import SimpleNamespace

from telegram.news_monitor import classify_event, _confirmed_setups


def test_oil_inventory_draw_is_provisional_bullish_for_crude():
    result = classify_event("EIA reports crude oil inventories fell sharply")
    assert result["relevant"] is True
    assert result["assets"] == ["WTI", "Brent"]
    assert result["impact"]["WTI"] == "RIALZISTA"
    assert result["impact"]["Brent"] == "RIALZISTA"


def test_hawkish_fed_headline_is_provisional_bearish_for_metals():
    result = classify_event("Federal Reserve signals hawkish policy and a rate hike")
    assert "Oro" in result["assets"]
    assert "Argento" in result["assets"]
    assert result["impact"]["Oro"] == "RIBASSISTA"


def test_ambiguous_macro_headline_does_not_force_direction():
    result = classify_event("Trump comments on tariffs")
    assert result["relevant"] is True
    assert result["impact"]["Oro"] == "MISTA"


def test_alert_requires_existing_live_confirmed_aligned_setup():
    event = {"title": "OPEC announces production cut"}
    good = SimpleNamespace(
        commodity="Petrolio WTI",
        symbol="WTI/USD",
        setup_direction="LONG",
        final_decision="PAPER_SIGNAL",
        trigger_confirmed=True,
        live=True,
        price=80.0,
        entry=80.1,
        stop=78.5,
        tp1=83.0,
        tp2=84.0,
    )
    not_live = SimpleNamespace(
        commodity="Petrolio Brent",
        symbol="BRENT/USD",
        setup_direction="LONG",
        final_decision="PAPER_SIGNAL",
        trigger_confirmed=True,
        live=False,
        price=85.0,
        entry=85.1,
        stop=83.5,
        tp1=88.0,
    )
    matches = _confirmed_setups(event, [good, not_live])
    assert len(matches) == 1
    assert matches[0]["asset"] == "WTI"
    assert matches[0]["direction"] == "LONG"
