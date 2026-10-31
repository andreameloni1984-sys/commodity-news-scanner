"""Tests for the optional free-plan Narwhal futures reference feed."""

from datetime import datetime, timezone
from types import SimpleNamespace

import engine.data as data
from engine.state import SoyuzState


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def _configure(monkeypatch, now=6300):
    monkeypatch.setattr(data, "_NARWHAL_SLOT_CACHE", {})
    monkeypatch.setattr(data.time, "time", lambda: now)
    monkeypatch.setenv("NARWHAL_REFERENCE_ENABLED", "1")
    monkeypatch.setenv("NARWHAL_API_KEY", "free-test-key")
    return datetime.fromtimestamp(now, timezone.utc).isoformat()


def _payload(timestamp, **overrides):
    value = {
        "id": "GC",
        "name": "Gold",
        "exchange": "COMEX",
        "currency": "USD",
        "unit": "usd_per_troy_ounce",
        "price": "2745.5",
        "timestamp": timestamp,
        "market_session": "open",
        "stale": False,
        "delayed": True,
    }
    value.update(overrides)
    return value


def test_narwhal_free_reference_preserves_provenance_and_never_sets_execution(monkeypatch):
    timestamp = _configure(monkeypatch)
    calls = []

    def fake_get(url, headers, timeout):
        calls.append((url, headers, timeout))
        return FakeResponse(_payload(timestamp))

    monkeypatch.setattr(data.requests, "get", fake_get)

    reference = data._fetch_narwhal_reference("XAU/USD")

    assert len(calls) == 1
    url, headers, timeout = calls[0]
    assert url.endswith("/v1/futures/GC/price")
    assert headers["Authorization"] == "Bearer free-test-key"
    assert timeout == data.TIMEOUT_SECONDS
    assert reference["provider"] == "NARWHAL"
    assert reference["symbol"] == "GC"
    assert reference["source_timestamp"] == timestamp
    assert reference["currency"] == "USD"
    assert reference["unit"] == "usd_per_troy_ounce"
    assert reference["price"] == 2745.5
    assert reference["bid"] is None
    assert reference["ask"] is None
    assert reference["age_seconds"] == 0.0
    assert reference["delayed"] is True
    assert reference["status"] == "DELAYED_15M"
    assert reference["market_type"] == "FUTURES_FRONT_MONTH_CONTINUOUS"
    assert reference["contract_month"] is None
    assert reference["comparison_status"] == "CONTRACT_MONTH_NOT_EXPOSED"
    assert reference["deviation_pct"] is None
    assert reference["source_independence_status"] == (
        "UNVERIFIED_UPSTREAM_ROUTING_NOT_DISCLOSED"
    )
    assert "NARWHAL" not in data.PROVIDER_ORDER["XAU/USD"]


def test_narwhal_reference_is_disabled_without_free_key(monkeypatch):
    monkeypatch.setattr(data, "_NARWHAL_SLOT_CACHE", {})
    monkeypatch.setattr(data.time, "time", lambda: 6300)
    monkeypatch.setenv("NARWHAL_REFERENCE_ENABLED", "1")
    monkeypatch.delenv("NARWHAL_API_KEY", raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("No request may be made without a configured key.")

    monkeypatch.setattr(data.requests, "get", forbidden)
    reference = data._fetch_narwhal_reference("XAU/USD")

    assert reference["status"] == "NOT_CONFIGURED"
    assert reference["price"] is None


def test_narwhal_rotation_skips_non_scheduled_symbol(monkeypatch):
    _configure(monkeypatch, now=6300)  # slot 7 rotates to XAU/USD

    def forbidden(*args, **kwargs):
        raise AssertionError("A non-scheduled instrument must not consume quota.")

    monkeypatch.setattr(data.requests, "get", forbidden)
    reference = data._fetch_narwhal_reference("XAG/USD")

    assert reference["status"] == "NOT_SCHEDULED_THIS_SLOT"
    assert reference["scheduled_symbol"] == "XAU/USD"


def test_narwhal_stale_price_is_retained_as_stale_reference_only(monkeypatch):
    now = 6300
    timestamp = datetime.fromtimestamp(now - 1800, timezone.utc).isoformat()
    _configure(monkeypatch, now=now)
    monkeypatch.setattr(
        data.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            _payload(timestamp, stale=True)
        ),
    )

    reference = data._fetch_narwhal_reference("XAU/USD")

    assert reference["status"] == "STALE"
    assert reference["age_seconds"] == 1800.0
    assert reference["price"] == 2745.5
    assert reference["deviation_pct"] is None


def test_narwhal_rejects_invalid_price_and_symbol_mismatch(monkeypatch):
    timestamp = _configure(monkeypatch)
    monkeypatch.setattr(
        data.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            _payload(timestamp, price="NaN")
        ),
    )
    invalid_price = data._fetch_narwhal_reference("XAU/USD")
    assert invalid_price["status"] == "INVALID_PRICE"
    assert invalid_price["price"] is None

    _configure(monkeypatch, now=6300)
    monkeypatch.setattr(
        data.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            _payload(timestamp, id="SI")
        ),
    )
    mismatch = data._fetch_narwhal_reference("XAU/USD")
    assert mismatch["status"] == "SYMBOL_MISMATCH"
    assert mismatch["price"] is None


def test_narwhal_reference_does_not_replace_execution_price(monkeypatch):
    candles = []
    latest = 6300 - 30
    for index in range(data.MIN_CANDLES_REQUIRED):
        close = 100.0 + index * 0.01
        candles.append({
            "timestamp": latest - (data.MIN_CANDLES_REQUIRED - index - 1) * 300,
            "open": close - 0.05,
            "high": close + 0.50,
            "low": close - 0.50,
            "close": close,
            "volume": 10.0,
        })

    monkeypatch.setattr(
        data,
        "_fetch_narwhal_reference",
        lambda symbol: {
            "provider": "NARWHAL",
            "price": 2745.5,
            "status": "DELAYED_15M",
            "deviation_pct": None,
        },
    )
    monkeypatch.setattr(
        data,
        "classify_data_status",
        lambda commodity, live, data_ok, timestamp=None: "LIVE" if live else "STALE",
    )

    state = SoyuzState(commodity="Oro", symbol="XAU/USD")
    state.metadata["execution_provider"] = "YAHOO"
    state.metadata["execution_symbol"] = "GC=F"
    state.metadata["execution_market_type"] = "FUTURES_CONTINUOUS"
    finalized = data._finalize_with_narwhal_reference(
        state, candles, "YAHOO"
    )

    assert finalized.price == candles[-1]["close"]
    assert finalized.data_source == "YAHOO"
    assert finalized.metadata["execution_provider"] == "YAHOO"
    assert finalized.metadata["reference_quotes"]["NARWHAL"]["price"] == 2745.5
