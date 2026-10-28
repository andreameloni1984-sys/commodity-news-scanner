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


def test_duplicate_timestamps_fail_closed_without_forecasts():
    rows = flat_candles()
    rows[51]["timestamp"] = rows[50]["timestamp"]
    result = evaluate_missed_moves(rows, horizon=4, start=40)
    assert result["status"] == "INVALID_TIMESTAMPS"
    assert result["forecasts"] == 0


def test_out_of_order_timestamps_fail_closed_without_sorting():
    rows = flat_candles()
    rows[50]["timestamp"] = rows[49]["timestamp"] - 1
    result = evaluate_missed_moves(rows, horizon=4, start=40)
    assert result["status"] == "INVALID_TIMESTAMPS"
    assert result["forecasts"] == 0


def test_missing_or_timezone_naive_timestamps_fail_closed():
    missing = flat_candles()
    missing[0].pop("timestamp")
    result = evaluate_missed_moves(missing, horizon=4, start=40)
    assert result["status"] == "INVALID_TIMESTAMPS"
    assert result["forecasts"] == 0

    naive = flat_candles()
    naive[0]["timestamp"] = "2026-10-28T00:00:00"
    result = evaluate_missed_moves(naive, horizon=4, start=40)
    assert result["status"] == "INVALID_TIMESTAMPS"
    assert result["forecasts"] == 0


def test_timezone_aware_iso_timestamps_are_accepted():
    from datetime import datetime, timedelta, timezone

    rows = flat_candles()
    start = datetime(2026, 10, 28, tzinfo=timezone.utc)
    for index, row in enumerate(rows):
        row["timestamp"] = (
            start + timedelta(minutes=5 * index)
        ).isoformat().replace("+00:00", "Z")
    result = evaluate_missed_moves(rows, horizon=4, start=40, threshold_pct=0.5)
    assert result["status"] == "CALCULATED"


def test_non_finite_threshold_is_rejected():
    result = evaluate_missed_moves(flat_candles(), threshold_pct=float("inf"))
    assert result["status"] == "INVALID_PARAMETERS"
    assert result["forecasts"] == 0
