from engine.day_automation import UNIVERSE, decide


def test_commodities_are_in_the_engine():
    assert {"WTI", "BRENT", "XAUUSD", "SUGAR", "COFFEE"} <= set(UNIVERSE)
    assert {"SPY", "QQQ", "ES", "EURUSD"} <= set(UNIVERSE)


def test_wti_can_enter_when_data_aligns():
    decision = decide("WTI", {
        "weekly_bias": "LONG",
        "session": "OPENING_RANGE",
        "news_window": "CLEAR",
        "opening_range": "BROKEN",
        "volume": "ABOVE_AVERAGE",
        "price": 78.4,
        "range_high": 77.8,
        "range_low": 77.1,
        "vwap": 77.5,
        "spread": 0.02,
    })
    assert decision["action"] == "ENTER"
    assert decision["class"] == "commodity"
    assert decision["stop"] == 77.1
    assert decision["send_order"] is False


def test_missing_commodity_data_does_not_enter():
    decision = decide("XAUUSD", {})
    assert decision["action"] == "NONE"
    assert decision["send_order"] is False
