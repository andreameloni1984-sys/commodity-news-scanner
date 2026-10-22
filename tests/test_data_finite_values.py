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
