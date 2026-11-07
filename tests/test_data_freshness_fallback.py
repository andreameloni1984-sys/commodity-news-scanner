"""Futures freshness tests: independent CFD references never replace futures quotes."""

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


def _configure_provider_chain(monkeypatch, provider_rows, provider_order=("YAHOO",)):
    monkeypatch.setattr(
        data,
        "PROVIDER_ORDER",
        {"XAU/USD": tuple(provider_order)},
    )
    calls = []

    def provider_call(state, symbol, provider):
        calls.append(provider)
        return provider_rows[provider]

    monkeypatch.setattr(data, "_try_provider", provider_call)
    # Keep tests independent of the weekday/weekend market calendar.
    monkeypatch.setattr(
        data,
        "classify_data_status",
        lambda commodity, live, data_ok, timestamp=None: "LIVE" if live else "STALE",
    )
    return calls


def _load(monkeypatch, provider_rows, provider_order=("YAHOO",)):
    _configure_provider_chain(monkeypatch, provider_rows, provider_order)
    state = SoyuzState(commodity="Oro", symbol="XAU/USD")
    commodity = SimpleNamespace(name="Oro", symbol="XAU/USD")
    return data.load_data(state, commodity)


def test_biquote_cfd_reference_is_never_a_futures_fallback(monkeypatch):
    provider_rows = {
        "YAHOO": (_candles(900), None, "GC=F"),
        "BIQUOTE": (_candles(30), None, "XAUUSD"),
    }
    calls = _configure_provider_chain(monkeypatch, provider_rows, provider_order=("YAHOO",))

    state = data.load_data(
        SoyuzState(commodity="Oro", symbol="XAU/USD"),
        SimpleNamespace(name="Oro", symbol="XAU/USD"),
    )

    assert calls == ["YAHOO"]
    assert state.data_source == "YAHOO"
    assert state.data_ok is True
    assert state.live is False
    assert state.metadata["freshness_status"] == "STALE"
    assert state.metadata["freshness_fallback_reason"] == "ALL_PROVIDER_CANDLES_STALE"


def test_stale_yahoo_futures_sample_is_kept_as_non_live_context(monkeypatch):
    provider_rows = {
        "YAHOO": (_candles(720), None, "GC=F"),
    }

    state = _load(monkeypatch, provider_rows)

    assert state.data_source == "YAHOO"
    assert state.data_ok is True
    assert state.live is False
    assert state.metadata["freshness_status"] == "STALE"
    assert state.metadata["freshness_fallback_reason"] == "ALL_PROVIDER_CANDLES_STALE"
    assert 700 <= state.data_age_seconds <= 740


def test_closed_market_marks_stale_yahoo_futures_as_market_closed(monkeypatch):
    provider_rows = {
        "YAHOO": (_candles(720), None, "GC=F"),
    }
    calls = _configure_provider_chain(monkeypatch, provider_rows)
    monkeypatch.setattr(
        data,
        "classify_data_status",
        lambda commodity, live, data_ok, timestamp=None: "MARKET_CLOSED",
    )
    state = data.load_data(
        SoyuzState(commodity="Oro", symbol="XAU/USD"),
        SimpleNamespace(name="Oro", symbol="XAU/USD"),
    )

    assert calls == ["YAHOO"]
    assert state.live is False
    assert state.metadata["data_status"] == "MARKET_CLOSED"
    assert state.metadata["freshness_fallback_reason"] == "MARKET_CLOSED"
