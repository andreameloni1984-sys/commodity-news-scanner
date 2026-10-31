"""Free-only, market-basis-safe routing tests for the active Gagarin universe."""

import time
from types import SimpleNamespace

from commodities.universe import enabled_commodities
import engine.data as data
from engine.state import SoyuzState


COMMODITY_SYMBOLS = {
    "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD",
    "BRENT/USD", "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
}
FX_SYMBOLS = {"EUR/USD", "GBP/USD"}


def _fresh_candles():
    latest = time.time() - 30
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


def test_all_ten_active_symbols_have_explicit_free_market_basis_routes():
    active = {row.symbol for row in enabled_commodities()}

    assert active == COMMODITY_SYMBOLS | FX_SYMBOLS
    assert set(data.PROVIDER_ORDER) == active
    assert set(data.EXECUTION_MARKET_TYPES) == active
    assert set(data.INSTRUMENT_DATA_METADATA) == active

    for symbol in COMMODITY_SYMBOLS:
        assert data.PROVIDER_ORDER[symbol] == ("YAHOO",)
        assert data.EXECUTION_MARKET_TYPES[symbol] == "FUTURES_CONTINUOUS"
        assert data.PROVIDER_MARKET_TYPES[symbol] == {
            "YAHOO": "FUTURES_CONTINUOUS"
        }

    for symbol in FX_SYMBOLS:
        assert data.PROVIDER_ORDER[symbol] == ("BIQUOTE", "YAHOO")
        assert data.EXECUTION_MARKET_TYPES[symbol] == "FX_SPOT"
        assert data.PROVIDER_MARKET_TYPES[symbol] == {
            "BIQUOTE": "FX_SPOT",
            "YAHOO": "FX_SPOT",
        }

    assert all(
        provider in data.FREE_EXECUTION_PROVIDERS
        for chain in data.PROVIDER_ORDER.values()
        for provider in chain
    )
    assert all(
        "TWELVE_DATA" not in chain
        for chain in data.PROVIDER_ORDER.values()
    )


def test_biquote_fx_symbols_are_explicit_and_yahoo_fallback_is_spot():
    assert data.BIQUOTE_SYMBOLS["EUR/USD"] == "EURUSD"
    assert data.BIQUOTE_SYMBOLS["GBP/USD"] == "GBPUSD"
    assert data.YAHOO_SYMBOLS["EUR/USD"] == "EURUSD=X"
    assert data.YAHOO_SYMBOLS["GBP/USD"] == "GBPUSD=X"


def test_biquote_commodity_cfd_cannot_replace_futures_execution():
    for symbol in COMMODITY_SYMBOLS:
        assert "BIQUOTE" not in data.PROVIDER_MARKET_TYPES[symbol]
        assert data.PROVIDER_MARKET_TYPES[symbol]["YAHOO"] == "FUTURES_CONTINUOUS"


def test_runtime_guard_rejects_paid_and_cross_basis_provider_candidates(monkeypatch):
    monkeypatch.setattr(
        data,
        "PROVIDER_ORDER",
        {"XAU/USD": ("TWELVE_DATA", "BIQUOTE", "YAHOO")},
    )
    monkeypatch.setattr(
        data,
        "classify_data_status",
        lambda commodity, live, data_ok, timestamp=None: "LIVE" if live else "STALE",
    )

    calls = []

    def provider_call(state, symbol, provider):
        calls.append(provider)
        return _fresh_candles(), None, data.YAHOO_SYMBOLS[symbol]

    monkeypatch.setattr(data, "_try_provider", provider_call)

    state = data.load_data(
        SoyuzState(commodity="Oro", symbol="XAU/USD"),
        SimpleNamespace(name="Oro", symbol="XAU/USD"),
    )

    assert calls == ["YAHOO"]
    assert state.data_source == "YAHOO"
    assert state.live is True
    assert state.metadata["provider_chain"] == ["YAHOO"]
    assert [row["provider"] for row in state.metadata["rejected_provider_candidates"]] == [
        "TWELVE_DATA", "BIQUOTE"
    ]
    assert state.metadata["execution_provider"] == "YAHOO"
    assert state.metadata["execution_symbol"] == "GC=F"
    assert state.metadata["execution_market_type"] == "FUTURES_CONTINUOUS"


def test_quote_provenance_metadata_is_complete_without_fabricated_bid_ask(monkeypatch):
    monkeypatch.setattr(
        data,
        "classify_data_status",
        lambda commodity, live, data_ok, timestamp=None: "LIVE" if live else "STALE",
    )
    monkeypatch.setattr(
        data,
        "_try_provider",
        lambda state, symbol, provider: (
            _fresh_candles(), None, data.YAHOO_SYMBOLS[symbol]
        ),
    )

    state = data.load_data(
        SoyuzState(commodity="Oro", symbol="XAU/USD"),
        SimpleNamespace(name="Oro", symbol="XAU/USD"),
    )

    metadata = state.metadata
    assert metadata["quote_provider"] == "YAHOO"
    assert metadata["quote_symbol"] == "GC=F"
    assert metadata["quote_timestamp"] == metadata["last_bar_timestamp"]
    assert metadata["quote_currency"] == "USD"
    assert metadata["quote_unit"] == "troy_oz"
    assert metadata["quote_market_type"] == "FUTURES_CONTINUOUS"
    assert metadata["quote_bid"] is None
    assert metadata["quote_ask"] is None
    assert metadata["quote_bid_ask_available"] is False
    assert metadata["quote_age_seconds"] <= data.EFFECTIVE_LIVE_MAX_AGE_SECONDS
    assert metadata["quote_freshness_status"] == "LIVE"
    assert metadata["quote_status"] == "LIVE"
    assert metadata["quote_price"] == state.price


def test_twelve_data_provider_is_hard_disabled_even_if_called_directly(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A paid/unverified provider must never be called.")

    monkeypatch.setattr(data, "_fetch_twelve", forbidden)
    monkeypatch.setattr(data, "_fetch_twelve_agriculture", forbidden)

    candles, error, provider_symbol = data._try_provider(
        SoyuzState(commodity="Oro", symbol="XAU/USD"),
        "XAU/USD",
        "TWELVE_DATA",
    )

    assert candles == []
    assert error == "PAID_OR_UNVERIFIED_PROVIDER_DISABLED_BY_FREE_ONLY_POLICY"
    assert provider_symbol is None
