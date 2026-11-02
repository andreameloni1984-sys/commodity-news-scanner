from engine.lubjanka import intercept_market

BASE = 1_800_000_000  # aligned to a 5-minute boundary


def make_bars(direction="flat", count=30, last_volume=100):
    closes = [100.0] * count
    if direction == "up":
        closes[-4:] = [100.15, 100.35, 100.65, 101.05]
    elif direction == "down":
        closes[-4:] = [99.85, 99.65, 99.35, 98.95]
    bars = []
    for index, close in enumerate(closes):
        opening = closes[index - 1] if index else close
        bars.append({
            "timestamp": BASE + index * 300,
            "open": opening,
            "high": max(opening, close) + 0.10,
            "low": min(opening, close) - 0.10,
            "close": close,
            "volume": last_volume if index == count - 1 else 100,
        })
    return bars


def test_lubjanka_intercepts_early_move_momentum_and_breakout_long():
    candles = make_bars("up", last_volume=250)
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 301, provider="Yahoo")
    names = {event["interceptor"] for event in result["events"]}

    assert result["status"] == "INTERCEPTED"
    assert result["direction"] == "LONG"
    assert result["stage"] == "EARLY_SETUP"
    assert {"EARLY_MOVE", "MOMENTUM", "BREAKOUT"} <= names
    assert result["volume_proxy"] == "EXPANSION"
    assert result["evidence_type"] == "OHLCV_PROXY_NOT_DOM"
    assert result["decision_impact"] == "OBSERVATION_ONLY"
    assert result["execution_levels"] == "NOT_GENERATED"
    assert not any(key in result for key in ("entry", "stop", "tp1", "tp2", "tp3"))



def test_lubjanka_intercepts_failed_upside_breakout_as_short():
    candles = make_bars("flat")
    candles[-1]["high"] = 100.4
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 301)
    event = next(item for item in result["events"] if item["interceptor"] == "FALSE_BREAKOUT")
    assert event["direction"] == "SHORT"
    assert event["stage"] == "EARLY_SETUP"
    assert result["direction"] == "SHORT"
    assert result["primary_interceptor"] == "FALSE_BREAKOUT"


def test_lubjanka_intercepts_failed_downside_breakout_as_long():
    candles = make_bars("flat")
    candles[-1]["low"] = 99.6
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 301)
    event = next(item for item in result["events"] if item["interceptor"] == "FALSE_BREAKOUT")
    assert event["direction"] == "LONG"
    assert event["stage"] == "EARLY_SETUP"
    assert result["direction"] == "LONG"


def test_lubjanka_marks_two_sided_range_sweep_as_directional_conflict():
    candles = make_bars("flat")
    candles[-1]["high"] = 100.4
    candles[-1]["low"] = 99.6
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 301)
    false_breakouts = [
        item for item in result["events"]
        if item["interceptor"] == "FALSE_BREAKOUT"
    ]
    assert {item["direction"] for item in false_breakouts} == {"LONG", "SHORT"}
    assert result["directional_conflict"] is True
    assert result["directions_detected"] == ["LONG", "SHORT"]


def test_lubjanka_intercepts_short_direction():
    candles = make_bars("down")
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 301)
    assert result["status"] == "INTERCEPTED"
    assert result["direction"] == "SHORT"
    assert any(event["direction"] == "SHORT" for event in result["events"])


def test_lubjanka_does_not_invent_a_signal_in_a_flat_market():
    candles = make_bars("flat")
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 301)
    assert result["status"] == "NO_INTERCEPT"
    assert result["direction"] == "NO_DIRECTION"
    assert result["events"] == []


def test_lubjanka_ignores_the_still_forming_five_minute_candle():
    candles = make_bars("up")
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 100)
    assert result["status"] == "INTERCEPTED"
    assert result["last_bar_timestamp"] == candles[-2]["timestamp"]


def test_lubjanka_rejects_stale_completed_candles():
    candles = make_bars("up")
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 3600)
    assert result["status"] == "STALE_DATA"
    assert result["events"] == []


def test_lubjanka_rejects_non_monotonic_timestamps():
    candles = make_bars("up")
    candles[-2]["timestamp"] = candles[-1]["timestamp"]
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 301)
    assert result["status"] == "NON_MONOTONIC_CANDLES"


def test_lubjanka_rejects_impossible_ohlc():
    candles = make_bars("up")
    candles[-1]["low"] = 999
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 301)
    assert result["status"] == "MALFORMED_OHLC"


def test_lubjanka_allows_finite_negative_historical_futures_prices():
    candles = make_bars("down")
    for bar in candles:
        for key in ("open", "high", "low", "close"):
            bar[key] -= 200
    result = intercept_market(candles, now_epoch=candles[-1]["timestamp"] + 301)
    assert result["status"] == "INTERCEPTED"
    assert result["direction"] == "SHORT"
