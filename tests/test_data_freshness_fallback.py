"""Provider freshness fallback tests using a test-only same-basis commodity provider."""

import time
from types import SimpleNamespace

import engine.data as data
from engine.state import SoyuzState


def _candles(latest_age_seconds):
    latest = time.time() - latest_age_seconds
    rows = []
    for index in range(data.MIN_CANDLES_REQUIRED):
        close = 100.0 + index * 0.01
        rows.append({
            "timestamp": latest - (data.MIN_CANDLES_REQUIRED - index - 1) * 300,
            "open": close - 0.05,
            "high": close + 0.50,
            "low": close - 0.50,
            "close": close,
            "volume": 10.0,
        })
    return rows


def _configure_provider_chain(monkeypatch, provider_rows):
    providers = tuple(provider_rows)
    monkeypatch.setattr(data, "PROVIDER_ORDER", {"XAU/USD": providers})
    monkeypatch.setattr(data, "FREE_EXECUTION_PROVIDERS", frozenset(providers))
    monkeypatch.setattr(
        data,
        "EXECUTION_MARKET_TYPES",
        {**data.EXECUTION_MARKET_TYPES, "XAU/USD": "FUTURES_CONTINUOUS"},
    )
    monkeypatch.setattr(
        data,
        "PROVIDER_MARKET_TYPES",
        {
            **data.PROVIDER_MARKET_TYPES,
            "XAU/USD": {provider: "FUTURES_CONTINUOUS" for provider in providers},
        },
    )
    monkeypatch.setattr(
        data,
        "_try_provider",
        lambda state, symbol, provider: provider_rows[provider],
    )
    monkeypatch.setattr(
        data,
        "classify_data_status",
        lambda commodity, live, data_ok, timestamp=None: "LIVE" if live else "STALE",
    )


def _load(monkeypatch, provider_rows):
    _configure_provider_chain(monkeypatch, provider_rows)
    state = SoyuzState(commodity="Oro", symbol="XAU/USD")
    commodity = SimpleNamespace(name="Oro", symbol="XAU/USD")
    return data.load_data(state, commodity)


def test_stale_primary_provider_falls_through_to_fresh_provider(monkeypatch):
    provider_rows = {
        "ALT_TEST": (_candles(900), None, "TEST-GOLD-ALT"),
        "YAHOO": (_candles(90), None, "GC=F"),
    }
    state = _load(monkeypatch, provider_rows)

    assert state.data_source == "YAHOO"
    assert state.live is True
    assert state.metadata["freshness_status"] == "LIVE"
    assert state.metadata["freshness_fallback_used"] is True
    attempts = state.metadata["provider_attempts"]
    assert attempts[0]["freshness_status"] == "STALE"
    assert attempts[0]["accepted_for_live"] is False
    assert attempts[1]["freshness_status"] == "LIVE"
    assert attempts[1]["accepted_for_live"] is True


def test_all_stale_providers_keep_freshest_sample_as_non_live_context(monkeypatch):
    provider_rows = {
        "ALT_TEST": (_candles(1200), None, "TEST-GOLD-ALT"),
        "YAHOO": (_candles(720), None, "GC=F"),
    }
    state = _load(monkeypatch, provider_rows)

    assert state.data_source == "YAHOO"
    assert state.data_ok is True
    assert state.live is False
    assert state.metadata["freshness_status"] == "STALE"
    assert state.metadata["freshness_fallback_reason"] == "ALL_PROVIDER_CANDLES_STALE"
    assert 700 <= state.data_age_seconds <= 740


def test_closed_market_marks_stale_fallback_as_market_closed(monkeypatch):
    provider_rows = {
        "ALT_TEST": (_candles(1200), None, "TEST-GOLD-ALT"),
        "YAHOO": (_candles(720), None, "GC=F"),
    }
    _configure_provider_chain(monkeypatch, provider_rows)
    monkeypatch.setattr(
        data,
        "classify_data_status",
        lambda commodity, live, data_ok, timestamp=None: "MARKET_CLOSED",
    )
    calls = []

    def provider_call(state, symbol, provider):
        calls.append(provider)
        return provider_rows[provider]

    monkeypatch.setattr(data, "_try_provider", provider_call)
    state = data.load_data(
        SoyuzState(commodity="Oro", symbol="XAU/USD"),
        SimpleNamespace(name="Oro", symbol="XAU/USD"),
    )

    assert calls == ["ALT_TEST"]
    assert state.live is False
    assert state.metadata["data_status"] == "MARKET_CLOSED"
    assert state.metadata["freshness_fallback_reason"] == "MARKET_CLOSED"
