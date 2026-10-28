from engine.regime import _volatility_diagnostics
from engine.state import SoyuzState


def _state(highs, lows, atr=1.0):
    return SoyuzState(
        commodity="Oro",
        symbol="XAU/USD",
        atr=atr,
        highs=list(highs),
        lows=list(lows),
    )


def test_valid_aligned_recent_ranges_produce_diagnostic():
    highs = [101, 102, 103, 104, 105, 106, 107, 108]
    lows = [100, 101, 102, 103, 104, 105, 106, 107]
    result = _volatility_diagnostics(_state(highs, lows))
    assert result["status"] == "STABLE"
    assert result["samples"] == 8
    assert result["recent_to_older_ratio"] == 1.0


def test_invalid_latest_range_returns_unknown_instead_of_skipping_bar():
    highs = [101, 102, 103, 104, 105, 106, 107, float("nan")]
    lows = [100, 101, 102, 103, 104, 105, 106, 107]
    result = _volatility_diagnostics(_state(highs, lows))
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "INVALID_RECENT_RANGE"
    assert result["samples"] == 7


def test_mismatched_high_low_lengths_return_unknown():
    highs = [101, 102, 103, 104, 105, 106, 107, 108]
    lows = [100, 101, 102, 103, 104, 105, 106]
    result = _volatility_diagnostics(_state(highs, lows))
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "OHLC_LENGTH_MISMATCH"
    assert result["samples"] == 0


def test_invalid_atr_remains_unknown():
    result = _volatility_diagnostics(_state([101] * 8, [100] * 8, atr=float("inf")))
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "INVALID_ATR"
