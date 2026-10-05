from soyuz_gagarin.prediction_outcome import evaluate_prediction


BASE = {
    "direction": "LONG",
    "entry": 100.0,
    "stop": 95.0,
    "tp1": 107.5,
    "tp2": 110.0,
    "tp3": 112.5,
}


def test_tp1_is_counted_after_entry():
    bars = [
        {"low": 101, "high": 103},
        {"low": 100, "high": 108},
    ]
    result = evaluate_prediction(BASE, bars)
    assert result.outcome == "TP1"
    assert result.entry_hit is True
    assert result.r_multiple == 1.5


def test_stop_is_counted_as_loss():
    bars = [
        {"low": 99, "high": 101},
        {"low": 94, "high": 99},
    ]
    result = evaluate_prediction(BASE, bars)
    assert result.outcome == "SL"
    assert result.r_multiple == -1.0


def test_entry_not_touched_is_not_a_prediction_win_or_loss():
    bars = [
        {"low": 101, "high": 104},
        {"low": 100.5, "high": 106},
    ]
    result = evaluate_prediction(BASE, bars)
    assert result.outcome == "NOT_TRIGGERED"
    assert result.entry_hit is False
    assert result.r_multiple is None


def test_same_bar_stop_and_target_is_ambiguous():
    bars = [
        {"low": 94, "high": 108},
    ]
    result = evaluate_prediction(BASE, bars)
    assert result.outcome == "AMBIGUOUS"
    assert result.r_multiple is None


def test_short_r_is_calculated_from_actual_geometry():
    prediction = {
        "direction": "SHORT",
        "entry": 100.0,
        "stop": 104.0,
        "tp1": 94.0,
        "tp2": 92.0,
        "tp3": 90.0,
    }
    result = evaluate_prediction(
        prediction,
        [{"low": 93.5, "high": 99.5}],
    )
    assert result.outcome == "TP1"
    assert result.r_multiple == 1.5
