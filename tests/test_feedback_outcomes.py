from types import SimpleNamespace

from engine.feedback import _candles, _timestamp, append_signal, load_feedback, record_forecasts, summarize, update_open_outcomes


def state(candles):
    return SimpleNamespace(
        commodity="Gold",
        symbol="XAU/USD",
        setup_direction="LONG",
        timeframe="5min",
        probability=71,
        quality=68,
        confidence=70,
        entry=100.0,
        stop=98.0,
        tp1=103.0,
        tp2=104.0,
        tp3=105.0,
        rr1=1.5,
        rr2=2.0,
        rr3=2.5,
        stop_atr=1.0,
        regime="TREND_UP",
        structure_direction="LONG",
        setup="TREND_CONTINUATION",
        trigger="BREAKOUT",
        data_source="TEST",
        data_ok=True,
        live=True,
        metadata={"data_status": "TEST", "gagarin_action": "PAPER_ENTRY"},
        candles=candles,
        timestamps=[],
        highs=[],
        lows=[],
    )


def test_signal_is_not_duplicated_on_repeated_scan(tmp_path):
    path = tmp_path / "feedback.csv"
    s = state([{"timestamp": 1000, "high": 101, "low": 99}])
    assert append_signal(s, path=path) is True
    assert append_signal(s, path=path) is False
    assert len(load_feedback(path)) == 1


def test_target_outcome_and_r_metrics_are_recorded(tmp_path):
    path = tmp_path / "feedback.csv"
    s0 = state([{"timestamp": 1000, "high": 101, "low": 99}])
    append_signal(s0, path=path)
    s1 = state([
        {"timestamp": 1000, "high": 101, "low": 99},
        {"timestamp": 2000, "high": 103.5, "low": 99.5},
    ])
    assert update_open_outcomes([s1], path=path) == 1
    row = load_feedback(path)[0]
    assert row["outcome"] == "TP1"
    assert float(row["r_multiple"]) == 1.5
    assert float(row["mfe_r"]) == 1.75
    assert int(row["bars_held"]) == 1
    summary = summarize(path=path)
    assert summary["closed"] == 1
    assert summary["win_rate_pct"] == 100.0


def test_same_bar_stop_and_target_is_scored_as_stop(tmp_path):
    path = tmp_path / "feedback.csv"
    append_signal(state([{"timestamp": 1000, "high": 101, "low": 99}]), path=path)
    s1 = state([
        {"timestamp": 1000, "high": 101, "low": 99},
        {"timestamp": 2000, "high": 104, "low": 97.5},
    ])
    update_open_outcomes([s1], path=path)
    row = load_feedback(path)[0]
    assert row["outcome"] == "STOP"
    assert float(row["r_multiple"]) == -1.0


def test_summary_breaks_down_per_asset_and_direction(tmp_path):
    path = tmp_path / "feedback.csv"
    append_signal(state([{"timestamp": 1000, "high": 101, "low": 99}]), path=path)
    s1 = state([
        {"timestamp": 1000, "high": 101, "low": 99},
        {"timestamp": 2000, "high": 103.5, "low": 99.5},
    ])
    update_open_outcomes([s1], path=path)
    summary = summarize(path=path)
    group = summary["by_symbol_direction"]["XAU/USD LONG"]
    assert group["closed"] == 1
    assert group["win_rate_pct"] == 100.0
    assert group["average_r"] == 1.5


def test_live_directional_watch_forecast_is_tracked_separately(tmp_path):
    path = tmp_path / "feedback.csv"
    s = state([{"timestamp": 1000, "high": 101, "low": 99}])
    s.metadata["gagarin_action"] = "PAPER_WATCH"
    assert record_forecasts([s], path=path) == 1
    row = load_feedback(path)[0]
    assert row["direction"] == "LONG"
    assert row["action"] == "PAPER_WATCH"
    assert row["outcome"] == "OPEN"


