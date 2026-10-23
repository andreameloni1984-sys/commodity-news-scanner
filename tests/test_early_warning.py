from datetime import datetime, timezone

from engine.early_warning import compute_market_early_warning, classify_catalyst_timing


def test_market_early_warning_requires_timestamped_data():
    result = compute_market_early_warning([100, 99, 98], [], 1.0)
    assert result["stage"] == "INSUFFICIENT_DATA"
    assert result["execution_authorized"] is False


def test_market_early_warning_detects_directional_acceleration_without_authorizing_trade():
    now = 1_800_000_000.0
    timestamps = [now + i * 60 for i in range(91)]
    closes = []
    for i in range(91):
        if i < 60:
            closes.append(100.0 + 0.002 * i)
        else:
            closes.append(100.12 - 0.035 * (i - 60))
    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=timestamps[-1])
    assert result["direction"] == "SHORT"
    assert result["stage"] in {"EARLY_WARNING", "LATE_MOVE", "WATCH"}
    assert result["execution_authorized"] is False
    assert result["method"] == "HEURISTIC_NOT_CALIBRATED"


def test_catalyst_timing_requires_real_publication_timestamp():
    now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
    missing = classify_catalyst_timing({"title": "Oil supply news"}, now)
    fresh = classify_catalyst_timing({
        "published": "Thu, 22 Oct 2026 11:50:00 GMT"
    }, now)
    stale = classify_catalyst_timing({
        "published": "Thu, 22 Oct 2026 06:00:00 GMT"
    }, now)
    assert missing["timing"] == "TIME_UNVERIFIED"
    assert fresh["timing"] == "FRESH_CATALYST"
    assert stale["timing"] == "STALE_CATALYST"
    assert all(x["execution_authorized"] is False for x in (missing, fresh, stale))


def test_market_early_warning_rejects_stale_latest_timestamp():
    now = 1_800_000_000.0
    timestamps = [now - 9000 + i * 60 for i in range(91)]
    closes = [100.0 + i * 0.02 for i in range(91)]
    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=now)
    assert result["stage"] == "INSUFFICIENT_DATA"
    assert result["direction"] == "NONE"
    assert result["latest_timestamp_age_seconds"] == 3600.0
    assert "troppo vecchio" in result["reasons"][0]
    assert result["execution_authorized"] is False


def test_market_early_warning_rejects_future_latest_timestamp():
    now = 1_800_000_000.0
    timestamps = [now + 300 + i * 60 for i in range(91)]
    closes = [100.0 + i * 0.02 for i in range(91)]
    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=now)
    assert result["stage"] == "INSUFFICIENT_DATA"
    assert result["direction"] == "NONE"
    assert "nel futuro" in result["reasons"][0]
    assert result["execution_authorized"] is False


def test_lead_time_backtest_needs_valid_history():
    from engine.early_warning import backtest_market_early_warning_lead_time
    result = backtest_market_early_warning_lead_time([])
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["execution_authorized"] is False



def test_market_early_warning_rejects_mismatched_price_timestamp_lengths():
    now = 1_800_000_000.0
    timestamps = [now - (90 - i) * 60 for i in range(91)]
    closes = [100.0 + i * 0.01 for i in range(91)]

    missing_timestamp = compute_market_early_warning(
        closes, timestamps[:-1], atr=0.5, now=now
    )
    missing_price = compute_market_early_warning(
        closes[:-1], timestamps, atr=0.5, now=now
    )

    for result in (missing_timestamp, missing_price):
        assert result["stage"] == "INSUFFICIENT_DATA"
        assert result["direction"] == "NONE"
        assert result["score"] == 0
        assert "non coincide" in result["reasons"][0]
        assert result["execution_authorized"] is False


def test_reversal_is_not_mislabeled_as_directional_acceleration():
    now = 1_800_000_000.0
    timestamps = [now - (90 - i) * 60 for i in range(91)]
    closes = []
    for i in range(91):
        if i <= 30:
            closes.append(103.0)
        elif i <= 60:
            closes.append(103.0 - (3.0 * (i - 30) / 30.0))
        else:
            closes.append(100.0 + (1.0 * (i - 60) / 30.0))
    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=now)
    assert result["direction"] == "LONG"
    assert "accelerazione recente coerente con la direzione" not in result["reasons"]
    assert result["execution_authorized"] is False
