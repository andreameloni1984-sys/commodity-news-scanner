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
    event = {"title": "OPEC announces production cut", "baseline_prices": {"WTI": 80.0}}
    good = SimpleNamespace(
        commodity="Petrolio WTI",
        symbol="WTI/USD",
        setup_direction="LONG",
        final_decision="PAPER_SIGNAL",
        trigger_confirmed=True,
        live=True,
        price=80.1,
        entry=80.1,
        stop=78.5,
        tp1=83.0,
        tp2=84.0,
        data_source="TEST_FEED",
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
    assert matches[0]["move_pct"] >= 0.05



def test_new_news_triggers_immediate_analysis_then_waits_for_price_confirmation(tmp_path, monkeypatch):
    import telegram.news_monitor as monitor
    from datetime import datetime, timedelta, timezone

    monkeypatch.setattr(monitor, "STATE_PATH", tmp_path / "news_state.json")
    now = datetime(2026, 10, 18, 14, 0, tzinfo=timezone.utc)
    item = {
        "source": "Test RSS",
        "title": "OPEC announces production cut",
        "url": "https://example.test/opec-cut",
        "published_at": (now - timedelta(minutes=1)).isoformat(),
    }
    state = SimpleNamespace(
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
        data_source="TEST_FEED",
    )
    analysis_calls = []
    messages = []

    def analyze():
        analysis_calls.append(1)
        return [state]

    first = monitor.poll_news_once(
        lambda message: messages.append(message) or True,
        analyze,
        fetcher=lambda: [item],
        now=now,
    )
    assert first["analysis"] == 1
    assert first["alerts"] == 0
    assert len(analysis_calls) == 1

    state.price = 80.1
    second = monitor.poll_news_once(
        lambda message: messages.append(message) or True,
        analyze,
        fetcher=lambda: [item],
        now=now + timedelta(minutes=5),
    )
    assert second["analysis"] == 1
    assert second["alerts"] == 1
    assert len(messages) == 1
    assert "Reazione dal rilevamento" in messages[0]
    assert "PAPER/DEMO" in messages[0]



def test_oil_supply_risk_headlines_are_classified_bullish():
    for title in (
        "Tanker attacks raise oil supply risk",
        "Iran sanctions threaten crude exports",
        "Oilfield shutdown disrupts production",
    ):
        result = classify_event(title)
        assert result["impact"]["Brent"] == "RIALZISTA"
        assert result["impact"]["WTI"] == "RIALZISTA"
        assert result["matched_terms"]["Brent"]["bullish"]


def test_mixed_oil_catalysts_stay_neutral_and_explain_why():
    result = classify_event(
        "OPEC production cut as weak demand outlook raises oversupply concerns"
    )
    assert result["impact"]["Brent"] == "MISTA"
    assert result["matched_terms"]["Brent"]["bullish"]
    assert result["matched_terms"]["Brent"]["bearish"]
    assert 0 <= result["confidence_score"] <= 100


def test_selected_agricultural_commodities_are_classified_by_crop_catalyst():
    coffee = classify_event("Brazil drought threatens Arabica coffee harvest")
    cocoa = classify_event("Cocoa crop disease reduces production forecast")
    rice = classify_event("Rice export ban disrupts supply")
    sugar = classify_event("Sugar production rises after bumper harvest")
    assert coffee["impact"]["Caffè"] == "RIALZISTA"
    assert cocoa["impact"]["Cacao"] == "RIALZISTA"
    assert rice["impact"]["Riso"] == "RIALZISTA"
    assert sugar["impact"]["Zucchero"] == "RIBASSISTA"


def test_platinum_supported_but_silver_excluded_from_selected_universe():
    result = classify_event("Platinum rises as the Federal Reserve signals rate cuts")
    assert "Platino" in result["assets"]
    assert "Argento" not in result["assets"]


def test_agricultural_mixed_catalysts_remain_mixed():
    result = classify_event("Coffee harvest improves but drought threatens supply")
    assert result["impact"]["Caffè"] == "MISTA"
