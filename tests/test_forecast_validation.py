from engine.forecast_validation import walk_forward_evaluate


def make_candles(closes):
    return [{"open": x, "high": x * 1.003, "low": x * 0.997, "close": x,
             "timestamp": i * 300} for i, x in enumerate(closes)]


def test_walk_forward_requires_future_outcomes():
    result = walk_forward_evaluate(make_candles([100 + i for i in range(40)]), horizon=4, start=40)
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["observations"] == 0


def test_walk_forward_reports_baseline_and_coverage():
    closes = [100 + i * 0.25 for i in range(80)]
    result = walk_forward_evaluate(make_candles(closes), horizon=3, start=40)
    assert result["status"] == "CALCULATED"
    assert result["observations"] > 0
    assert 0 <= result["accuracy_pct"] <= 100
    assert 0 <= result["coverage_pct"] <= 100
    assert result["benchmark_accuracy_pct"] is not None
    assert "excludes fees" in result["note"]


def test_walk_forward_is_deterministic():
    rows = make_candles([100 + i * 0.1 for i in range(75)])
    assert walk_forward_evaluate(rows) == walk_forward_evaluate(rows)


def test_walk_forward_counts_missed_moves_and_false_signals():
    closes = [100 + i * 0.25 for i in range(80)]
    result = walk_forward_evaluate(make_candles(closes), horizon=3, start=40)
    assert result["status"] == "CALCULATED"
    assert result["missed_move_count"] >= 0
    assert 0 <= result["missed_move_rate_pct"] <= 100
    assert 0 <= result["false_signal_rate_pct"] <= 100
    assert 0 <= result["directional_precision_pct"] <= 100
    assert result["regime_breakdown"]
    for stats in result["regime_breakdown"].values():
        assert stats["observations"] > 0
        assert stats["mean_signed_return_pct"] is not None


def test_missed_move_rate_is_none_when_no_directional_outcomes():
    # Constant prices create no directional outcomes at this threshold.
    rows = make_candles([100.0] * 80)
    result = walk_forward_evaluate(rows, horizon=3, start=40)
    assert result["status"] == "CALCULATED"
    assert result["actual_directional_moves"] == 0
    assert result["missed_move_rate_pct"] is None
