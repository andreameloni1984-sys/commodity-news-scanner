from engine.data import _aggregate, _build_mtf


def _candles(count=48):
    return [
        {
            "timestamp": float(i * 300),
            "open": 100.0 + i,
            "high": 100.5 + i,
            "low": 99.5 + i,
            "close": 100.25 + i,
            "volume": 1.0,
        }
        for i in range(count)
    ]


def test_4h_aggregation_is_built_from_source_candles():
    candles = _candles(48)
    h4 = _aggregate(candles, 240)
    assert len(h4) == 1
    assert h4[0]["open"] == candles[0]["open"]
    assert h4[0]["close"] == candles[-1]["close"]
    assert h4[0]["high"] == max(c["high"] for c in candles)
    assert h4[0]["low"] == min(c["low"] for c in candles)


def test_mtf_exposes_real_4h_and_no_synthetic_1m():
    mtf = _build_mtf(_candles(48))
    assert "H4" in mtf
    assert "4h" in mtf
    assert "1M" not in mtf
    assert "1min" not in mtf


def test_4h_aggregation_preserves_volume():
    candles = _candles(48)
    h4 = _aggregate(candles, 240)
    assert h4[0]["volume"] == sum(c["volume"] for c in candles)
