"""Fail-closed tests for Yahoo's parallel candle arrays."""

import time

import pytest

from engine.data import MIN_CANDLES_REQUIRED, _parse_yahoo


def _payload():
    count = MIN_CANDLES_REQUIRED
    latest = int(time.time()) - 60
    timestamps = [latest - (count - index - 1) * 300 for index in range(count)]
    closes = [100.0 + index * 0.1 for index in range(count)]
    return {
        "chart": {
            "result": [{
                "timestamp": timestamps,
                "indicators": {
                    "quote": [{
                        "open": [value - 0.1 for value in closes],
                        "high": [value + 0.5 for value in closes],
                        "low": [value - 0.5 for value in closes],
                        "close": closes,
                        "volume": [100.0] * count,
                    }]
                },
            }]
        }
    }


def test_parse_yahoo_accepts_aligned_ohlc_and_volume_arrays():
    candles, error = _parse_yahoo(_payload())

    assert error is None
    assert len(candles) == MIN_CANDLES_REQUIRED
    assert candles[-1]["close"] == pytest.approx(100.0 + (MIN_CANDLES_REQUIRED - 1) * 0.1)


@pytest.mark.parametrize("field", ["open", "high", "low", "close"])
def test_parse_yahoo_rejects_misaligned_ohlc_array(field):
    payload = _payload()
    payload["chart"]["result"][0]["indicators"]["quote"][0][field].pop()

    candles, error = _parse_yahoo(payload)

    assert candles == []
    assert error == "YAHOO_MISALIGNED_OHLC_ARRAYS"


def test_parse_yahoo_rejects_misaligned_nonempty_volume_array():
    payload = _payload()
    payload["chart"]["result"][0]["indicators"]["quote"][0]["volume"].pop()

    candles, error = _parse_yahoo(payload)

    assert candles == []
    assert error == "YAHOO_MISALIGNED_VOLUME_ARRAY"


def test_parse_yahoo_allows_missing_optional_volume_array():
    payload = _payload()
    payload["chart"]["result"][0]["indicators"]["quote"][0].pop("volume")

    candles, error = _parse_yahoo(payload)

    assert error is None
    assert len(candles) == MIN_CANDLES_REQUIRED
    assert all(candle["volume"] == 0 for candle in candles)

def test_parse_yahoo_rejects_non_list_timestamp_array():
    payload = _payload()
    payload["chart"]["result"][0]["timestamp"] = "not-a-timestamp-array"

    candles, error = _parse_yahoo(payload)

    assert candles == []
    assert error == "YAHOO_INVALID_TIMESTAMP_ARRAY"
