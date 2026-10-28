from engine.missed_move_validation import evaluate_missed_moves


def flat_candles(n=70):
    return [
        {"open": 100.0, "high": 100.1, "low": 99.9, "close": 100.0,
         "timestamp": i * 300}
        for i in range(n)
    ]


def test_detects_large_move_that_reverses_before_horizon_close():
    rows = flat_candles()
    # Price briefly reaches +2%, then closes back near the origin price.
    rows[50]["high"] = 102.0
    result = evaluate_missed_moves(rows, horizon=4, start=40, threshold_pct=0.5)
    assert result["status"] == "CALCULATED"
    assert result["important_events"] > 0
    assert result["unanticipated_up"] > 0
    assert result["missed_no_signal"] > 0
    assert result["missed_rate_pct"] is not None


def test_quiet_series_has_no_important_excursions():
    result = evaluate_missed_moves(flat_candles(), horizon=4, start=40, threshold_pct=0.5)
    assert result["status"] == "CALCULATED"
    assert result["important_events"] == 0
    assert result["missed_events"] == 0
    assert result["missed_rate_pct"] is None


def test_insufficient_history_is_explicit():
    result = evaluate_missed_moves(flat_candles(40), horizon=4, start=40)
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["forecasts"] == 0


def test_non_finite_future_excursions_are_skipped():
    rows = flat_candles()
    rows[50]["high"] = float("nan")
    result = evaluate_missed_moves(rows, horizon=4, start=40, threshold_pct=0.5)
    baseline = evaluate_missed_moves(flat_candles(), horizon=4, start=40, threshold_pct=0.5)
    assert result["status"] == "CALCULATED"
    assert result["forecasts"] < baseline["forecasts"]
    assert result["missed_rate_pct"] is None


def test_non_finite_threshold_is_rejected():
    result = evaluate_missed_moves(flat_candles(), threshold_pct=float("inf"))
    assert result["status"] == "INVALID_PARAMETERS"
    assert result["forecasts"] == 0



def test_invalid_audit_parameters_fail_closed_without_coercion():
    invalid_cases = [
        {"horizon": 4.5},
        {"horizon": True},
        {"horizon": float("inf")},
        {"horizon": 0},
        {"start": float("nan")},
        {"start": -1},
        {"threshold_pct": -0.1},
        {"threshold_pct": True},
        {"threshold_pct": "not-a-number"},
    ]
    for kwargs in invalid_cases:
        result = evaluate_missed_moves(flat_candles(), **kwargs)
        assert result["status"] == "INVALID_PARAMETERS", kwargs
        assert result["forecasts"] == 0, kwargs
