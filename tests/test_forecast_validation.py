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

def test_universe_validation_keeps_symbols_separate():
    from engine.forecast_universe_validation import evaluate_universe

    history = {
        "BRENT": make_candles([70 + i * 0.15 for i in range(80)]),
        "XAUUSD": make_candles([2000 - i * 0.2 for i in range(80)]),
    }
    result = evaluate_universe(history, horizon=3, start=40)
    assert result["status"] == "CALCULATED"
    assert result["instrument_count"] == 2
    assert result["valid_instrument_count"] == 2
    assert set(result["instruments"]) == {"BRENT", "XAUUSD"}
    assert result["total_observations"] == sum(
        metrics["observations"] for metrics in result["instruments"].values()
    )


def test_universe_validation_handles_insufficient_history():
    from engine.forecast_universe_validation import evaluate_universe

    result = evaluate_universe({"BRENT": make_candles([70 + i for i in range(20)])})
    assert result["status"] == "NO_VALID_INSTRUMENTS"
    assert result["total_observations"] == 0
    assert result["aggregate_missed_move_rate_pct"] is None

def test_walk_forward_defaults_to_non_overlapping_horizons():
    rows = make_candles([100 + i * 0.2 for i in range(80)])
    result = walk_forward_evaluate(rows, horizon=4, start=40)
    assert result["status"] == "CALCULATED"
    assert result["step_bars"] == 4
    assert result["observations"] == 10


def test_walk_forward_allows_explicit_step_for_signal_frequency_study():
    rows = make_candles([100 + i * 0.2 for i in range(80)])
    sparse = walk_forward_evaluate(rows, horizon=4, start=40, step=4)
    dense = walk_forward_evaluate(rows, horizon=4, start=40, step=1)
    assert sparse["observations"] > 0
    assert dense["observations"] > sparse["observations"]
    assert dense["step_bars"] == 1


def test_walk_forward_skips_non_finite_outcome_prices():
    closes = [100 + i * 0.25 for i in range(80)]
    rows = make_candles(closes)
    rows[45]["close"] = float("nan")
    result = walk_forward_evaluate(rows, horizon=3, start=40)
    assert result["status"] == "CALCULATED"
    assert result["observations"] > 0
    assert result["mean_signed_return_pct"] is not None


def test_walk_forward_cost_adjustment_is_explicit_and_monotonic():
    rows = make_candles([100 + i * 0.25 for i in range(80)])
    gross = walk_forward_evaluate(rows, horizon=3, start=40)
    zero_cost = walk_forward_evaluate(rows, horizon=3, start=40, round_trip_cost_bps=0)
    costly = walk_forward_evaluate(rows, horizon=3, start=40, round_trip_cost_bps=10)
    assert zero_cost["mean_net_signed_return_pct"] == gross["mean_signed_return_pct"]
    assert costly["mean_net_signed_return_pct"] < costly["mean_signed_return_pct"]
    assert costly["round_trip_cost_bps"] == 10
    assert "hypothetical round-trip cost" in costly["note"]
    for stats in costly["regime_breakdown"].values():
        assert "mean_net_signed_return_pct" in stats


def test_walk_forward_rejects_invalid_cost_and_move_threshold():
    rows = make_candles([100 + i * 0.25 for i in range(80)])
    for kwargs in ({"round_trip_cost_bps": -1},
                   {"round_trip_cost_bps": float("inf")},
                   {"min_move_pct": float("nan")}):
        result = walk_forward_evaluate(rows, **kwargs)
        assert result["status"] == "INVALID_PARAMETERS"
        assert result["observations"] == 0


def test_universe_validation_propagates_cost_scenario():
    from engine.forecast_universe_validation import evaluate_universe

    history = {
        "BRENT": make_candles([70 + i * 0.15 for i in range(80)]),
        "XAUUSD": make_candles([2000 - i * 0.2 for i in range(80)]),
    }
    gross = evaluate_universe(history, horizon=3, start=40, round_trip_cost_bps=0)
    costly = evaluate_universe(history, horizon=3, start=40, round_trip_cost_bps=12)
    assert costly["round_trip_cost_bps"] == 12
    assert costly["observation_weighted_mean_net_signed_return_pct"] < (
        costly["observation_weighted_mean_signed_return_pct"]
    )
    assert costly["observation_weighted_mean_net_signed_return_pct"] < (
        gross["observation_weighted_mean_net_signed_return_pct"]
    )
    for metrics in costly["instruments"].values():
        if metrics["status"] == "CALCULATED":
            assert metrics["round_trip_cost_bps"] == 12
            assert "mean_net_signed_return_pct" in metrics


def test_walk_forward_compares_net_returns_with_simple_baselines():
    rows = make_candles([100 + i * 0.25 for i in range(80)])
    result = walk_forward_evaluate(rows, horizon=3, start=40, round_trip_cost_bps=8)
    assert result["status"] == "CALCULATED"
    assert "baseline_always_long_net_return_pct" in result
    assert "baseline_always_short_net_return_pct" in result
    assert result["baseline_always_flat_return_pct"] == 0.0
    assert result["net_edge_vs_always_long_pct"] == round(
        result["mean_net_signed_return_pct"] - result["baseline_always_long_net_return_pct"], 5
    )
    assert result["net_edge_vs_always_short_pct"] == round(
        result["mean_net_signed_return_pct"] - result["baseline_always_short_net_return_pct"], 5
    )
    assert result["net_edge_vs_always_flat_pct"] == result["mean_net_signed_return_pct"]

def test_universe_aggregates_simple_net_return_baselines():
    from engine.forecast_universe_validation import evaluate_universe
    history = {
        "BRENT": make_candles([70 + i * 0.15 for i in range(80)]),
        "XAUUSD": make_candles([2000 - i * 0.2 for i in range(80)]),
    }
    result = evaluate_universe(history, horizon=3, start=40, round_trip_cost_bps=8)
    assert result["status"] == "CALCULATED"
    assert result["observation_weighted_baseline_always_long_net_return_pct"] is not None
    assert result["observation_weighted_baseline_always_short_net_return_pct"] is not None
    assert result["round_trip_cost_bps"] == 8