from engine.intraday_indicators import calculate_intraday_context


def _candles(count=240):
    rows = []
    for i in range(count):
        close = 100.0 + i * 0.1
        rows.append({
            "timestamp": 1794000000 + i * 300,
            "datetime": None,
            "open": close - 0.05,
            "high": close + 0.1,
            "low": close - 0.1,
            "close": close,
            "volume": 100 + i,
        })
    return rows


def test_intraday_context_calculates_ema_bollinger_vwap_and_poc():
    rows = _candles()
    result = calculate_intraday_context(rows)
    assert result["status"] == "CALCULATED"
    assert result["ema"]["ema10"] is not None
    assert result["ema"]["ema50"] is not None
    assert result["ema"]["ema200"] is not None
    assert result["bollinger_20_2"]["middle"] is not None
    assert result["vwap"]["value"] is not None
    assert result["volume_profile"]["poc"] is not None


def test_intraday_context_degrades_gracefully_without_volume_or_history():
    rows = [{"high": 2, "low": 1, "close": 1.5} for _ in range(5)]
    result = calculate_intraday_context(rows)
    assert result["status"] == "CALCULATED"
    assert result["ema"]["ema50"] is None
    assert result["bollinger_20_2"] is None
    assert result["vwap"]["value"] is None
    assert result["volume_profile"] is None
