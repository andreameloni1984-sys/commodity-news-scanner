"""Offline regression tests for Gagarin's free SILV spot reference."""

from datetime import datetime, timezone

import pytest
import requests

import engine.data as data
from engine.state import SoyuzState


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload


def _iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def _payload(now, gold_overrides=None, silver_overrides=None):
    component_time = int(now * 1000)
    gold = {
        "symbol": "Au",
        "category": "precious_metals",
        "price": 3900.0,
        "bid": 3899.0,
        "ask": 3901.0,
        "currency": "USD",
        "unit": "troy_oz",
        "last_updated": _iso(now - 60),
        "timestamp": _iso(now),
        "data_age_minutes": 0,
        "source_prices": [
            {"source": "kitco", "price": 3899.5, "bid": 3899.0, "ask": 3900.0, "timestamp": component_time},
            {"source": "fault", "price": 3900.1, "timestamp": component_time},
            {"source": "chainlink", "price": 3899.8, "timestamp": component_time},
            {"source": "nfusion", "price": 3900.2, "bid": 3899.2, "ask": 3901.2, "timestamp": component_time},
        ],
    }
    silver = {
        "symbol": "Ag",
        "category": "precious_metals",
        "price": 49.2,
        "bid": 49.1,
        "ask": 49.3,
        "currency": "USD",
        "unit": "troy_oz",
        "last_updated": _iso(now - 60),
        "timestamp": _iso(now),
        "data_age_minutes": 0,
        "source_prices": [
            {"source": "kitco", "price": 49.1, "timestamp": component_time},
            {"source": "fault", "price": 49.2, "timestamp": component_time},
            {"source": "chainlink", "price": 49.15, "timestamp": component_time},
            {"source": "nfusion", "price": 49.25, "timestamp": component_time},
        ],
    }
    gold.update(gold_overrides or {})
    silver.update(silver_overrides or {})
    return {"commodities": {"gold": gold, "silver": silver}}


def _configure(monkeypatch, now):
    monkeypatch.setattr(data, "_SILV_SPOT_CACHE", {})
    monkeypatch.setattr(data.time, "time", lambda: now)
    monkeypatch.setenv("SILV_SPOT_REFERENCE_ENABLED", "1")


def test_silv_gold_reference_preserves_timestamp_bid_ask_and_components(monkeypatch):
    now = datetime(2026, 10, 31, 22, 40, tzinfo=timezone.utc).timestamp()
    _configure(monkeypatch, now)
    calls = []
    payload = _payload(now)

    def fake_get(url, headers, timeout):
        calls.append((url, headers, timeout))
        return FakeResponse(payload)

    monkeypatch.setattr(data.requests, "get", fake_get)

    quote = data._fetch_silv_spot_reference("XAU/USD")

    assert len(calls) == 1
    assert calls[0][0] == data.SILV_SPOT_URL
    assert "Authorization" not in calls[0][1]
    assert calls[0][2] == data.TIMEOUT_SECONDS
    assert quote["provider"] == "SILV_DATA"
    assert quote["symbol"] == "AU"
    assert quote["source_timestamp"] == _iso(now - 60)
    assert quote["currency"] == "USD"
    assert quote["unit"] == "troy_oz"
    assert quote["price"] == 3900.0
    assert quote["bid"] == 3899.0
    assert quote["ask"] == 3901.0
    assert quote["age_seconds"] == 60.0
    assert quote["status"] == "WITHIN_AGE_LIMIT"
    assert quote["market_type"] == "SPOT"
    assert [row["provider"] for row in quote["source_components"]] == [
        "CHAINLINK", "FAULT", "KITCO", "NFUSION"
    ]
    assert quote["source_component_count"] == 4
    assert quote["source_independence_status"] == (
        "PROVIDER_REPORTED_MULTIPLE_COMPONENTS_NOT_INDEPENDENTLY_AUDITED"
    )
    assert quote["deviation_pct"] is None
    assert quote["basis_spot_minus_futures_pct"] is None


def test_silv_cache_is_shared_between_gold_and_silver(monkeypatch):
    now = datetime(2026, 10, 31, 22, 40, tzinfo=timezone.utc).timestamp()
    _configure(monkeypatch, now)
    calls = []
    monkeypatch.setattr(
        data.requests,
        "get",
        lambda *args, **kwargs: (
            calls.append((args, kwargs)) or FakeResponse(_payload(now))
        ),
    )

    gold = data._fetch_silv_spot_reference("XAU/USD")
    silver = data._fetch_silv_spot_reference("XAG/USD")

    assert len(calls) == 1
    assert gold["cache_status"] == "FETCHED"
    assert silver["cache_status"] == "CACHE_HIT"
    assert silver["symbol"] == "AG"
    assert silver["price"] == 49.2


