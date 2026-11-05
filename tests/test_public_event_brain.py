from engine.public_event_brain import classify
from telegram.news_monitor import classify_event


def test_tariff_headline_maps_to_selected_watch_candidates_without_trade():
    result = classify("New tariffs on China announced")
    assert "TRADE_POLICY" in result["domains"]
    assert {"SPY", "QQQ", "GOLD"} <= set(result["watch_instruments"])
    assert "NASDAQ100" not in result["watch_instruments"]
    assert "USD" not in result["watch_instruments"]
    assert result["trade_direction"] is None
    assert result["order_authorized"] is False


def test_energy_and_agriculture_headlines_map_to_selected_instruments():
    energy = classify("OPEC cuts crude oil output")
    agriculture = classify("Drought threatens wheat and soybean harvest")
    assert "WTI" in energy["watch_instruments"]
    assert "BRENT" in energy["watch_instruments"]
    assert {"WHEAT", "CORN", "SOYBEAN"} <= set(agriculture["watch_instruments"])
    assert not ({"COFFEE", "COCOA", "RICE", "SUGAR"} & set(agriculture["watch_instruments"]))


def test_metals_headline_maps_only_gold_silver_copper():
    result = classify("Gold, silver and copper prices rise")
    assert {"GOLD", "SILVER", "COPPER"} <= set(result["watch_instruments"])
    assert "PLATINUM" not in result["watch_instruments"]
    assert "PALLADIUM" not in result["watch_instruments"]


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


def test_data_centre_self_generation_maps_to_qqq_and_copper_watch_candidates():
    title = (
        "Trump says data centers should produce their own electricity "
        "and sell excess power to the grid"
    )
    result = classify(title)
    assert "AI_TECH" in result["domains"]
    assert "DATA_CENTERS" in result["domains"]
    assert "POWER_INFRA" in result["domains"]
    assert result["trade_direction"] is None
    assert result["order_authorized"] is False
    assert "QQQ" in result["watch_instruments"]
    assert "COPPER" in result["watch_instruments"]
    assert "POWER_INFRASTRUCTURE" not in result["watch_instruments"]
    assert "NATGAS" not in result["watch_instruments"]


def test_catalyst_candidates_are_watch_only_and_never_authorize_execution():
    from sputnik_catalyst import catalyst_watchlist

    rows = catalyst_watchlist([{
        "source": "WHITE_HOUSE_RSS",
        "event_id": "data-centre-policy-1",
        "domains": ["AI_TECH", "DATA_CENTERS", "POWER_INFRA"],
        "evidence": "PUBLIC_RSS_ITEM",
    }])
    assert rows
    assert all(row["status"] == "WATCH" for row in rows)
    assert all(row["execution_authorized"] is False for row in rows)
    symbols = {row["instrument"] for row in rows}
    assert {"QQQ", "COPPER"} <= symbols
    assert "SEMICONDUCTORS" not in symbols


def test_unrelated_media_mention_does_not_trigger_data_centre_mapping():
    result = classify("Trump discusses media coverage and television interviews")
    assert "DATA_CENTERS" not in result["domains"]
    assert "POWER_INFRA" not in result["domains"]
    assert "QQQ" not in result["watch_instruments"]


def test_generic_data_centre_headline_does_not_create_direction():
    result = classify("AI data centers expand in the United States")
    assert "DATA_CENTERS" in result["domains"]
    assert result["trade_direction"] is None
    assert result["order_authorized"] is False
