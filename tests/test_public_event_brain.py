from engine.public_event_brain import classify
from telegram.news_monitor import classify_event


def test_tariff_headline_maps_to_watch_candidates_without_trade():
    result = classify("New tariffs on China announced")
    assert "TRADE_POLICY" in result["domains"]
    assert "NASDAQ100" in result["watch_instruments"]
    assert result["trade_direction"] is None
    assert result["order_authorized"] is False


def test_energy_and_agriculture_headlines_map_to_relevant_instruments():
    energy = classify("OPEC cuts crude oil output")
    agriculture = classify("Drought threatens coffee and cocoa harvest")
    assert "WTI" in energy["watch_instruments"]
    assert "BRENT" in energy["watch_instruments"]
    assert "COFFEE" in agriculture["watch_instruments"]
    assert "COCOA" in agriculture["watch_instruments"]


def test_irrelevant_headline_does_not_create_signal():
    result = classify("Local museum opens a new exhibition")
    assert result["status"] == "UNCLASSIFIED"
    assert result["watch_instruments"] == []
    assert result["order_authorized"] is False


def test_gagarin_news_classifier_embeds_public_intelligence():
    result = classify_event("Tariffs on China threaten oil and gold")
    assert result["relevant"] is True
    intelligence = result["political_intelligence"]
    assert "TRADE_POLICY" in intelligence["domains"]
    assert intelligence["order_authorized"] is False
    assert intelligence["trade_direction"] is None
