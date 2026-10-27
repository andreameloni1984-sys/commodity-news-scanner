"""Regression tests for finite numeric market-data validation."""

import math
import time

import pytest

from engine.data import MIN_CANDLES_REQUIRED, _normalize, _validate_candles


@pytest.mark.parametrize(
    "field,value",
    [
        ("timestamp", float("nan")),
        ("timestamp", float("inf")),
        ("open", float("nan")),
        ("high", float("inf")),
        ("low", float("-inf")),
        ("close", float("nan")),
        ("volume", float("inf")),
    ],
)
def test_normalize_rejects_non_finite_values(field, value):
    candle = {
        "timestamp": time.time(),
        "open": 100.0,
        "high": 102.0,
        "low": 99.0,
        "close": 101.0,
        "volume": 10.0,
    }
    candle[field] = value

    assert _normalize(
        candle["timestamp"],
        candle["open"],
        candle["high"],
        candle["low"],
        candle["close"],
        candle["volume"],
    ) is None


@pytest.mark.parametrize(
    "field",
    ["timestamp", "open", "high", "low", "close", "volume"],
)
def test_normalize_rejects_boolean_market_fields(field):
    candle = {
        "timestamp": time.time(),
        "open": 100.0,
        "high": 102.0,
        "low": 99.0,
        "close": 101.0,
        "volume": 10.0,
    }
    candle[field] = True

    assert _normalize(
        candle["timestamp"],
        candle["open"],
        candle["high"],
        candle["low"],
        candle["close"],
        candle["volume"],
    ) is None


def test_normalize_rejects_negative_volume():
    assert _normalize(time.time(), 100, 102, 99, 101, -1) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("timestamp", float("nan")),
        ("open", float("nan")),
        ("high", float("inf")),
        ("low", float("-inf")),
        ("close", float("nan")),
        ("volume", float("inf")),
    ],
)
def test_validate_candles_drops_non_finite_rows(field, value):
    now = time.time()
    candles = [
        {
            "timestamp": now - (MIN_CANDLES_REQUIRED - i) * 60,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
        }
        for i in range(MIN_CANDLES_REQUIRED + 1)
    ]
    candles[0][field] = value

    cleaned, error = _validate_candles(candles)

    assert error is None
    assert len(cleaned) == MIN_CANDLES_REQUIRED
    for row in cleaned:
        assert all(
            math.isfinite(row[key])
            for key in ("timestamp", "open", "high", "low", "close", "volume")
        )


def test_validate_candles_rejects_negative_volume():
    now = time.time()
    candles = [
        {
            "timestamp": now - (MIN_CANDLES_REQUIRED - i) * 60,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
        }
        for i in range(MIN_CANDLES_REQUIRED + 1)
    ]
    candles[0]["volume"] = -1

    cleaned, error = _validate_candles(candles)

    assert error is None
    assert len(cleaned) == MIN_CANDLES_REQUIRED
    assert all(row["volume"] >= 0 for row in cleaned)

def test_validate_candles_deduplicates_identical_timestamp_rows():
    now = time.time()
    candles = [
        {
            "timestamp": now - (MIN_CANDLES_REQUIRED - i) * 60,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
        }
        for i in range(MIN_CANDLES_REQUIRED + 1)
    ]
    candles.append(candles[-1].copy())

    cleaned, error = _validate_candles(candles)

    assert error is None
    assert len(cleaned) == MIN_CANDLES_REQUIRED + 1


def test_validate_candles_fails_closed_on_conflicting_duplicate_timestamp():
    now = time.time()
    candles = [
        {
            "timestamp": now - (MIN_CANDLES_REQUIRED - i) * 60,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
        }
        for i in range(MIN_CANDLES_REQUIRED + 1)
    ]
    conflicting = candles[-1].copy()
    conflicting["close"] = 101.5
    candles.append(conflicting)

    cleaned, error = _validate_candles(candles)

    assert cleaned == []
    assert error == "CONFLICTING_DUPLICATE_TIMESTAMP"



@pytest.mark.parametrize(
    "field",
    ["timestamp", "open", "high", "low", "close", "volume"],
)
def test_validate_candles_drops_rows_with_boolean_market_fields(field):
    now = time.time()
    candles = [
        {
            "timestamp": now - (MIN_CANDLES_REQUIRED - i) * 60,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
        }
        for i in range(MIN_CANDLES_REQUIRED + 1)
    ]
    candles[0][field] = True

    cleaned, error = _validate_candles(candles)

    assert error is None
    assert len(cleaned) == MIN_CANDLES_REQUIRED
    assert all(not isinstance(row[field], bool) for row in cleaned)


@pytest.mark.parametrize("boolean_field", ["timestamp", "ohlc", "volume"])
def test_validate_candles_rejects_boolean_numeric_values(boolean_field):
    now = time.time()
    candles = [
        {
            "timestamp": now - (MIN_CANDLES_REQUIRED - i) * 60,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
        }
        for i in range(MIN_CANDLES_REQUIRED + 1)
    ]

    row = candles[0]
    if boolean_field == "timestamp":
        row["timestamp"] = True
    elif boolean_field == "volume":
        row["volume"] = True
    else:
        # All-boolean OHLC remains numerically plausible after float(True)=1.0
        # unless the validator explicitly rejects booleans.
        for field in ("open", "high", "low", "close"):
            row[field] = True

    cleaned, error = _validate_candles(candles)

    assert error is None
    assert len(cleaned) == MIN_CANDLES_REQUIRED
    assert all(not isinstance(value, bool) for candle in cleaned for value in candle.values())
