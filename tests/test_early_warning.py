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
    result = compute_market_early_warning(closes, timestamps, atr=0.5)
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
