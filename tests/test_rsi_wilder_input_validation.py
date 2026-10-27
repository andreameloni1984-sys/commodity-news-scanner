import math

from engine.regime import _rsi_wilder


def test_rsi_wilder_rejects_fractional_boolean_and_nonfinite_periods():
    closes = [float(i) for i in range(20)]
    for period in (14.5, True, float("nan"), float("inf"), float("-inf"), "not-a-period"):
        assert _rsi_wilder(closes, period=period) is None


def test_rsi_wilder_accepts_integer_period_and_preserves_flat_series_behavior():
    rising = [float(i) for i in range(20)]
    flat = [100.0] * 20

    assert _rsi_wilder(rising, period=14) == 100.0
    assert _rsi_wilder(flat, period=14) == 50.0
