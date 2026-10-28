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


def test_non_finite_ohlc_fails_closed_before_forecasting():
    rows = flat_candles()
    rows[50]["high"] = float("nan")
    result = evaluate_missed_moves(rows, horizon=4, start=40, threshold_pct=0.5)
    assert result["status"] == "INVALID_OHLC"
    assert result["forecasts"] == 0


def test_open_or_close_outside_bar_range_fails_closed():
    for field, value in (("open", 99.0), ("close", 101.0)):
        rows = flat_candles()
        rows[50][field] = value
        result = evaluate_missed_moves(rows, horizon=4, start=40, threshold_pct=0.5)
        assert result["status"] == "INVALID_OHLC", (field, value)
        assert result["forecasts"] == 0


def test_non_finite_threshold_is_rejected():
    result = evaluate_missed_moves(flat_candles(), threshold_pct=float("inf"))
    assert result["status"] == "INVALID_PARAMETERS"
    assert result["forecasts"] == 0
