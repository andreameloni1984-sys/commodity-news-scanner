from engine.forecast_ensemble import forecast_ensemble


def candles(closes):
    rows = []
    for i, close in enumerate(closes):
        rows.append({"open": close * 0.999, "high": close * 1.002,
                     "low": close * 0.998, "close": close,
                     "timestamp": i * 300})
    return rows


def test_insufficient_history_is_explicit():
    result = forecast_ensemble(candles([100 + i for i in range(10)]))
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["direction"] == "NONE"


def test_trend_forecast_is_auditable_and_bounded():
    result = forecast_ensemble(candles([100 + i * 0.5 for i in range(50)]))
    assert result["status"] == "CALCULATED"
    assert result["direction"] == "LONG"
    assert 0 <= result["score"] <= 100
    assert result["features"]["momentum_12bar_pct"] > 0
    assert "not calibrated probability" in result["caveat"].lower()


def test_downtrend_direction():
    result = forecast_ensemble(candles([150 - i * 0.6 for i in range(50)]))
    assert result["status"] == "CALCULATED"
    assert result["direction"] == "SHORT"
    assert result["features"]["momentum_32bar_pct"] < 0


def test_future_candles_do_not_change_past_forecast():
    history = candles([100 + i * 0.2 for i in range(45)])
    before = forecast_ensemble(history)
    after = forecast_ensemble(history + candles([80, 70, 60]))
    assert before == forecast_ensemble(history)
    assert after["status"] == "CALCULATED"

def test_malformed_ohlc_bars_are_ignored():
    valid = candles([100 + i * 0.3 for i in range(45)])
    malformed = {"open": 105, "high": 101, "low": 99, "close": 104, "timestamp": 999}
    clean_result = forecast_ensemble(valid)
    filtered_result = forecast_ensemble(valid[:20] + [malformed] + valid[20:])
    assert filtered_result == clean_result


def test_invalid_bars_cannot_make_history_look_sufficient():
    valid = candles([100 + i * 0.3 for i in range(20)])
    malformed = {"open": 105, "high": 101, "low": 99, "close": 104}
    result = forecast_ensemble(valid + [malformed] * 20)
    assert result["status"] == "INSUFFICIENT_DATA"



def test_prebreakout_fields_are_bounded_and_causal():
    closes = [97, 99, 96, 98, 95, 99, 96, 98, 95, 99, 96, 98,
              95, 99, 96, 98, 95, 99, 96, 98, 95, 99, 96, 98,
              95, 99, 96, 98, 95, 99, 96, 98, 95, 99, 96, 98,
              98.7, 98.9, 99.0, 99.1, 99.2, 99.3, 99.35, 99.4,
              99.42, 99.44, 99.46, 99.48, 99.50, 99.49]
    history = candles(closes)
    result = forecast_ensemble(history)
    assert result["status"] == "CALCULATED"
    assert result["prebreakout_direction"] == "LONG"
    assert result["prebreakout_score"] > 0
    assert result["prebreakout_score"] <= 100
    assert "prebreakout_compression_ratio" in result["features"]
    assert result == forecast_ensemble(history)
