from types import SimpleNamespace

from engine.feedback import append_signal, load_feedback, record_forecasts, summarize, update_open_outcomes


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
