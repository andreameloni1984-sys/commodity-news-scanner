from engine.universe_audit import audit_universe


def test_audit_reports_missing_and_category_coverage():
    report = audit_universe(
        {"XAUUSD": "commodities", "WTI": "commodities", "EURUSD": "forex", "SPY": "etf"},
        [
            {"symbol": "XAUUSD", "category": "commodities"},
            {"symbol": "WTI", "category": "commodities"},
            {"symbol": "SPY", "category": "etf"},
        ],
    )

    assert report["expected_count"] == 4
    assert report["covered_count"] == 3
    assert report["missing_symbols"] == ["EURUSD"]
    assert report["coverage_pct"] == 75.0
    assert report["by_category"]["forex"] == {
        "expected": 1, "covered": 0, "missing": 1
    }
    assert report["provider_availability_verified"] is False
    assert report["broker_tradability_verified"] is False


def test_disabled_instrument_does_not_count_as_covered():
    report = audit_universe(
        {"AAPL": "equity"},
        [{"symbol": "AAPL", "category": "equity", "enabled": False}],
    )

    assert report["covered_count"] == 0
    assert report["missing_symbols"] == ["AAPL"]
    assert report["disabled_expected_symbols"] == ["AAPL"]


def test_audit_surfaces_duplicates_unexpected_and_malformed_entries():
    report = audit_universe(
        {"EURUSD": "forex"},
        [
            {"symbol": " eurusd ", "category": "forex"},
            {"symbol": "EURUSD", "category": "forex"},
            {"symbol": "BTCUSD", "category": "crypto"},
            {"category": "unknown"},
        ],
    )

    assert report["duplicate_symbols"] == ["EURUSD"]
    assert report["unexpected_symbols"] == ["BTCUSD"]
    assert report["malformed_entries"] == ["EMPTY_SYMBOL"]
    assert report["covered_count"] == 1
