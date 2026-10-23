import pytest

from engine.commodity_research import audit_missed_moves, load_ohlc_csv


def bars(n=80):
    return [{"timestamp": i * 300, "open": 100.0, "high": 100.1,
             "low": 99.9, "close": 100.0, "volume": 1.0} for i in range(n)]


def test_audit_flags_spike_reversed_before_window_close():
    rows = bars()
    rows[50]["high"] = 102.0
    report = audit_missed_moves(rows, horizon=4, start=40, threshold_pct=0.5)
    assert report["status"] == "CALCULATED"
    assert report["up_event_windows"] > 0
    assert report["missed_up_windows"] > 0
    assert report["missed_up_by_any_signal"] >= 0
    assert report["prebreakout_only_up"] >= 0
    assert report["paper_only"] is True
    assert report["overlapping_windows"] is True


def test_quiet_series_does_not_invent_events():
    report = audit_missed_moves(bars(), horizon=4, start=40)
    assert report["status"] == "CALCULATED"
    assert report["up_event_windows"] == report["down_event_windows"] == 0
    assert report["missed_rate_pct"] is None
    assert report["missed_up_by_any_signal"] == report["missed_down_by_any_signal"] == 0
    assert report["by_regime"]
    assert sum(x["forecast_windows"] for x in report["by_regime"].values()) == report["forecasts"]
    assert sum(x["up_events"] for x in report["by_regime"].values()) == report["up_event_windows"]


def test_both_barriers_touched_are_marked_ambiguous():
    rows = bars()
    rows[50]["high"] = 102.0
    rows[50]["low"] = 98.0
    report = audit_missed_moves(rows, horizon=1, start=40, threshold_pct=0.5)
    assert report["ambiguous_windows"] > 0


def test_rejects_bad_parameters():
    with pytest.raises(ValueError, match="INVALID_AUDIT_PARAMETERS"):
        audit_missed_moves(bars(), threshold_pct=0)
    with pytest.raises(ValueError, match="INVALID_AUDIT_PARAMETERS"):
        audit_missed_moves(bars(), horizon=1.5)


def test_duplicate_and_nonchronological_timestamps_rejected(tmp_path):
    duplicate = tmp_path / "duplicate.csv"
    duplicate.write_text("timestamp,open,high,low,close\n1,100,101,99,100\n1,100,101,99,100\n")
    with pytest.raises(ValueError, match="DUPLICATE_TIMESTAMP"):
        load_ohlc_csv(duplicate)
    unordered = tmp_path / "unordered.csv"
    unordered.write_text("timestamp,open,high,low,close\n2,100,101,99,100\n1,100,101,99,100\n")
    with pytest.raises(ValueError, match="TIMESTAMPS_NOT_STRICTLY_INCREASING"):
        load_ohlc_csv(unordered)


def test_loads_valid_csv_and_rejects_invalid_or_nonfinite_ohlc(tmp_path):
    good = tmp_path / "good.csv"
    good.write_text("timestamp,open,high,low,close,volume\n1,100,101,99,100,3\n2,100,102,98,101,4\n")
    assert len(load_ohlc_csv(good)) == 2
    bad = tmp_path / "bad.csv"
    bad.write_text("timestamp,open,high,low,close\n1,100,99,98,100\n")
    with pytest.raises(ValueError, match="INVALID_OHLC"):
        load_ohlc_csv(bad)
    nonfinite = tmp_path / "nan.csv"
    nonfinite.write_text("timestamp,open,high,low,close\n1,nan,101,99,100\n")
    with pytest.raises(ValueError, match="NONFINITE_VALUE"):
        load_ohlc_csv(nonfinite)


def test_insufficient_history_is_explicit():
    report = audit_missed_moves(bars(40), horizon=4, start=40)
    assert report["status"] == "INSUFFICIENT_DATA"
    assert report["forecasts"] == 0



def test_non_overlapping_audit_sampling_is_explicit():
    rows = bars(100)
    report = audit_missed_moves(rows, horizon=4, start=40, step=4)
    assert report["status"] == "CALCULATED"
    assert report["sample_step_bars"] == 4
    assert report["overlapping_windows"] is False
    with pytest.raises(ValueError, match="INVALID_AUDIT_PARAMETERS"):
        audit_missed_moves(rows, horizon=4, start=40, step=0)
