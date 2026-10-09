from engine.day_automation import decide, line


def test_missing_data_blocks_with_reason():
    decision = decide("SPY", {"weekly_bias": "LONG"})
    assert decision["action"] == "NONE"
    assert decision["send_order"] is False
    assert decision["reason"]


def test_aligned_long_has_entry_stop_exit():
    decision = decide("SPY", {
        "weekly_bias": "LONG",
        "session": "OPENING_RANGE",
        "news_window": "CLEAR",
        "opening_range": "BROKEN",
        "volume": "ABOVE_AVERAGE",
        "price": 570,
        "range_high": 568,
        "range_low": 566,
        "vwap": 567,
        "spread": 0.01,
        "max_spread": 0.03,
    })
    assert decision["action"] == "ENTER"
    assert decision["side"] == "LONG"
    assert decision["entry"] == 570
    assert decision["stop"] == 566
    assert decision["exit"] == "sotto VWAP"
    assert decision["send_order"] is False
    assert "entra 570" in line(decision)
