"""Tests for the strict Trading 212 CFD instrument/series identity boundary."""
from dataclasses import replace

import pytest

from engine.cfd_identity import (
    CFDInstrumentIdentity,
    CFDQuoteSeriesIdentity,
    GAGARIN_CFD_LOGICAL_SYMBOLS,
    build_cfd_signal_id,
    validate_same_cfd_series,
)


def _instrument(**overrides):
    values = {
        "broker": "TRADING212",
        "market_type": "CFD",
        "logical_symbol": "WTI/USD",
        "broker_symbol": "OIL.BRENT.WTI.CONTRACT",
        "contract": "WTI CFD 27 Nov 2026",
        "expiry": "2026-11-27",
        "currency": "USD",
        "verification_source": "TRADING_212_APP_SCREEN",
        "verified_at_utc": "2026-11-06T00:00:00Z",
    }
    values.update(overrides)
    return CFDInstrumentIdentity(**values)


def _series(**overrides):
    values = {
        "provider": "TRADING212_CFD",
        "broker": "TRADING212",
        "market_type": "CFD",
        "broker_symbol": "OIL.BRENT.WTI.CONTRACT",
        "contract": "WTI CFD 27 Nov 2026",
        "expiry": "2026-11-27",
        "currency": "USD",
        "timeframe": "M5",
        "series_id": "t212-cfd-wti-2026-11-27-m5",
    }
    values.update(overrides)
    return CFDQuoteSeriesIdentity(**values)


def test_logical_universe_contains_exactly_the_eight_selected_commodities():
    assert GAGARIN_CFD_LOGICAL_SYMBOLS == {
        "XAU/USD",
        "XAG/USD",
        "COPPER/USD",
        "WTI/USD",
        "BRENT/USD",
        "WHEAT/USD",
        "CORN/USD",
        "SOYBEAN/USD",
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"logical_symbol": "NATGAS/USD"},
        {"logical_symbol": "EUR/USD"},
        {"logical_symbol": "SPY"},
        {"broker_symbol": ""},
        {"contract": ""},
        {"expiry": ""},
        {"expiry": "27-11-2026"},
        {"currency": "usd"},
        {"currency": "US"},
        {"verification_source": "BIQUOTE"},
        {"market_type": "FUTURES"},
    ],
)
def test_unverified_or_out_of_scope_instrument_identity_is_rejected(changes):
    with pytest.raises(ValueError):
        _instrument(**changes).validate()


def test_exact_trading212_cfd_series_can_be_bound_to_verified_instrument():
    validate_same_cfd_series(_instrument(), _series())


@pytest.mark.parametrize(
    "field,value",
    [
        ("broker_symbol", "WTI"),
        ("contract", "WTI CFD 04 Dec 2026"),
        ("expiry", "2026-12-04"),
        ("currency", "EUR"),
    ],
)
def test_quote_series_with_different_contract_identity_is_rejected(field, value):
    with pytest.raises(ValueError, match="identity mismatch"):
        validate_same_cfd_series(_instrument(), _series(**{field: value}))


@pytest.mark.parametrize("provider", ["BIQUOTE", "YAHOO", "YAHOO_FUTURES"])
def test_independent_reference_and_futures_series_cannot_become_t212_cfd(provider):
    with pytest.raises(ValueError, match="official Trading 212 CFD feed"):
        validate_same_cfd_series(_instrument(), _series(provider=provider))


def test_cfd_signal_id_is_namespaced_and_stable_for_same_verified_series():
    kwargs = {
        "direction": "LONG",
        "candle_timestamp": "2026-11-06T00:05:00+00:00",
        "entry": 78.10,
        "stop_loss": 77.70,
        "take_profits": (78.90, 79.40),
    }
    first = build_cfd_signal_id(_instrument(), _series(), **kwargs)
    second = build_cfd_signal_id(_instrument(), _series(), **kwargs)

    assert first.startswith("T212CFD-")
    assert first == second
    assert first != "a1b2c3d4e5f607182930"


def test_cfd_signal_id_rejects_naive_candle_timestamp_and_missing_levels():
    with pytest.raises(ValueError, match="UTC offset"):
        build_cfd_signal_id(
            _instrument(),
            _series(),
            direction="LONG",
            candle_timestamp="2026-11-06T00:05:00",
            entry=78.10,
            stop_loss=77.70,
            take_profits=(78.90,),
        )

    with pytest.raises(ValueError, match="take-profit"):
        build_cfd_signal_id(
            _instrument(),
            _series(),
            direction="LONG",
            candle_timestamp="2026-11-06T00:05:00Z",
            entry=78.10,
            stop_loss=77.70,
            take_profits=(),
        )


def test_cfd_signal_id_changes_when_verified_contract_expiry_changes():
    kwargs = {
        "direction": "SHORT",
        "candle_timestamp": "2026-11-06T00:10:00Z",
        "entry": 78.10,
        "stop_loss": 78.50,
        "take_profits": (77.70, 77.20),
    }
    first = build_cfd_signal_id(_instrument(), _series(), **kwargs)

    next_contract = _instrument(
        contract="WTI CFD 04 Dec 2026",
        expiry="2026-12-04",
        broker_symbol="OIL.WTI.DEC26",
    )
    next_series = _series(
        contract="WTI CFD 04 Dec 2026",
        expiry="2026-12-04",
        broker_symbol="OIL.WTI.DEC26",
        series_id="t212-cfd-wti-2026-12-04-m5",
    )
    second = build_cfd_signal_id(next_contract, next_series, **kwargs)

    assert first != second
