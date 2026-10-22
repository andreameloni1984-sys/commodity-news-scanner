import pytest
from engine.overnight_wti import evaluate_directional_edge, summarize_overnight


def test_overnight_summary_measures_return_range_volatility_and_gap():
    result = summarize_overnight(
        [
            {"timestamp": 1, "open": 80, "high": 81, "low": 79, "close": 80.5, "volume": 10},
            {"timestamp": 2, "open": 80.5, "high": 82, "low": 80, "close": 81.6, "volume": 15},
        ],
        previous_close=80, us_open=82.416,
        historical_ranges_pct=[0.5] * 20, event_flags={"EIA": True, "OPEC": False},
    )
    assert result["paper_only"] is True
    assert result["overnight_return_pct"] == pytest.approx(2.0)
    assert result["range_pct"] == pytest.approx(3.75)
    assert result["realized_volatility_pct"] is not None
    assert result["gap_to_us_open_pct"] == pytest.approx(1.0)
    assert result["volume"] == 25
    assert result["regime"] == "SHOCK"
    assert result["event_caution"] is True
    assert result["directional_bias"] == "UNTESTED"


def test_insufficient_history_does_not_invent_regime():
    result = summarize_overnight(
        [{"high": 81, "low": 79, "close": 80, "open": 80}],
        previous_close=80, historical_ranges_pct=[1.0, 2.0],
    )
    assert result["regime"] == "UNCLASSIFIED_INSUFFICIENT_HISTORY"


def test_empty_or_invalid_bars_fail_closed():
    result = summarize_overnight([{"high": "bad", "low": 2, "close": 3}])
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["regime"] == "UNKNOWN"
    assert result["overnight_return_pct"] is None


def test_directional_edge_requires_sample_and_does_not_promote():
    rows = [
        {"overnight_return_pct": 1, "next_session_return_pct": 0.5},
        {"overnight_return_pct": -1, "next_session_return_pct": -0.2},
        {"overnight_return_pct": 1, "next_session_return_pct": -0.1},
    ]
    result = evaluate_directional_edge(rows, minimum_samples=30)
    assert result["samples"] == 3
    assert result["same_direction_rate_pct"] == pytest.approx(200 / 3)
    assert result["status"] == "INSUFFICIENT_SAMPLE"
    assert result["directional_edge_validated"] is False