def test_watch_forecast_upgrades_to_entry_without_duplicate(tmp_path):
    path = tmp_path / "feedback.csv"
    s = state([{"timestamp": 1000, "high": 101, "low": 99}])
    s.metadata["gagarin_action"] = "PAPER_WATCH"
    assert record_forecasts([s], path=path) == 1
    s.metadata["gagarin_action"] = "PAPER_ENTRY"
    assert record_forecasts([s], path=path) == 0
    rows = load_feedback(path)
    assert len(rows) == 1
    assert rows[0]["action"] == "PAPER_ENTRY"

def test_outcome_matching_uses_timeframe_when_symbol_is_shared(tmp_path):
    path = tmp_path / "feedback.csv"
    five_min = state([
        {"timestamp": 1000, "high": 101, "low": 99},
    ])
    five_min.timeframe = "5min"
    append_signal(five_min, path=path)

    fifteen_min = state([
        {"timestamp": 1000, "high": 101, "low": 99},
    ])
    fifteen_min.timeframe = "15min"
    fifteen_min.entry = 100.0
    fifteen_min.stop = 95.0
    fifteen_min.tp1 = 110.0
    fifteen_min.tp2 = 115.0
    fifteen_min.tp3 = 120.0
    fifteen_min.metadata["gagarin_action"] = "PAPER_WATCH"
    # The 15-minute candles hit a stop, but must not be used for the 5-minute row.
    fifteen_min.candles.append({"timestamp": 2000, "high": 101, "low": 97})
    assert update_open_outcomes([five_min, fifteen_min], path=path) == 0
    assert load_feedback(path)[0]["outcome"] == "OPEN"


def test_summary_reports_probability_calibration_and_regime_breakdown(tmp_path):
    path = tmp_path / "feedback.csv"
    s0 = state([{"timestamp": 1000, "high": 101, "low": 99}])
    append_signal(s0, path=path)
    s1 = state([
        {"timestamp": 1000, "high": 101, "low": 99},
        {"timestamp": 2000, "high": 103.5, "low": 99.5},
    ])
    update_open_outcomes([s1], path=path)
    summary = summarize(path=path)
    calibration = summary["probability_calibration"]
    assert calibration["samples"] == 1
    assert calibration["brier_score"] == 0.0841
    assert calibration["bins"] == [{
        "range_pct": "70-80",
        "count": 1,
        "mean_predicted_pct": 71.0,
        "observed_win_rate_pct": 100.0,
    }]
    assert summary["by_regime"]["TREND_UP"]["closed"] == 1
    assert summary["by_setup"]["TREND_CONTINUATION"]["average_r"] == 1.5
    assert summary["max_drawdown_r_sequential"] == 0.0


def test_forecast_identity_includes_timeframe(tmp_path):
    path = tmp_path / "feedback.csv"
    five_min = state([{"timestamp": 1000, "high": 101, "low": 99}])
    fifteen_min = state([{"timestamp": 1000, "high": 101, "low": 99}])
    fifteen_min.timeframe = "15min"

    assert record_forecasts([five_min, fifteen_min], path=path) == 2
    rows = load_feedback(path)
    assert len(rows) == 2
    assert {row["timeframe"] for row in rows} == {"5min", "15min"}
    assert len({row["signal_id"] for row in rows}) == 2



def test_naive_iso_timestamp_is_rejected_but_explicit_utc_is_accepted():
    assert _timestamp("2026-10-21T08:00:00") is None
    aware = _timestamp("2026-10-21T08:00:00+00:00")
    zulu = _timestamp("2026-10-21T08:00:00Z")
    assert aware is not None
    assert aware == zulu


def test_candles_are_sorted_deduplicated_and_invalid_ranges_rejected():
    s = state([
        {"timestamp": 3000, "high": 103, "low": 101},
        {"timestamp": 2000, "high": 99, "low": 100},  # invalid OHLC range
        {"timestamp": 1000, "high": 101, "low": 99},
        {"timestamp": 3000, "high": 104, "low": 102},  # later update wins
    ])
    assert _candles(s) == [
        (1000.0, 101.0, 99.0),
        (3000.0, 104.0, 102.0),
    ]