def test_silv_freshness_uses_last_updated_not_response_time_or_reported_age(monkeypatch):
    now = datetime(2026, 10, 31, 22, 40, tzinfo=timezone.utc).timestamp()
    old_quote = _iso(now - 31 * 60)
    _configure(monkeypatch, now)
    monkeypatch.setattr(
        data.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            _payload(
                now,
                gold_overrides={
                    "last_updated": old_quote,
                    "timestamp": _iso(now),
                    "data_age_minutes": 0,
                },
            )
        ),
    )

    quote = data._fetch_silv_spot_reference("XAU/USD")

    assert quote["status"] == "STALE"
    assert quote["age_seconds"] == 1860.0
    assert quote["basis_spot_minus_futures_pct"] is None


def test_silv_spot_futures_basis_is_separate_from_deviation(monkeypatch):
    now = datetime(2026, 10, 31, 22, 40, tzinfo=timezone.utc).timestamp()
    _configure(monkeypatch, now)
    monkeypatch.setattr(
        data.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(_payload(now)),
    )

    quote = data._fetch_silv_spot_reference(
        "XAU/USD",
        execution_price=3905.0,
        execution_currency="USD",
        execution_unit="troy_oz",
        execution_market_type="FUTURES_CONTINUOUS",
        execution_status="LIVE",
        execution_provider="YAHOO",
        execution_symbol="GC=F",
        execution_timestamp=_iso(now - 30),
    )

    assert quote["comparison_status"] == "BASIS_SPOT_VS_FUTURES"
    assert quote["basis_status"] == "CALCULATED_SPOT_MINUS_FUTURES"
    assert quote["basis_spot_minus_futures_pct"] == pytest.approx(
        ((3900.0 - 3905.0) / 3905.0) * 100.0,
        abs=0.000001,
    )
    assert quote["deviation_pct"] is None
    assert quote["use_restriction"] == "REFERENCE_ONLY_NOT_FOR_TRADE_EXECUTION"


def test_silv_timeout_is_reported_without_fabricating_a_price(monkeypatch):
    now = datetime(2026, 10, 31, 22, 40, tzinfo=timezone.utc).timestamp()
    _configure(monkeypatch, now)

    def timeout(*args, **kwargs):
        raise requests.Timeout("mock timeout")

    monkeypatch.setattr(data.requests, "get", timeout)
    quote = data._fetch_silv_spot_reference("XAU/USD")

    assert quote["status"] == "REQUEST_TIMEOUT"
    assert quote["price"] is None
    assert quote["source_timestamp"] is None


def test_silv_reference_never_replaces_yahoo_execution_price(monkeypatch):
    now = datetime(2026, 10, 31, 22, 40, tzinfo=timezone.utc).timestamp()
    _configure(monkeypatch, now)
    monkeypatch.setattr(
        data.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(_payload(now)),
    )
    monkeypatch.setattr(
        data,
        "_fetch_narwhal_reference",
        lambda symbol: {"provider": "NARWHAL", "status": "DISABLED", "price": None},
    )
    monkeypatch.setattr(
        data,
        "classify_data_status",
        lambda commodity, live, data_ok, timestamp=None: "LIVE",
    )

    latest = now - 30
    candles = []
    for index in range(data.MIN_CANDLES_REQUIRED):
        close = 3890.0 + index * 0.01
        candles.append({
            "timestamp": latest - (data.MIN_CANDLES_REQUIRED - index - 1) * 300,
            "open": close - 0.05,
            "high": close + 0.50,
            "low": close - 0.50,
            "close": close,
            "volume": 10.0,
        })

    state = SoyuzState(commodity="Oro", symbol="XAU/USD")
    state.metadata["execution_provider"] = "YAHOO"
    state.metadata["execution_symbol"] = "GC=F"
    state.metadata["execution_market_type"] = "FUTURES_CONTINUOUS"
    finalized = data._finalize_with_narwhal_reference(state, candles, "YAHOO")

    assert finalized.price == candles[-1]["close"]
    assert finalized.data_source == "YAHOO"
    assert finalized.metadata["execution_provider"] == "YAHOO"
    reference = finalized.metadata["reference_quotes"]["SILV_DATA"]
    assert reference["price"] == 3900.0
    assert reference["basis_status"] == "CALCULATED_SPOT_MINUS_FUTURES"
    assert reference["basis_spot_minus_futures_pct"] is not None
